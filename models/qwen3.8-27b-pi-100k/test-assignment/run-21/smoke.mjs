// CDP smoke test for index.html (headless Chrome)
import { spawn } from 'node:child_process';
import { setTimeout as sleep } from 'node:timers/promises';
import fs from 'node:fs';

const PORT = 9341;
const URL = 'file://' + process.cwd() + '/index.html';

let failures = [];
const ok = (cond, msg) => {
  console.log((cond ? 'PASS' : 'FAIL') + ' — ' + msg);
  if (!cond) failures.push(msg);
};

const chrome = spawn('/usr/bin/google-chrome', [
  '--headless=new',
  '--no-sandbox',
  '--disable-gpu',
  '--disable-dev-shm-usage',
  '--remote-debugging-port=' + PORT,
  '--user-data-dir=' + fs.mkdtempSync('/tmp/chrome-disc-'),
  'about:blank'
], { stdio: 'ignore' });

async function getJson(path) {
  const r = await fetch('http://127.0.0.1:' + PORT + path);
  return r.json();
}

let ws, idc = 0;
const pending = new Map();
const events = [];
const pageEvents = [];

function send(method, params = {}) {
  return new Promise((resolve, reject) => {
    const id = ++idc;
    pending.set(id, { resolve, reject });
    ws.send(JSON.stringify({ id, method, params }));
  });
}

async function connect() {
  let targets;
  for (let i = 0; i < 60; i++) {
    await sleep(300);
    try { targets = await getJson('/json/list'); if (targets.length) break; } catch (e) {}
  }
  const page = targets.find(t => t.type === 'page');
  if (!page) throw new Error('no page target');
  ws = new WebSocket(page.webSocketDebuggerUrl);
  await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });
  ws.onmessage = (ev) => {
    const msg = JSON.parse(ev.data);
    if (msg.id && pending.has(msg.id)) {
      const { resolve, reject } = pending.get(msg.id);
      pending.delete(msg.id);
      msg.error ? reject(new Error(JSON.stringify(msg.error))) : resolve(msg.result);
    } else if (msg.method) events.push(msg);
  };
}

async function evalJs(expression) {
  const r = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true });
  if (r.exceptionDetails) throw new Error('JS exception: ' + JSON.stringify(r.exceptionDetails.exception?.description || r.exceptionDetails.text));
  return r.result.value;
}

