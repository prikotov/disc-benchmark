import { spawn } from 'node:child_process';
import { writeFileSync } from 'node:fs';

const chrome = spawn('google-chrome', [
  '--headless=new', '--disable-gpu', '--no-sandbox', '--hide-scrollbars',
  '--remote-debugging-port=9222', '--user-data-dir=/tmp/disc-chrome-test',
  '--window-size=1440,1100',
  'file://' + process.cwd() + '/index.html'
], { stdio: ['ignore', 'ignore', 'ignore'] });

const sleep = (ms) => new Promise(r => setTimeout(r, ms));
let target;
for (let i = 0; i < 60; i++) {
  try {
    const res = await fetch('http://127.0.0.1:9222/json');
    const list = await res.json();
    target = list.find(x => x.type === 'page' && x.url.includes('index.html'));
    if (target) break;
  } catch {}
  await sleep(150);
}
if (!target) { console.error('no target'); chrome.kill(); process.exit(1); }

const ws = new WebSocket(target.webSocketDebuggerUrl);
await new Promise((resolve, reject) => { ws.onopen = resolve; ws.onerror = reject; });
let id = 0;
const pending = new Map();
const events = [];
ws.onmessage = (e) => {
  const msg = JSON.parse(e.data);
  if (msg.id) {
    const p = pending.get(msg.id);
    if (p) { pending.delete(msg.id); msg.error ? p.reject(new Error(JSON.stringify(msg.error))) : p.resolve(msg.result); }
  } else {
    events.push(msg);
  }
};
function send(method, params = {}) {
  return new Promise((resolve, reject) => {
    const n = ++id;
    pending.set(n, { resolve, reject });
    ws.send(JSON.stringify({ id: n, method, params }));
  });
}
async function evalJS(expression, awaitPromise = false) {
  const r = await send('Runtime.evaluate', { expression, awaitPromise, returnByValue: true, userGesture: true });
  if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails));
  return r.result.value;
}
await send('Page.enable');
await send('Runtime.enable');
await send('Network.enable');
await send('Log.enable');
await sleep(500);

const checks = {};
checks.title = await evalJS('document.title');
checks.lists = await evalJS('document.querySelectorAll(".rank-list").length');
checks.options = await evalJS('document.querySelectorAll(".option").length');
checks.tabs = await evalJS('document.querySelectorAll(".step-tab").length');
checks.visiblePanes = await evalJS('Array.from(document.querySelectorAll(".step-pane")).filter(p=>!p.hidden).length');
checks.externalRefs = await evalJS(`JSON.stringify([...document.querySelectorAll('script[src],link[href],img[src],iframe[src]')].map(e=>e.src||e.href))`);
checks.initialTexts = await evalJS(`JSON.stringify([...document.querySelectorAll('.rank-list')].slice(0,2).map(l=>[...l.children].map(li=>li.querySelector('.option-text').textContent)))`);
checks.initialTypes = await evalJS(`JSON.stringify([...document.querySelectorAll('.rank-list')].slice(0,2).map(l=>[...l.children].map(li=>li.dataset.type)))`);

// Capture page screenshot
const shot = await send('Page.captureScreenshot', { format: 'png' });
writeFileSync('shot-start.png', Buffer.from(shot.data, 'base64'));

// Go to last step and finish
await evalJS(`document.querySelectorAll('.step-tab')[7].click()`);
await sleep(200);
checks.lastStep = await evalJS(`JSON.stringify({hidden:document.querySelector('#finishBtn').hidden, nextHidden:document.querySelector('#nextBtn').hidden, counter:document.querySelector('#stepCounter').textContent, pct:document.querySelector('#progressPercent').textContent, visible:Array.from(document.querySelectorAll('.step-pane')).map(p=>!p.hidden)})`);
const shotLast = await send('Page.captureScreenshot', { format: 'png' });
writeFileSync('shot-last.png', Buffer.from(shotLast.data, 'base64'));
await evalJS(`document.querySelector('#finishBtn').click()`);
await sleep(300);
checks.result = await evalJS(`JSON.stringify({testHidden:document.querySelector('#wizardmodal').hidden,resultHidden:document.querySelector('#result').hidden,scoreLine:document.querySelector('#scoreLine').textContent,d:document.querySelector('#scoreD').textContent,i:document.querySelector('#scoreI').textContent,s:document.querySelector('#scoreS').textContent,c:document.querySelector('#scoreC').textContent,markers:['D','I','S','C'].map(k=>document.querySelector('#marker'+k).style.left)})`);
const shotResult = await send('Page.captureScreenshot', { format: 'png' });
writeFileSync('shot-result.png', Buffer.from(shotResult.data, 'base64'));

