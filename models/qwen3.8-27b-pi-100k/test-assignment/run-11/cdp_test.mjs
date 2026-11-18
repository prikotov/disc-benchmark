// CDP smoke test for index.html (headless Chrome)
import { spawn } from 'node:child_process';
import { setTimeout as sleep } from 'node:timers/promises';
import fs from 'node:fs';

const PORT = 9333;
const FILE = 'file://' + process.cwd() + '/index.html';
const BASE = `http://127.0.0.1:${PORT}`;

const chrome = spawn('/usr/bin/google-chrome', [
  '--headless=new', `--remote-debugging-port=${PORT}`,
  '--no-first-run', '--no-default-browser-check', '--disable-gpu',
  '--user-data-dir=/tmp/disc-cdp-' + Date.now(),
  'about:blank'
], { stdio: 'pipe' });

let targetWsUrl = null;
for (let i = 0; i < 40; i++) {
  try {
    const r = await fetch(BASE + '/json/new?' + encodeURIComponent(FILE), { method: 'PUT' });
    if (r.ok) { const t = await r.json(); targetWsUrl = t.webSocketDebuggerUrl; break; }
  } catch {}
  await sleep(250);
}
if (!targetWsUrl) { console.error('no target'); chrome.kill(); process.exit(1); }

const ws = new WebSocket(targetWsUrl);
let seq = 0;
const pending = new Map();
const errors = [];
const logs = [];
ws.onmessage = (ev) => {
  const m = JSON.parse(ev.data);
  if (m.id && pending.has(m.id)) { const { resolve } = pending.get(m.id); pending.delete(m.id); resolve(m); }
  if (m.method === 'Runtime.exceptionThrown') errors.push(JSON.stringify(m.params.exceptionDetails));
  if (m.method === 'Runtime.consoleAPICalled') logs.push(m.params.args.map(a => a.value ?? a.description).join(' '));
};
await new Promise(res => ws.onopen = res);

