const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');
const os = require('os');
const PORT = 9334;
const userDir = fs.mkdtempSync(path.join(os.tmpdir(), 'disc-chrome-'));
const chrome = spawn('google-chrome', [
  '--headless=new', '--no-sandbox', '--disable-gpu', '--hide-scrollbars',
  '--disable-dev-shm-usage', '--no-first-run', '--no-default-browser-check',
  `--remote-debugging-port=${PORT}`, `--user-data-dir=${userDir}`,
  '--window-size=1440,1100', 'about:blank'
], { stdio: 'ignore' });
const sleep = (ms) => new Promise(r => setTimeout(r, ms));
async function waitForJson(){ for(let i=0;i<100;i++){ try{ const r=await fetch(`http://127.0.0.1:${PORT}/json`); if(r.ok) return await r.json(); }catch{} await sleep(100);} throw new Error('no chrome'); }

(async () => {
  const targets = await waitForJson();
  const target = targets.find(t => t.type === 'page');
  const ws = new WebSocket(target.webSocketDebuggerUrl);
  const pending = new Map();
  const events = [];
  let seq = 0;
  await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });
  ws.onmessage = (ev) => {
    const msg = JSON.parse(ev.data);
    if (msg.id) { const p = pending.get(msg.id); if (p) { pending.delete(msg.id); msg.error ? p.reject(new Error(JSON.stringify(msg.error))) : p.resolve(msg.result); } }
    else events.push(msg);
  };
  const send = (method, params = {}) => new Promise((resolve, reject) => { const id=++seq; pending.set(id,{resolve,reject}); ws.send(JSON.stringify({id,method,params})); });
  const evaluate = async (expression) => {
    const res = await send('Runtime.evaluate', {expression, returnByValue:true, awaitPromise:true, userGesture:true});
    if (res.exceptionDetails) throw new Error('Eval exception: '+JSON.stringify(res.exceptionDetails));
    return res.result.value;
  };
  const click = (sel) => evaluate(`document.querySelector(${JSON.stringify(sel)}).click()`);
  const mouse = (type, x, y, extra={}) => send('Input.dispatchMouseEvent', {type, x, y, ...extra});

  await send('Runtime.enable');
  await send('Page.enable');
  await send('Page.navigate', {url:'file://' + path.resolve('index.html')});
  await sleep(1000);

  const initial = await evaluate(`(() => ({
    step: document.querySelector('#rootwizard').dataset.step,
    active: document.querySelector('.disc-pane.is-active').id,
    order: [...document.querySelectorAll('#draggable-list1 .disc-item')].map(li => ({text: li.querySelector('.disc-item__text').textContent, type: li.dataset.type})),
    score: document.querySelector('#score-string').textContent,
    testHidden: document.querySelector('#screen-test').hidden,
    resultHidden: document.querySelector('#screen-result').hidden
  }))()`);
  console.log('INITIAL', JSON.stringify(initial, null, 2));

  // Move first item of list 1 to the bottom via mouse drag.
  const rects = await evaluate(`(() => [...document.querySelectorAll('#draggable-list1 .disc-item')].map(li => { const r=li.getBoundingClientRect(); return {x:r.x+r.width/2,y:r.y+r.height/2,top:r.top,bottom:r.bottom}; }))()`);
  const start = rects[0];
  const endY = rects[3].bottom + 4;
  await mouse('mouseMoved', start.x, start.y, {button:'none', buttons:0});
  await mouse('mousePressed', start.x, start.y, {button:'left', buttons:1, clickCount:1});
  await sleep(50);
  for (let i=1;i<=8;i++) {
    const y = start.y + (endY - start.y) * i / 8;
    await mouse('mouseMoved', start.x, y, {button:'none', buttons:1});
    await sleep(25);
  }
  await mouse('mouseReleased', start.x, endY, {button:'left', buttons:0, clickCount:1});
  await sleep(200);

  const afterDrag = await evaluate(`(() => ({
    order: [...document.querySelectorAll('#draggable-list1 .disc-item')].map(li => li.querySelector('.disc-item__text').textContent),
    ghost: !!document.querySelector('.disc-drag-ghost'),
    bodyDragging: document.body.classList.contains('is-dragging'),
    sourceGhost: !!document.querySelector('.is-ghost-source'),
    dropMarks: document.querySelectorAll('.is-drop-before, .is-drop-end').length,
    focused: document.activeElement && document.activeElement.className,
    live: document.querySelector('#live-status').textContent
  }))()`);
  console.log('AFTER DRAG', JSON.stringify(afterDrag, null, 2));

  // Navigate with next button through all 8 steps, recording progress.
  const steps = [];
  for (let i=0;i<7;i++) {
    await click('#next-btn');
    await sleep(80);
    steps.push(await evaluate(`(() => ({
      step: document.querySelector('#rootwizard').dataset.step,
      active: document.querySelector('.disc-pane.is-active').id,
      current: document.querySelector('#step-current').textContent,
      progress: document.querySelector('#discProgress').style.width,
      aria: document.querySelector('#progress-track').getAttribute('aria-valuenow'),
      nextHidden: document.querySelector('#next-btn').hidden,
      finishHidden: document.querySelector('#finish-btn').hidden,
      prevDisabled: document.querySelector('#prev-btn').disabled,
      activeTab: document.querySelector('.disc-tab.is-active').textContent
    }))()`));
  }
  console.log('STEPS', JSON.stringify(steps, null, 2));

  // Go back twice to check.
  await click('#prev-btn'); await sleep(50);
  await click('#prev-btn'); await sleep(50);
  console.log('BACK', JSON.stringify(await evaluate(`({step:document.querySelector('#rootwizard').dataset.step, active:document.querySelector('.disc-pane.is-active').id, nextHidden:document.querySelector('#next-btn').hidden, finishHidden:document.querySelector('#finish-btn').hidden})`)));

  // Jump to last step via tab click, then finish.
  await click('[data-step-btn="7"]'); await sleep(150);
  await click('#finish-btn'); await sleep(300);

  const result = await evaluate(`(() => ({
    title: document.title,
    testHidden: document.querySelector('#screen-test').hidden,
    resultHidden: document.querySelector('#screen-result').hidden,
    score: document.querySelector('#score-string').textContent,
    values: {d:document.querySelector('#score-d').textContent,i:document.querySelector('#score-i').textContent,s:document.querySelector('#score-s').textContent,c:document.querySelector('#score-c').textContent},
    focused: document.activeElement.id,
    live: document.querySelector('#live-status').textContent,
    scrollY: window.scrollY,
    rect: (()=>{const r=document.querySelector('.result-shell').getBoundingClientRect(); return {x:r.x,y:r.y,w:r.width,h:r.height,bottom:r.bottom};})()
  }))()`);
  console.log('RESULT', JSON.stringify(result, null, 2));

  // Check expected score by independent computation.
  const expected = await evaluate(`(() => {
    const score={d:0,i:0,s:0,c:0};
    document.querySelectorAll('.disc-list').forEach(list => {
      const lis=[...list.querySelectorAll('.disc-item')];
      score[lis[0].dataset.type]++; score[lis[lis.length-1].dataset.type]--;
    });
    return score;
  })()`);
  console.log('EXPECTED', JSON.stringify(expected));

  // Restart.
  await click('#restart-btn'); await sleep(250);
  const restarted = await evaluate(`(() => ({
    testHidden: document.querySelector('#screen-test').hidden,
    resultHidden: document.querySelector('#screen-result').hidden,
    step: document.querySelector('#rootwizard').dataset.step,
    order: [...document.querySelectorAll('#draggable-list1 .disc-item')].map(li => li.querySelector('.disc-item__text').textContent),
    progress: document.querySelector('#discProgress').style.width,
    title: document.title,
    focused: document.activeElement.id
  }))()`);
  console.log('RESTARTED', JSON.stringify(restarted, null, 2));

  // Tab keyboard navigation check.
  await evaluate(`document.querySelector('#step-tab-0').focus()`);
  await send('Input.dispatchKeyEvent', {type:'keyDown', key:'ArrowRight', code:'ArrowRight', windowsVirtualKeyCode:39, nativeVirtualKeyCode:39});
  await send('Input.dispatchKeyEvent', {type:'keyUp', key:'ArrowRight', code:'ArrowRight', windowsVirtualKeyCode:39, nativeVirtualKeyCode:39});
  await sleep(100);
  console.log('KEY TAB', JSON.stringify(await evaluate(`({step:document.querySelector('#rootwizard').dataset.step, activeTab:document.querySelector('.disc-tab.is-active').textContent, focus:document.activeElement.id})`)));

  const errors = events.filter(e => ['Runtime.exceptionThrown','Log.entryAdded'].includes(e.method));
  console.log('ERRORS', JSON.stringify(errors.map(e=>({method:e.method, params:e.params})), null, 2));
  ws.close(); chrome.kill('SIGKILL');
})().catch(err => { console.error(err); chrome.kill('SIGKILL'); process.exit(1); });