// Restart and verify order restored
await evalJS(`document.querySelector('#restartBtn').click()`);
await sleep(200);
checks.restart = await evalJS(`JSON.stringify({testHidden:document.querySelector('#wizardmodal').hidden,resultHidden:document.querySelector('#result').hidden,step:document.querySelectorAll('.step-pane')[0].hidden,texts:[...document.querySelector('.rank-list').children].map(li=>li.querySelector('.option-text').textContent)})`);

// Keyboard reorder first row down twice
await evalJS(`document.querySelector('.rank-list .option').focus()`);
await send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'ArrowDown', code: 'ArrowDown', windowsVirtualKeyCode: 40, nativeVirtualKeyCode: 40 });
await send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'ArrowDown', code: 'ArrowDown', windowsVirtualKeyCode: 40, nativeVirtualKeyCode: 40 });
await sleep(80);
checks.keyboardOrder = await evalJS(`JSON.stringify([...document.querySelector('.rank-list').children].map(li=>({t:li.querySelector('.option-text').textContent,p:li.dataset.pos,r:li.querySelector('.option-rank').textContent})))`);

// Reset for pointer drag
await evalJS(`document.querySelector('#restartBtn').click()`);
await sleep(100);

// Real mouse drag: first option in first card to below last option
const dragInfo = await evalJS(`(()=>{const l=document.querySelector('.rank-list');const a=l.children[0].getBoundingClientRect();const b=l.children[3].getBoundingClientRect();return {sx:a.left+a.width/2,sy:a.top+a.height/2,ex:b.left+b.width/2,ey:b.top+b.height-4,order:[...l.children].map(li=>li.querySelector('.option-text').textContent)}})()`);
await send('Input.dispatchMouseEvent', { type: 'mousePressed', x: dragInfo.sx, y: dragInfo.sy, button: 'left', clickCount: 1 });
for (let i = 1; i <= 12; i++) {
  await send('Input.dispatchMouseEvent', { type: 'mouseMoved', x: dragInfo.sx + (dragInfo.ex-dragInfo.sx)*i/12, y: dragInfo.sy + (dragInfo.ey-dragInfo.sy)*i/12, button: 'left', buttons: 1 });
  await sleep(20);
}
// extra move near bottom
await send('Input.dispatchMouseEvent', { type: 'mouseMoved', x: dragInfo.ex, y: dragInfo.ey + 5, button: 'left', buttons: 1 });
await sleep(80);
const during = await evalJS(`JSON.stringify({ghosts:document.querySelectorAll('.drag-ghost').length,dragging:document.querySelectorAll('.is-dragging').length,order:[...document.querySelector('.rank-list').children].map(li=>li.querySelector('.option-text').textContent)})`);
await send('Input.dispatchMouseEvent', { type: 'mouseReleased', x: dragInfo.ex, y: dragInfo.ey + 5, button: 'left', clickCount: 1 });
await sleep(150);
checks.drag = { before: dragInfo.order, during: JSON.parse(during), after: await evalJS(`JSON.stringify([...document.querySelector('.rank-list').children].map(li=>({t:li.querySelector('.option-text').textContent,p:li.dataset.pos})))`) };
checks.postDragGhosts = await evalJS(`JSON.stringify({ghosts:document.querySelectorAll('.drag-ghost').length,dragging:document.querySelectorAll('.is-dragging').length,bodyClass:document.body.className})`);

// Finish again to verify score changed by one D/I swap at list 1
await evalJS(`document.querySelectorAll('.step-tab')[7].click(); document.querySelector('#finishBtn').click()`);
await sleep(250);
checks.resultAfterDrag = await evalJS(`JSON.stringify({scoreLine:document.querySelector('#scoreLine').textContent,d:document.querySelector('#scoreD').textContent,i:document.querySelector('#scoreI').textContent,s:document.querySelector('#scoreS').textContent,c:document.querySelector('#scoreC').textContent})`);

checks.errors = events.filter(e => e.method === 'Runtime.exceptionThrown' || (e.method === 'Log.entryAdded' && ['error','warning'].includes(e.params.entry.level))).map(e => e.method === 'Runtime.exceptionThrown' ? e.params.exceptionDetails.text : e.params.entry.text);
checks.requests = events.filter(e => e.method === 'Network.requestWillBeSent').map(e => e.params.request.url).filter(u => !u.startsWith('file:') && !u.startsWith('data:'));
console.log(JSON.stringify(checks, null, 2));
ws.close();
chrome.kill();
