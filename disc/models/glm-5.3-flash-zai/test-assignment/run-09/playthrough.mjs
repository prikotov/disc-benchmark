// Playthrough: headless Chrome via CDP, synthetic Pointer Events drags
import { spawn } from 'node:child_process';
import fs from 'node:fs';

const PORT = 9333;
const FILE = 'file://' + process.cwd() + '/index.html';
const sleep = (ms) => new Promise(r => setTimeout(r, ms));

const chrome = spawn('google-chrome', [
  '--headless=new', `--remote-debugging-port=${PORT}`,
  '--window-size=1400,950', '--no-first-run', '--no-default-browser-check',
  '--user-data-dir=/tmp/disc-cdp-' + Date.now(), 'about:blank'
], { stdio: 'ignore' });

const getJson = (p) => new Promise((res, rej) => {
  httpGet({ host: '127.0.0.1', port: PORT, path: p }, res, rej);
});
function httpGet(opts, res, rej) {
  import('node:http').then(({ default: http }) => {
    http.get(opts, (r) => { let d = ''; r.on('data', c => d += c); r.on('end', () => res(JSON.parse(d))); })
      .on('error', rej);
  });
}

let ws, msgId = 0;
const pending = new Map();
const events = [];
const exceptions = [];

function send(method, params = {}) {
  const id = ++msgId;
  ws.send(JSON.stringify({ id, method, params }));
  return new Promise((res, rej) => pending.set(id, { res, rej }));
}

