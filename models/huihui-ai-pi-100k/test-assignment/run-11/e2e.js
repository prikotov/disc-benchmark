/* E2E test of index.html via CDP (headless Chrome) */
const { spawn } = require('node:child_process');
const http = require('node:http');

const PAGE = 'file:///tmp/disc-pi-k25iafj4/run/index.html';
const PORT = 9333;

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function httpJson(path, method = 'GET') {
  return new Promise((resolve, reject) => {
    const req = http.request({ host: '127.0.0.1', port: PORT, path, method, headers: { 'content-type': 'application/json' } }, (res) => {
      let d = '';
      res.on('data', (c) => (d += c));
      res.on('end', () => { try { resolve(JSON.parse(d)); } catch (e) { resolve(d); } });
    });
    req.on('error', reject);
    req.end();
  });
}

let passed = 0, failed = 0;
function check(name, cond, extra) {
  if (cond) { passed++; console.log('  PASS  ' + name); }
  else { failed++; console.log('  FAIL  ' + name + (extra !== undefined ? '  -> ' + JSON.stringify(extra) : '')); }
}

(async () => {
  const chrome = spawn('google-chrome', [
    '--headless=new', '--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage',
    `--remote-debugging-port=${PORT}`, '--user-data-dir=/tmp/chrome-disc-profile-e2e',
    '--window-size=1400,1000', 'about:blank'
  ], { stdio: 'ignore' });

  try {
    // wait for devtools
    let targets = null;
    for (let i = 0; i < 50; i++) {
      await sleep(200);
      try { targets = await httpJson('/json'); if (Array.isArray(targets) && targets.length) break; } catch (e) {}
    }
    if (!targets) throw new Error('chrome devtools not up');

    // open page target
    let page;
    try { page = await httpJson('/json/new?' + encodeURIComponent(PAGE), 'PUT'); }
    catch (e) { page = await httpJson('/json/new?' + encodeURIComponent(PAGE)); }
    const wsUrl = page.webSocketDebuggerUrl;
    await sleep(300);

    const ws = new WebSocket(wsUrl);
    let idc = 0; const pending = new Map();
    const exceptions = []; const consoleErrs = []; const nonLocalRequests = [];
    let nextId = 1;

    const send = (method, params) => new Promise((resolve) => {
      const id = nextId++;
      pending.set(id, resolve);
      ws.send(JSON.stringify({ id, method, params }));
    });
    ws.onmessage = (m) => {
      const msg = JSON.parse(m.data);
      if (msg.id && pending.has(msg.id)) { pending.get(msg.id)(msg.result); pending.delete(msg.id); return; }
      if (msg.method === 'Runtime.exceptionThrown') exceptions.push(msg.params.exceptionDetails && (msg.params.exceptionDetails.exception && msg.params.exceptionDetails.exception.description || msg.params.exceptionDetails.text));
      if (msg.method === 'Runtime.consoleAPICalled' && msg.params.type === 'error') consoleErrs.push(JSON.stringify(msg.params.args).slice(0, 200));
      if (msg.method === 'Network.requestWillBeSent' && !/^(file|data):/.test(msg.params.request.url)) nonLocalRequests.push(msg.params.request.url);
    };
    await new Promise((r) => (ws.onopen = r));
    await send('Runtime.enable', {});
    await send('Page.enable', {});
    await send('Network.enable', {});
    await send('Page.navigate', { url: PAGE });
    await sleep(1500);

    const ev = (expression) => send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true })
      .then((r) => { if (r && r.exceptionDetails) throw new Error('EVAL ERR: ' + JSON.stringify(r.exceptionDetails).slice(0, 400)); return r && r.result && r.result.value; });

    console.log('== initial state ==');
    const init = await ev(`(() => {
      const $ = (s) => document.querySelector(s), $$ = (s) => Array.from(document.querySelectorAll(s));
      return {
        panes: $$('#panes .disc-pane').length,
        lists: $$('#panes ul.disc-list').length,
        items: $$('#panes li.disc-item').length,
        tabs: $$('#discTabs .disc-tab').length,
        progress: $('#discProgress').style.width,
        modalOpen: $('#discWizard').classList.contains('is-open'),
        firstPaneActive: $('.disc-pane').classList.contains('is-active')
      };
    })()`);
    check('8 panes', init.panes === 8, init.panes);
    check('24 lists', init.lists === 24, init.lists);
    check('96 items', init.items === 96, init.items);
    check('8 tabs', init.tabs === 8, init.tabs);
    check('progress 12.5% at step 0 (closed modal)', parseFloat(init.progress) === 12.5, init.progress);
    check('modal initially closed', init.modalOpen === false);

    console.log('== open modal ==');
    await ev(`document.querySelector('[data-modal-open="discWizard"]').click(); true`);
    const opened = await ev(`(() => ({
      open: document.querySelector('#discWizard').classList.contains('is-open'),
      scrollLocked: document.documentElement.classList.contains('no-scroll'),
      btnPrevDisabled: document.querySelector('#btnPrev').disabled,
      btnNextHidden: document.querySelector('#btnNext').hidden,
      btnFinishHidden: document.querySelector('#btnFinish').hidden
    }))()`);
    check('modal opens', opened.open === true);
    check('body scroll locked', opened.scrollLocked === true);
    check('Назад disabled on step 0', opened.btnPrevDisabled === true);
    check('Далее visible, Завершить hidden on step 0', opened.btnNextHidden === false && opened.btnFinishHidden === true);

    console.log('== drag & drop (mouse, whole item) ==');
    // move first item of list #0 (Экспресcивный i -> Покладистый c -> Волевой d -> Осторожный s)
    // initial: i,c,d,s => pos0=i,pos3=s. After moving item0 to bottom: c,d,s,i => pos0=c,pos3=i
    const dragRes = await ev(`(() => {
      const $ = (s) => document.querySelector(s);
      const ul = document.querySelector('#panes ul.disc-list');
      const items = Array.from(ul.children);
      const li0 = items[0], li3 = items[3];
      const r0 = li0.getBoundingClientRect();
      const r3 = li3.getBoundingClientRect();
      const cx = r0.left + r0.width / 2, cy0 = r0.top + r0.height / 2;
      const targetY = cy0 + ((r3.top + r3.height/2) - (r0.top + r0.height/2)) + 10;
      const PE = (el, type, x, y) => el.dispatchEvent(new PointerEvent(type, {bubbles:true, cancelable:true, pointerId:1, pointerType:'mouse', isPrimary:true, button:0, buttons:1, clientX:x, clientY:y}));
      PE(li0, 'pointerdown', cx, cy0);
      const steps = 6;
      for (let i = 1; i <= steps; i++) {
        PE(window, 'pointermove', cx + 1, cy0 + (targetY - cy0) * i / steps);
      }
      PE(window, 'pointerup', cx + 1, targetY);
      return {
        before: items.map(li => li.dataset.type),
        after: Array.from(ul.children).map(li => li.dataset.type || li.className),
        draggingLeft: li0.classList.contains('is-dragging'),
        phLeft: Array.from(ul.children).some(li => li.classList.contains('disc-ph'))
      };
    })()`);
    check('item moved from pos0 to pos3', JSON.stringify(dragRes.after) === JSON.stringify(['c','d','s','i']), dragRes);
    check('no placeholder/drag state left in DOM', dragRes.phLeft === false && dragRes.draggingLeft === false, dragRes);

    console.log('== keyboard reorder (ArrowDown/ArrowUp) ==');
    // order before: [c,d,s,i]; move first item down (-> [d,c,s,i]), then back up (-> [c,d,s,i])
    const keyRes = await ev(`(() => {
      const ul = document.querySelector('#panes ul.disc-list');
      const li0 = ul.children[0];
      li0.focus();
      li0.dispatchEvent(new KeyboardEvent('keydown', {bubbles:true, cancelable:true, key:'ArrowDown'}));
      const mid = Array.from(ul.children).map(li => li.dataset.type);
      const li0b = Array.from(ul.children).find(li => li.dataset.type === li0.dataset.type);
      li0b.dispatchEvent(new KeyboardEvent('keydown', {bubbles:true, cancelable:true, key:'ArrowUp'}));
      return { mid, final: Array.from(ul.children).map(li => li.dataset.type) };
    })()`);
    check('ArrowDown moves item down', JSON.stringify(keyRes.mid) === JSON.stringify(['d','c','s','i']), keyRes.mid);
    check('ArrowUp moves item back', JSON.stringify(keyRes.final) === JSON.stringify(['c','d','s','i']), keyRes.final);

    console.log('== steps navigation ==');
    const nav1 = await ev(`(() => {
      document.querySelector('#btnNext').click();
      const t = document.querySelector('#discTabs .disc-tab');
      t.setAttribute('data-x','1');
      return {
        tab2active: document.querySelectorAll('#discTabs .disc-tab')[1].classList.contains('is-active'),
        pane2: document.querySelectorAll('#panes .disc-pane')[1].classList.contains('is-active'),
        progress: document.querySelector('#discProgress').style.width,
        btnPrevDisabled: document.querySelector('#btnPrev').disabled
      };
    })()`);
    check('next -> step 2', nav1.tab2active === true && nav1.pane2 === true, nav1);
    const dispCheck = await ev(`(() => ({
      nextBtn: getComputedStyle(document.querySelector('#btnNext')).display,
      finishBtn: getComputedStyle(document.querySelector('#btnFinish')).display
    }))()`);
    check('Далее visible / Завершить not (computed display)', dispCheck.nextBtn !== 'none' && dispCheck.finishBtn === 'none', dispCheck);
    check('progress 25% at step 1', parseFloat(nav1.progress) === 25, nav1.progress);
    check('Назад enabled at step 1', nav1.btnPrevDisabled === false);

    await ev(`document.querySelectorAll('#discTabs .disc-tab')[3].click(); true`);
    const nav2 = await ev(`(() => ({
      pane4: document.querySelectorAll('#panes .disc-pane')[3].classList.contains('is-active'),
      progress: document.querySelector('#discProgress').style.width
    }))()`);
    check('tab jump -> step 4', nav2.pane4 === true, nav2);
    check('progress 50% at step 3', parseFloat(nav2.progress) === 50, nav2.progress);

    console.log('== finish on last step ==');
    await ev(`(() => { let g=0; while (document.querySelector('#btnNext') && !document.querySelector('#btnNext').hidden && g<8){ document.querySelector('#btnNext').click(); g++; } true })()`);
    const last = await ev(`(() => ({
      btnNextHidden: document.querySelector('#btnNext').hidden,
      btnFinishShown: !document.querySelector('#btnFinish').hidden,
      progress: document.querySelector('#discProgress').style.width
    }))()`);
    check('Завершить shown at step 8', last.btnFinishShown === true && last.btnNextHidden === true, last);
    const dispCheck8 = await ev(`(() => ({
      nextBtn: getComputedStyle(document.querySelector('#btnNext')).display,
      finishBtn: getComputedStyle(document.querySelector('#btnFinish')).display
    }))()`);
    check('computed display: Далее hidden, Завершить visible', dispCheck8.nextBtn === 'none' && dispCheck8.finishBtn !== 'none', dispCheck8);
    check('progress 100%', parseFloat(last.progress) === 100, last.progress);

    // expected score: computed from DOM (independent of app's collectScore)
    const expected = await ev(`(() => {
      const lists = Array.from(document.querySelectorAll('#panes ul.disc-list'));
      const score = {d:0,i:0,s:0,c:0};
      lists.forEach(ul => {
        const its = Array.from(ul.children).filter(li => li.tagName === 'LI' && !li.classList.contains('disc-ph'));
        score[its[0].dataset.type] += 1;
        score[its[its.length-1].dataset.type] -= 1;
      });
      return score;
    })()`);

    await ev(`document.querySelector('#btnFinish').click(); true`);
    const res1 = await ev(`(() => {
      const line = document.querySelector('.result-scoreline');
      return {
        shown: !document.querySelector('#discResult').classList.contains('is-hidden'),
        text: line ? line.textContent : null,
        stepsHidden: document.querySelector('#stepWrap').style.display,
        tabsHidden: document.querySelector('#discTabs').style.display
      };
    })()`);
    check('result pane shown', res1.shown === true, res1);
    check('steps + tabs hidden in result', res1.stepsHidden === 'none' && res1.tabsHidden === 'none', res1);
    const m = /D:\s*(-?\d+)\s*,\s*I:\s*(-?\d+)\s*,\s*S:\s*(-?\d+)\s*,\s*C:\s*(-?\d+)/.exec(res1.text || '');
    check('score line present (D:x, I:y, S:z, C:w)', !!m, res1.text);
    if (m) {
      const got = { d:+m[1], i:+m[2], s:+m[3], c:+m[4] };
      check('score D matches', got.d === expected.d, {got, expected});
      check('score I matches', got.i === expected.i, {got, expected});
      check('score S matches', got.s === expected.s, {got, expected});
      check('score C matches', got.c === expected.c, {got, expected});
    }
    // untouched lists: 23 identical + 1 changed, so expected should be:
    // initial order pos0/pos3 across all 24 lists is fixed; we only changed list 0.
    const res2 = await ev(`(() => ({
      bars: Array.from(document.querySelectorAll('.rrow__val')).map(v => v.textContent),
      note: (document.querySelector('.result-topnote')||{}).textContent || '',
      descs: document.querySelectorAll('.result-desc .type-card').length
    }))()`);
    check('4 score bars rendered', res2.bars.length === 4, res2.bars);
    check('4 type descriptions rendered', res2.descs === 4, res2.descs);

    console.log('== retake ==');
    await ev(`document.querySelector('#btnRetake').click(); true`);
    const back = await ev(`(() => {
      const ul0 = document.querySelector('#panes ul.disc-list');
      return {
        order0: Array.from(ul0.children).map(li => li.dataset.type),
        step0active: document.querySelectorAll('#panes .disc-pane')[0].classList.contains('is-active'),
        firstTab: document.querySelectorAll('#discTabs .disc-tab')[0].classList.contains('is-active'),
        resultHidden: document.querySelector('#discResult').classList.contains('is-hidden'),
        stepsShown: document.querySelector('#stepWrap').style.display,
        progress: document.querySelector('#discProgress').style.width
      };
    })()`);
    check('lists reset to initial order', JSON.stringify(back.order0) === JSON.stringify(['i','c','d','s']), back.order0);
    check('back at step 1 with active tab', back.step0active === true && back.firstTab === true, back);
    check('result hidden, steps visible, progress 12.5%', back.resultHidden === true && back.stepsShown === '' && parseFloat(back.progress) === 12.5, back);

    console.log('== finish with untouched ordering (all 24 lists) ==');
    // expected value for pure initial order — computed from data
    await ev(`(() => { let g=0; while (!document.querySelector('#btnFinish').hidden && g<8){ g++; if (document.querySelector('#btnNext') && !document.querySelector('#btnNext').hidden) document.querySelector('#btnNext').click(); } true })()`);
    const untouched = await ev(`(() => {
      document.querySelector('#btnFinish').click();
      const line = document.querySelector('.result-scoreline');
      const score = {d:0,i:0,s:0,c:0};
      Array.from(document.querySelectorAll('#panes ul.disc-list')).forEach(ul => {
        const its = Array.from(ul.children).filter(li => li.tagName === 'LI');
        score[its[0].dataset.type] += 1; score[its[its.length-1].dataset.type] -= 1;
      });
      return { text: line.textContent, score, sum: score.d+score.i+score.s+score.c };
    })()`);
    const mu = /D:\s*(-?\d+)\s*,\s*I:\s*(-?\d+)\s*,\s*S:\s*(-?\d+)\s*,\s*C:\s*(-?\d+)/.exec(untouched.text);
    check('untouched result line', !!mu, untouched.text);
    if (mu) {
      check('sum of 4 scores is 0', untouched.sum === 0, untouched.sum);
      check('each |score| <= 24', ['d','i','s','c'].every(k => Math.abs(untouched.score[k]) <= 24), untouched.score);
      check('value consistency D', (+mu[1]) === untouched.score.d, untouched);
      check('value consistency C', (+mu[4]) === untouched.score.c, untouched);
    }

    console.log('== close modal (Esc) ==');
    await ev(`document.dispatchEvent(new KeyboardEvent('keydown', {bubbles:true, key:'Escape'})); true`);
    const closed = await ev(`(() => ({
      open: document.querySelector('#discWizard').classList.contains('is-open'),
      scrollFree: !document.documentElement.classList.contains('no-scroll')
    }))()`);
    check('Esc closes modal', closed.open === false, closed);
    check('scroll unlocked', closed.scrollFree === true, closed);

    console.log('== hygiene ==');
    check('no JS exceptions', exceptions.length === 0, exceptions);
    check('no console errors', consoleErrs.length === 0, consoleErrs);
    check('no external network requests', nonLocalRequests.length === 0, nonLocalRequests);

    await new Promise((r) => { ws.onclose = () => r(); try { ws.close(); } catch (e) { r(); } });
    console.log('\nRESULT: ' + passed + ' passed, ' + failed + ' failed');
    process.exitCode = failed ? 1 : 0;
  } finally {
    chrome.kill('SIGKILL');
  }
})().catch((e) => { console.error('E2E ERROR:', e); process.exit(2); });