function call(method, params = {}) {
  return new Promise((resolve, reject) => {
    const id = ++seq;
    pending.set(id, { resolve, reject });
    ws.send(JSON.stringify({ id, method, params }));
    setTimeout(() => { if (pending.has(id)) { pending.delete(id); reject(new Error('timeout ' + method)); } }, 8000);
  });
}
async function evaljs(expr) {
  const r = await call('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true });
  if (r.result && r.result.exceptionDetails) throw new Error('eval: ' + JSON.stringify(r.result.exceptionDetails));
  return r.result.result && r.result.result.value;
}

await call('Page.enable');
await call('Runtime.enable');

// wait until app booted
for (let i = 0; i < 40; i++) {
  const ok = await evaljs(`!!document.querySelector('.disc-list') && document.querySelectorAll('.disc-list').length === 24`);
  if (ok) break;
  await sleep(150);
}

const results = [];
function check(name, cond) { results.push([name, !!cond]); if (!cond) console.error('FAIL:', name); }

// --- static checks ---
check('24 lists', (await evaljs(`document.querySelectorAll('.disc-list').length`)) === 24);
check('96 items', (await evaljs(`document.querySelectorAll('.disc-item').length`)) === 96);
const wordOk = await evaljs(`(() => {
  const q = Array.from(document.querySelectorAll('.disc-list')).map(ul => Array.from(ul.children).map(li => li.dataset.type + ':' + li.textContent.trim().replace(/^{.*?}|\s*$/g,'')));
  return q;
})()`) && true;
check('modal initially aria-hidden', (await evaljs(`document.getElementById('wizardmodal').getAttribute('aria-hidden')`)) === 'true');

// --- open modal ---
await evaljs(`document.querySelector('[data-disc-open]').click()`);
await sleep(120);
check('modal opens', (await evaljs(`document.getElementById('wizardmodal').getAttribute('aria-hidden')`)) === 'false');
check('progress 12.5%', (await evaljs(`document.getElementById('discProgress').style.width`)) === '12.5%');
check('finish hidden at step 0', (await evaljs(`document.querySelector('[data-disc-finish]').hidden`)) === true);

// --- pointer drag: first card, move item index 3 to top ---
const g = await evaljs(`(() => {
  const ul = document.querySelector('.disc-list');
  const li = ul.children[3];
  const r = li.getBoundingClientRect();
  const first = ul.children[0].getBoundingClientRect();
  return { x: r.left + r.width/2, y: r.top + r.height/2, ty: first.top + first.height/4 };
})()`);
await call('Input.dispatchMouseEvent', { type: 'mousePressed', x: g.x, y: g.y, button: 'left', clickCount: 1 });
let prev = { x: g.x, y: g.y };
const steps = 14;
for (let i = 1; i <= steps; i++) {
  const y = g.y + (g.ty - g.y) * (i / steps);
  await call('Input.dispatchMouseEvent', { type: 'mouseMoved', x: prev.x + (Math.random() - .5) * 2, y, button: 'left', buttons: 1 });
  prev = { x: g.x, y };
  await sleep(16);
}
await call('Input.dispatchMouseEvent', { type: 'mouseReleased', x: g.x, y: prev.y, button: 'left' });
await sleep(120);
const firstTypeAfterDrag = await evaljs(`document.querySelector('.disc-list').children[0].dataset.type`);
check('drag: dragged item is still present exactly once', (await evaljs(`document.querySelectorAll('.disc-list .disc-item').length`)) === 96);
check('drag: item originally at idx3 now first', firstTypeAfterDrag === 's');

// --- deterministic permutation for scoring check ---
await evaljs(`(() => {
  document.querySelectorAll('.disc-list').forEach(ul => {
    const li = { d:null, i:null, s:null, c:null };
    Array.from(ul.children).forEach(x => li[x.dataset.type] = x);
    ul.innerHTML = '';
    ul.appendChild(li.d); ul.appendChild(li.s); ul.appendChild(li.c); ul.appendChild(li.i);
  });
})()`);
// order d,s,c,i  => maj d, min i  => d=24, i=-24, s=0, c=0
// walk to last step
for (let i = 0; i < 7; i++) {
  await evaljs(`document.querySelector('[data-disc-next]').click()`);
  await sleep(60);
}
check('prev disabled at 0 / step num 8/8', (await evaljs(`document.getElementById('stepNum').textContent`)) === '8 / 8');
check('next hidden at step 8', (await evaljs(`document.querySelector('[data-disc-next]').hidden`)) === true);
check('finish visible at step 8', (await evaljs(`document.querySelector('[data-disc-finish]').hidden`)) === false);
check('progress 100%', (await evaljs(`document.getElementById('discProgress').style.width`)) === '100%');

await evaljs(`document.querySelector('[data-disc-finish]').click()`);
await sleep(150);
const scoreText = await evaljs(`document.getElementById('scoreLine').textContent`);
check('score line "D:24, I:-24, S:0, C:0" (got: ' + scoreText + ')', scoreText === 'D:24, I:-24, S:0, C:0');
check('result view shown', (await evaljs(`!document.getElementById('result').hidden`)) === true);
check('modal closed after finish', (await evaljs(`document.getElementById('wizardmodal').getAttribute('aria-hidden')`)) === 'true');
check('4 chips', (await evaljs(`document.querySelectorAll('#chips .chip').length`)) === 4);

// --- restart ---
await evaljs(`document.getElementById('btnAgain').click()`);
await sleep(150);
check('restart: back to step 1', (await evaljs(`document.getElementById('stepNum').textContent`)) === '1 / 8');
check('restart: first list restored to source order (i,c,d,s)',
  (await evaljs(`Array.from(document.querySelector('.disc-list').children).map(li => li.dataset.type).join('')`)) === 'icds');
check('restart: first word is Экспресcивный (with latin c)',
  (await evaljs(`document.querySelector('.disc-list .disc-word').textContent`)) === 'Экспресcивный');

// --- go home ---
await evaljs(`document.getElementById('wizardmodal').querySelector('[data-disc-close]').click()`);
await sleep(80);
await evaljs(`document.querySelector('[data-disc-open]').click()`);
await sleep(80);
// finish with untouched order (all i at top, all c at pos3 in source? no — check score = 0? just verify format)
for (let i = 0; i < 7; i++) { await evaljs(`document.querySelector('[data-disc-next]').click()`); }
await evaljs(`document.querySelector('[data-disc-finish]').click()`);
await sleep(120);
const s2 = await evaljs(`document.getElementById('scoreLine').textContent`);
check('score format D:.., I:.., S:.., C:.. (got: ' + s2 + ')', /D:-?\d+, I:-?\d+, S:-?\d+, C:-?\d+/.test(s2));
await evaljs(`document.getElementById('btnHome').click()`);
check('home shown', (await evaljs(`!document.getElementById('screen').hidden && document.getElementById('result').hidden`)) === true);

check('no page exceptions', errors.length === 0);

const failed = results.filter(([, ok]) => !ok);
console.log('\n=== RESULT: ' + (results.length - failed.length) + '/' + results.length + ' passed ===');
for (const [n, ok] of results) console.log((ok ? '  ok  ' : '  FAIL') + ' ' + n);
if (errors.length) console.log('page errors:', errors);
ws.close();
chrome.kill();
process.exit(failed.length ? 1 : 0);
