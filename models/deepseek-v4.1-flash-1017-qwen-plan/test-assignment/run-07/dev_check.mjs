// Smoke + interaction test копии DISC через Chrome DevTools Protocol (без внешних зависимостей).
import { spawn } from 'node:child_process';
import { writeFileSync } from 'node:fs';

const FILE = process.argv[2] || process.cwd() + '/index.html';
const PORT = 9400;

const chrome = spawn('google-chrome', [
  '--headless=new', `--remote-debugging-port=${PORT}`,
  `--user-data-dir=/tmp/disc-chrome-${Date.now()}`,
  '--no-first-run', '--no-default-browser-check', '--disable-gpu',
  '--window-size=1280,960', '--hide-scrollbars',
  'about:blank'
], { stdio: 'ignore' });

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function getWsUrl() {
  for (let i = 0; i < 80; i++) {
    try {
      const res = await fetch(`http://127.0.0.1:${PORT}/json/list`);
      const list = await res.json();
      const page = list.find((t) => t.type === 'page');
      if (page) return page.webSocketDebuggerUrl;
    } catch (e) { /* not up yet */ }
    await sleep(250);
  }
  throw new Error('chrome did not start');
}

const wsUrl = await getWsUrl();
const ws = new WebSocket(wsUrl);
await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });

let id = 0;
const pending = new Map();
const events = [];
const requests = [];
ws.onmessage = (m) => {
  const msg = JSON.parse(m.data);
  if (msg.id && pending.has(msg.id)) {
    const { res, rej } = pending.get(msg.id);
    pending.delete(msg.id);
    msg.error ? rej(new Error(JSON.stringify(msg.error))) : res(msg.result);
  } else if (msg.method) {
    events.push(msg);
    if (msg.method === 'Network.requestWillBeSent') requests.push(msg.params.request.url);
  }
};
const send = (method, params = {}) => new Promise((res, rej) => {
  const mid = ++id;
  pending.set(mid, { res, rej });
  ws.send(JSON.stringify({ id: mid, method, params }));
});

const evaluate = async (expr) => {
  const r = await send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true });
  if (r.exceptionDetails) throw new Error('JS error: ' + JSON.stringify(r.exceptionDetails));
  return r.result.value;
};

await send('Page.enable');
await send('Runtime.enable');
await send('Network.enable');

await send('Page.navigate', { url: 'file://' + FILE });
await sleep(1200);

const results = {};

// ---------- 1. статическая структура
results.startVisible = await evaluate(`!document.getElementById('screen-start').hidden`);
results.itemsInDom = await evaluate(`document.querySelectorAll('.item').length`);
results.listsInDom = await evaluate(`document.querySelectorAll('.list').length`);
results.panes = await evaluate(`document.querySelectorAll('[data-step-pane]').length`);
results.duplicates = await evaluate(`(() => {
  const t = [...document.querySelectorAll('.item__text')].map(e => e.textContent);
  return t.filter((v, i) => t.indexOf(v) !== i).length;
})()`);
results.latinC = await evaluate(`[...document.querySelectorAll('.item__text')].filter(e => e.textContent.indexOf('Экспресcивный') === 0).length`);
results.svgCount = await evaluate(`document.querySelectorAll('svg').length`);
results.imgCount = await evaluate(`document.querySelectorAll('img,picture,video,iframe,link[rel=stylesheet],script[src]').length`);

// ---------- 2. старт
await evaluate(`document.getElementById('btn-start').click()`);
await sleep(300);
results.quizVisible = await evaluate(`!document.getElementById('screen-quiz').hidden`);
results.stepLabel = await evaluate(`document.getElementById('step-label').textContent`);
results.activePanes = await evaluate(`document.querySelectorAll('.pane:not([hidden])').length`);
results.prevDisabled = await evaluate(`document.getElementById('btn-prev').disabled`);