async function main() {
  // wait for CDP
  let list;
  for (let i = 0; i < 50; i++) {
    try { list = await getJson('/json/list'); break; } catch { await sleep(200); }
  }
  const target = list.find(t => t.type === 'page');
  ws = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise(r => ws.onopen = r);
  ws.onmessage = (e) => {
    const m = JSON.parse(e.data);
    if (m.id && pending.has(m.id)) {
      const { res, rej } = pending.get(m.id);
      pending.delete(m.id);
      m.error ? rej(new Error(m.error.message)) : res(m.result);
    } else if (m.method) {
      events.push(m);
      if (m.method === 'Runtime.exceptionThrown') exceptions.push(m.params);
    }
  };
  await send('Runtime.enable');
  await send('Page.enable');
  await send('Emulation.setDeviceMetricsOverride',
    { width: 1400, height: 950, deviceScaleFactor: 1, mobile: false });

  const evalJs = async (expression) => {
    const r = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true });
    if (r.exceptionDetails) throw new Error('eval failed: ' + JSON.stringify(r.exceptionDetails.exception?.description || r.exceptionDetails));
    return r.result.value;
  };
  const shot = async (name) => {
    const r = await send('Page.captureScreenshot', { format: 'png' });
    fs.writeFileSync(name, Buffer.from(r.data, 'base64'));
  };

  await send('Page.navigate', { url: FILE });
  await sleep(1200);

  const results = [];
  const check = (name, cond, extra = '') => {
    results.push([cond ? 'PASS' : 'FAIL', name, extra]);
  };

  // --- render smoke ---
  const dom = await evalJs(`(() => ({
    items: document.querySelectorAll('.disc-item').length,
    lists: document.querySelectorAll('.disc-list').length,
    panes: document.querySelectorAll('.disc-pane').length,
    tabs: document.querySelectorAll('.disc-tab').length,
    firstWords: Array.from(document.querySelectorAll('#draggable-list1 .disc-item__text')).map(e => e.textContent),
    types1: Array.from(document.querySelectorAll('#draggable-list1 .disc-item')).map(e => e.dataset.type)
  }))()`);
  check('render: 96 items', dom.items === 96, `got ${dom.items}`);
  check('render: 24 lists', dom.lists === 24);
  check('render: 8 panes', dom.panes === 8);
  check('render: 8 tabs', dom.tabs === 8);
  check('data: list1 words exact', JSON.stringify(dom.firstWords) ===
    JSON.stringify(["Экспресcивный", "Покладистый", "Волевой", "Осторожный"]), JSON.stringify(dom.firstWords));
  check('data: list1 types', JSON.stringify(dom.types1) === JSON.stringify(["i", "c", "d", "s"]));

  // --- open modal ---
  await evalJs(`document.querySelector('[data-modal-open]').click()`);
  await sleep(300);
  const opened = await evalJs(`document.getElementById('wizardmodal').classList.contains('is-open')`);
  check('modal opens', opened);
  await shot('shot-start.png');

  // --- drag helper (synthetic Pointer Events, like automated checks would) ---
  await evalJs(`(() => {
    window.__drag = async (listIdx, fromPos, toPosAfter) => {
      const ul = document.getElementById('draggable-list' + listIdx);
      const lis = Array.from(ul.querySelectorAll('.disc-item'));
      const src = lis[fromPos];
      const target = lis[toPosAfter === lis.length ? lis.length - 1 : toPosAfter];
      const fire = (el, type, x, y) => el.dispatchEvent(new PointerEvent(type, {
        bubbles: true, cancelable: true, composed: true,
        pointerId: 1, pointerType: 'mouse', isPrimary: true,
        button: 0, buttons: type === 'pointerup' ? 0 : 1, clientX: x, clientY: y
      }));
      const sr = src.getBoundingClientRect();
      let x = sr.left + sr.width / 2, y = sr.top + sr.height / 2;
      fire(src, 'pointerdown', x, y);
      const tr = target.getBoundingClientRect();
      const tx = tr.left + tr.width / 2;
      const ty = toPosAfter === lis.length ? tr.bottom + (sr.height / 2 + 4) : tr.top + tr.height / 2;
      const steps = 10;
      for (let i = 1; i <= steps; i++) {
        fire(src, 'pointermove', x + (tx - x) * i / steps, y + (ty - y) * i / steps);
        await new Promise(r => setTimeout(r, 15));
      }
      fire(src, 'pointerup', tx, ty);
      return Array.from(ul.querySelectorAll('.disc-item')).map(e => e.dataset.type).join('');
    };
  })()`);

  // --- walk 8 steps; each step: 3 lists; drag item0 to bottom (-> наименее) ---
  let cursor = 1;
  for (let s = 0; s < 8; s++) {
    for (let k = 0; k < 3; k++, cursor++) {
      const before = await evalJs(`Array.from(document.getElementById('draggable-list${cursor}').querySelectorAll('.disc-item')).map(e => e.dataset.type).join('')`);
      const after = await evalJs(`window.__drag(${cursor}, 0, 4)`);
      check(`drag list${cursor}: item0 -> bottom`, after === before.slice(1) + before[0],
        `${before} -> ${after}`);
    }
    if (s < 7) { await evalJs(`document.querySelector('[data-disc-next]').click()`); await sleep(150); }
  }
  await shot('shot-step8.png');

  const expected = await evalJs(`(() => {
    const maj = [], min = [];
    document.querySelectorAll('.disc-list').forEach(ul => {
      const t = Array.from(ul.querySelectorAll('.disc-item')).map(e => e.dataset.type);
      maj.push(t[0]); min.push(t[3]);
    });
    const c = (a, ch) => a.reduce((s, v) => s + (v === ch), 0);
    const r = { d: 0, i: 0, s: 0, c: 0 };
    for (const k of ['d','i','s','c']) r[k] = c(maj, k) - c(min, k);
    return r;
  })()`);
  const expLine = `D:${expected.d}, I:${expected.i}, S:${expected.s}, C:${expected.c}`;

  await evalJs(`document.querySelector('[data-disc-finish]').click()`);
  await sleep(300);
  const line = await evalJs(`document.getElementById('discScoreLine').textContent`);
  check('score line matches computed', line === expLine, `got "${line}", expected "${expLine}"`);
  const visible = await evalJs(`document.getElementById('discResult').classList.contains('is-visible')`);
  check('result view visible', visible);
  const bars = await evalJs(`document.querySelectorAll('#discScale .result__row').length`);
  check('result: 4 type rows', bars === 4);
  await shot('shot-result.png');

  // --- restart ---
  await evalJs(`document.querySelector('[data-disc-restart]').click()`);
  await sleep(300);
  const reset = await evalJs(`(() => ({
    step: document.getElementById('rootwizard').dataset.step,
    items: document.querySelectorAll('.disc-item').length,
    l1: Array.from(document.querySelectorAll('#draggable-list1 .disc-item')).map(e => e.dataset.type).join(''),
    result: document.getElementById('discResult').classList.contains('is-visible')
  }))()`);
  check('restart: back to step 0', reset.step === '0' && reset.items === 96 &&
    reset.l1 === 'icds' && !reset.result, JSON.stringify(reset));

  // --- esc / overlay close ---
  await evalJs(`document.querySelector('[data-modal-open]').click()`);
  await sleep(100);
  await evalJs(`document.dispatchEvent(new KeyboardEvent('keydown', {key:'Escape', bubbles:true}))`);
  await sleep(100);
  const closed = await evalJs(`!document.getElementById('wizardmodal').classList.contains('is-open')`);
  check('esc closes modal', closed);

  // --- uncaught exceptions ---
  check('no uncaught exceptions', exceptions.length === 0,
    exceptions.map(e => e.exceptionDetails?.exception?.description).join(' | '));

  let fails = 0;
  for (const [st, name, extra] of results) {
    if (st === 'FAIL') fails++;
    console.log(`${st}  ${name}${extra ? '   [' + extra + ']' : ''}`);
  }
  console.log(fails === 0 ? '\nALL PASS' : `\n${fails} FAILURES`);
  chrome.kill();
  process.exit(fails === 0 ? 0 : 1);
}

main().catch(e => { console.error('FATAL', e); chrome.kill(); process.exit(2); });