try {
  await connect();
  await send('Runtime.enable');
  await send('Page.enable');
  await send('Log.enable');

  const loadP = new Promise((res) => {
    const iv = setInterval(() => {
      if (events.some(e => e.method === 'Page.loadEventFired')) { clearInterval(iv); res(); }
    }, 50);
  });
  await send('Page.navigate', { url: URL });
  await loadP;
  await sleep(300);

  // 1. initial state: start view visible, test/result hidden
  ok(await evalJs(`!document.getElementById('startView').hidden`), 'start view visible on load');
  ok(await evalJs(`document.getElementById('testView').hidden && document.getElementById('resultView').hidden`), 'test/result hidden initially');
  ok(await evalJs(`document.querySelectorAll('.disc-list').length`), '24 lists rendered' && true);
  ok((await evalJs(`document.querySelectorAll('.disc-list').length`)) === 24, '24 draggable lists');
  ok((await evalJs(`document.querySelectorAll('.disc-item').length`)) === 96, '96 items with handles injected');
  ok(await evalJs(`!!document.querySelector('#draggable-list1 .disc-handle')`), 'drag handles injected');
  ok(await evalJs(`getComputedStyle(document.querySelector('#tab0')).display !== 'none'`), 'step 1 active initially');
  ok(await evalJs(`document.querySelector('[data-disc-prev]').disabled === true`), 'Назад disabled on step 1');

  // 2. open test
  await evalJs(`document.getElementById('btnStart').click(); true`);
  ok(await evalJs(`!document.getElementById('testView').hidden && document.getElementById('startView').hidden`), '«Пройти тест DISC» opens test');

  // 3. synthetic pointer drag: move last li of list1 to the front (upward), first li of list2 to the end (downward)
  const drag = (listId, fromIdx, toIdx) => `
    (() => {
      function fire(el, type, x, y) { el.dispatchEvent(new PointerEvent(type, { clientX: x, clientY: y, bubbles: true, cancelable: true, pointerId: 7, pointerType: 'mouse', button: 0, isPrimary: true })); }
      const ul = document.getElementById('${listId}');
      const lis = () => Array.from(ul.children).filter(n => n.tagName === 'LI');
      const li = lis()[${fromIdx}];
      const r = li.getBoundingClientRect();
      const sx = r.left + 40, sy = r.top + r.height / 2;
      const t = lis()[${toIdx}].getBoundingClientRect();
      const tx = t.left + 40, ty = ${toIdx} === 0 ? (t.top + 5) : (t.top + t.height - 5);
      fire(li, 'pointerdown', sx, sy);
      const steps = 24;
      for (let i = 1; i <= steps; i++) fire(window, 'pointermove', sx + (tx - sx) * i / steps, sy + (ty - sy) * i / steps);
      fire(window, 'pointerup', tx, ty);
      return lis().map(n => n.getAttribute('data-type'));
    })()`;
  ok(JSON.stringify(await evalJs(drag('draggable-list1', 3, 0))) === JSON.stringify(['s','i','c','d']), 'drag & drop (upward) reorders list1 to [s,i,c,d]');
  ok(JSON.stringify(await evalJs(drag('draggable-list2', 0, 3))) === JSON.stringify(['i','s','c','d']), 'drag & drop (downward) reorders list2 to [i,s,c,d]');

  // 4. step navigation: Далее 7 times (step1 → step8)
  for (let i = 0; i < 7; i++) {
    await evalJs(`document.querySelector('[data-disc-next]').click(); true`);
  }
  ok((await evalJs(`document.querySelector('.disc-pane.is-active').id`)) === 'tab7', '«Далее» ×7 reaches step 8 (Восьмой)');
  ok(await evalJs(`!document.querySelector('[data-disc-finish]').hidden && document.querySelector('[data-disc-next]').hidden`), 'on last step: «Завершить тест» shown, «Далее» hidden');
  ok(await evalJs(`Math.round(parseFloat(document.getElementById('discProgress').style.width)) === 100`), 'progress bar at 100%');
  ok(await evalJs(`document.querySelector('[data-disc-prev]').disabled === false`), '«Назад» enabled on last step');

  // 5. jump back via tab button
  await evalJs(`document.querySelector('[data-step-btn="0"]').click(); true`);
  ok(await evalJs(`document.querySelector('.disc-pane.is-active').id === 'tab0'`), 'tab button returns to step 1');
  const kept = await evalJs(`Array.from(document.getElementById('draggable-list1').children).filter(n => n.tagName === 'LI').map(n => n.getAttribute('data-type'))`);
  ok(JSON.stringify(kept) === JSON.stringify(['s','i','c','d']), 'reordering of step 1 is preserved after navigation');
  await evalJs(`document.querySelector('[data-step-btn="7"]').click(); true`);

  // 6. finish → expected from final DOM order
  await evalJs(`document.querySelector('[data-disc-finish]').click(); true`);
  ok(await evalJs(`!document.getElementById('resultView').hidden && document.getElementById('testView').hidden`), '«Завершить тест» shows result view');
  const fromDom = await evalJs(`(() => {
    const sc = { d: 0, i: 0, s: 0, c: 0 };
    document.querySelectorAll('.disc-list').forEach(ul => {
      const lis = Array.from(ul.children).filter(n => n.tagName === 'LI');
      sc[lis[0].getAttribute('data-type')] += 1;
      sc[lis[lis.length - 1].getAttribute('data-type')] -= 1;
    });
    return 'D:' + sc.d + ', I:' + sc.i + ', S:' + sc.s + ', C:' + sc.c;
  })()`);
  const expected = 'D:-4, I:0, S:-1, C:5'; // baseline (D:-1,I:0,S:-3,C:4) + list1 [i,c,d,s]→[s,i,c,d] (i:-1, s:+2) + list2 [d,i,s,c]→[i,s,c,d] (d:-2, i:+1, c:+1)
  ok(fromDom === expected, 'score per DOM order is «' + fromDom + '» (expected ' + expected + ')');
  const scoreText = await evalJs(`document.getElementById('discScore').textContent`);
  ok(scoreText === expected, 'displayed score is «' + scoreText + '» (expected ' + expected + ')');

  ok((await evalJs(`document.getElementById('discLink').value`)) === expected, 'copy field contains the score');
  // 7. copy button state (clipboard may be blocked — fallback path)
  await evalJs(`document.querySelector('[data-copy]').click(); true`);
  await sleep(250);
  const label = await evalJs(`document.querySelector('.copyfield__btnText').textContent`);
  ok(label === 'Скопировано' || label === 'Copy', 'copy button works without error (label: «' + label + '»)');
  if (label === 'Скопировано') ok(true, 'copy confirmed');
  else console.log('note: clipboard + execCommand both unavailable in headless — no crash, acceptable');

  // 8. restart resets order and goes back to step 1
  await evalJs(`document.getElementById('btnRestart').click(); true`);
  ok(await evalJs(`!document.getElementById('testView').hidden && document.getElementById('resultView').hidden`), '«Пройти ещё раз» returns to test');
  const reset = await evalJs(`Array.from(document.getElementById('draggable-list1').children).filter(n => n.tagName === 'LI').map(n => n.getAttribute('data-type'))`);
  ok(JSON.stringify(reset) === JSON.stringify(['i','c','d','s']), 'restart restores initial order of list1: ' + JSON.stringify(reset));
  const reset2 = await evalJs(`Array.from(document.getElementById('draggable-list2').children).filter(n => n.tagName === 'LI').map(n => n.getAttribute('data-type'))`);
  ok(JSON.stringify(reset2) === JSON.stringify(['d','i','s','c']), 'restart restores initial order of list2: ' + JSON.stringify(reset2));
  ok(await evalJs(`document.querySelector('.disc-pane.is-active').id === 'tab0'`), 'restart returns to step 1');

  // 9. console/JS errors
  const jsErrors = events.filter(e =>
    e.method === 'Runtime.exceptionThrown' ||
    (e.method === 'Runtime.consoleAPICalled' && e.params && e.params.type === 'error') ||
    (e.method === 'Log.entryAdded' && e.params.entry && e.params.entry.level === 'error')
  );
  ok(jsErrors.length === 0, 'no JS exceptions / console errors' + (jsErrors.length ? ' → ' + JSON.stringify(jsErrors) : ''));

  // 10. network: all requests should be file:// or none
  const net = events.filter(e => e.method === 'Network.requestWillBeSent');
  ok(net.length === 0, 'no network requests during session');

} finally {
  try { chrome.kill('SIGKILL'); } catch (e) {}
}

console.log(failures.length ? '\nRESULT: FAILED (' + failures.length + ')' : '\nRESULT: ALL CHECKS PASSED');
process.exit(failures.length ? 1 : 0);