// ---------- 3. drag мышью (последний → первый) в первом блоке
const r1 = await evaluate(`(() => {
  const ul = document.querySelectorAll('.list')[0];
  const lis = [...ul.children];
  const a = lis[3].getBoundingClientRect(), b = lis[0].getBoundingClientRect();
  return { x: a.x + a.width / 2, from: a.y + a.height / 2, to: b.y + 4 };
})()`);
const mouse = (type, x, y, buttons = 1) => send('Input.dispatchMouseEvent', { type, x, y, button: 'left', buttons, clickCount: 1 });
await mouse('mousePressed', r1.x, r1.from);
await sleep(30);
const draggingDuringMove = await (async () => {
  let seen = 0;
  for (let k = 1; k <= 8; k++) {
    await mouse('mouseMoved', r1.x, r1.from + (r1.to - r1.from) * (k / 8));
    await sleep(25);
    if (k === 4) seen = await evaluate(`document.querySelectorAll('.item.is-dragging').length`);
  }
  return seen;
})();
await mouse('mouseReleased', r1.x, r1.to, 0);
await sleep(200);
results.dragMouse = await evaluate(`[...document.querySelectorAll('.list')[0].children].map(li => li.dataset.type).join('')`);
results.dragMouseClassWhileMoving = draggingDuringMove;
results.dragCleanup = await evaluate(`document.querySelectorAll('.item.is-dragging').length + '/' + document.querySelectorAll('.list[data-dragging]').length`);
results.posNumbers = await evaluate(`[...document.querySelectorAll('.list')[0].children].map(li => getComputedStyle(li, '::before').content.replace(/[^0-9]/g, '')).join('')`);
results.itemTextOnly = await evaluate(`[...document.querySelectorAll('.list')[0].children].map(li => li.textContent.trim()).join('|')`);
results.ariaLabel = await evaluate(`document.querySelectorAll('.list')[0].children[0].getAttribute('aria-label')`);

// ---------- 4. клавиатура: стрелки перемещают качество
await evaluate(`(() => {
  const li = document.querySelectorAll('.list')[1].children[0];
  li.focus();
  li.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowDown', bubbles: true }));
  li.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowDown', bubbles: true }));
})()`);
results.keyboardOrder = await evaluate(`[...document.querySelectorAll('.list')[1].children].map(li => li.dataset.type).join('')`);

// ---------- 5. навигация, конец теста
for (let i = 0; i < 7; i++) { await evaluate(`document.getElementById('btn-next').click()`); await sleep(50); }
results.lastStep = await evaluate(`document.getElementById('step-label').textContent`);
results.finishVisible = await evaluate(`!document.getElementById('btn-finish').hidden`);
results.nextHidden = await evaluate(`document.getElementById('btn-next').hidden`);
results.progress = await evaluate(`document.getElementById('progress-bar').style.width`);

const expected = await evaluate(`(() => {
  const maj = [], min = [];
  [...document.querySelectorAll('.list')].forEach(ul => [...ul.children].forEach((li, i) => {
    if (i === 0) maj.push(li.dataset.type);
    if (i === 3) min.push(li.dataset.type);
  }));
  const c = (a, ch) => a.filter(v => v === ch).length;
  return 'D:' + (c(maj,'d')-c(min,'d')) + ', I:' + (c(maj,'i')-c(min,'i')) +
         ', S:' + (c(maj,'s')-c(min,'s')) + ', C:' + (c(maj,'c')-c(min,'c'));
})()`);

await evaluate(`document.getElementById('btn-finish').click()`);
await sleep(400);
results.resultVisible = await evaluate(`!document.getElementById('screen-result').hidden`);
results.scoreText = (await evaluate(`document.getElementById('score-line').textContent`)).replace(/\s+/g, ' ').trim();
results.expected = expected;
results.scoreMatches = results.scoreText === expected;
results.bars = await evaluate(`document.querySelectorAll('.bar').length`);
results.scoreSum = await evaluate(`(document.getElementById('score-line').textContent.match(/-?\\d+/g) || []).map(Number).reduce((a,b)=>a+b,0)`);
results.scoreRange = await evaluate(`(() => { const v = (document.getElementById('score-line').textContent.match(/-?\\d+/g)||[]).map(Number); return v.every(x => x >= -8 && x <= 8); })()`);

// ---------- 6. «Вернуться к ответам» и «Пройти заново»
await evaluate(`document.getElementById('btn-review').click()`);
await sleep(200);
results.reviewWorks = await evaluate(`!document.getElementById('screen-quiz').hidden && document.getElementById('screen-result').hidden && document.getElementById('step-label').textContent`);
await evaluate(`document.getElementById('btn-finish').click()`);
await sleep(200);
await evaluate(`document.getElementById('btn-restart').click()`);
await sleep(250);
results.restartOrder = await evaluate(`[...document.querySelectorAll('.list')].map(ul => [...ul.children].map(li => li.dataset.type).join('')).slice(0,3).join(' | ')`);
results.restartScreen = await evaluate(`!document.getElementById('screen-quiz').hidden && document.getElementById('screen-result').hidden && document.getElementById('step-label').textContent`);

// ---------- 7. скриншоты (десктоп)
const shot = async (name) => {
  const r = await send('Page.captureScreenshot', { format: 'png' });
  writeFileSync(name, Buffer.from(r.data, 'base64'));
};
await evaluate(`document.getElementById('screen-quiz').hidden = true; document.getElementById('screen-start').hidden = false; window.scrollTo(0,0)`);
await sleep(250);
await shot('shot-start.png');
await evaluate(`document.getElementById('btn-start').click()`);
await sleep(300);
await shot('shot-step1.png');
for (let i = 0; i < 7; i++) await evaluate(`document.getElementById('btn-next').click()`);
await sleep(300);
await shot('shot-step8.png');
await evaluate(`document.getElementById('btn-finish').click()`);
await sleep(500);
await shot('shot-result.png');

// ---------- 8. мобильный вид + touch-drag за «точечки»
await send('Emulation.setDeviceMetricsOverride', { width: 390, height: 844, deviceScaleFactor: 2, mobile: true });
await send('Emulation.setTouchEmulationEnabled', { enabled: true, maxTouchPoints: 1 });
await sleep(400);
await evaluate(`document.getElementById('screen-result').hidden = true; document.getElementById('screen-quiz').hidden = false; document.querySelectorAll('.pane').forEach((p,i)=>{p.hidden = i!==0}); document.querySelectorAll('.tab')[0].click(); document.getElementById('btn-next').hidden = false; document.getElementById('btn-finish').hidden = true; window.scrollTo(0,0)`);
await sleep(400);
await shot('shot-mobile.png');
await evaluate(`document.querySelectorAll('.list')[2].scrollIntoView({block:'center'})`);
await sleep(500);

const hr = await evaluate(`(() => {
  const ul = document.querySelectorAll('.list')[2];
  const lis = [...ul.children];
  const h = lis[2].querySelector('.handle').getBoundingClientRect();
  const b = lis[0].getBoundingClientRect();
  return { x: h.x + h.width/2, from: h.y + h.height/2, to: b.y + 4, before: [...ul.children].map(li=>li.dataset.type).join('') };
})()`);
const touch = (type, x, y) => send('Input.dispatchTouchEvent', {
  type, touchPoints: type === 'touchEnd' ? [] : [{ x, y, id: 1 }]
});
await touch('touchStart', hr.x, hr.from);
await sleep(40);
for (let k = 1; k <= 10; k++) {
  await touch('touchMove', hr.x, hr.from + (hr.to - hr.from) * (k / 10));
  await sleep(30);
}
await touch('touchEnd', hr.x, hr.to);
await sleep(250);
results.touchBefore = hr.before;
results.touchAfter = await evaluate(`[...document.querySelectorAll('.list')[2].children].map(li => li.dataset.type).join('')`);
await shot('shot-mobile-after-drag.png');

// ---------- 9. ошибки и сеть
results.jsErrors = events.filter(e => e.method === 'Runtime.exceptionThrown')
  .map(e => e.params.exceptionDetails.text + ' ' + (e.params.exceptionDetails.exception?.description || ''));
results.consoleErrors = events.filter(e => e.method === 'Runtime.consoleAPICalled' && e.params.type === 'error')
  .map(e => e.params.args.map(a => a.value ?? a.description).join(' '));
results.externalRequests = requests.filter(u => !u.startsWith('file://'));

console.log(JSON.stringify(results, null, 2));

ws.close();
chrome.kill('SIGKILL');
await sleep(300);
process.exit(0);