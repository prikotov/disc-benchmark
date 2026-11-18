import { spawn } from 'node:child_process';
import { setTimeout as sleep } from 'node:timers/promises';

const PORT = 9334;
const BASE = `http://127.0.0.1:${PORT}`;
const chrome = spawn('/usr/bin/google-chrome', [
  '--headless=new', `--remote-debugging-port=${PORT}`,
  '--no-first-run', '--disable-gpu', '--user-data-dir=/tmp/disc-cdp2-' + Date.now(), 'about:blank'
], { stdio: 'pipe' });

let wsUrl = null;
for (let i = 0; i < 40; i++) {
  try {
    const r = await fetch(BASE + '/json/new?' + encodeURIComponent('file://' + process.cwd() + '/index.html'), { method: 'PUT' });
    if (r.ok) { wsUrl = (await r.json()).webSocketDebuggerUrl; break; }
  } catch {}
  await sleep(250);
}
const ws = new WebSocket(wsUrl);
let seq = 0; const pend = new Map();
ws.onmessage = (ev) => { const m = JSON.parse(ev.data); if (m.id && pend.has(m.id)) { pend.get(m.id)(m); pend.delete(m.id); } };
await new Promise(r => ws.onopen = r);
const call = (method, params = {}) => new Promise((res) => { const id = ++seq; pend.set(id, res); ws.send(JSON.stringify({ id, method, params })); setTimeout(() => { if (pend.has(id)) { pend.delete(id); res({}); } }, 8000); });
const ev2 = async (e) => (await call('Runtime.evaluate', { expression: e, returnByValue: true })).result.result.value;

for (let i = 0; i < 30 && !(await ev2(`document.querySelectorAll('.disc-list').length === 24`)); i++) await sleep(150);

await ev2(`document.querySelector('[data-disc-open]').click()`);
await sleep(150);

const log = (await call('Runtime.evaluate', { expression: `(() => {
  window.__seq = [];
  const origInsert = HTMLUListElement.prototype.insertBefore;
  HTMLUListElement.prototype.insertBefore = function(node, ref) {
    if (node && node.classList && node.classList.contains('disc-item')) window.__seq.push('insertBefore ' + node.dataset.type + ' -> ' + (ref ? ref.dataset.type : 'END'));
    return origInsert.call(this, node, ref);
  };
  return 'hooked';
})()`, returnByValue: true })).result.result.value;

const g = await ev2(`(() => {
  const ul = document.querySelector('.disc-list');
  const li = ul.children[3];
  const r = li.getBoundingClientRect();
  const first = ul.children[0].getBoundingClientRect();
  return JSON.stringify({ x: r.left + r.width/2, y: r.top + r.height/2, ty: first.top + first.height * 0.25, h: r.height });
})()`);
console.log('geom', g);
const P = JSON.parse(g);
await call('Input.dispatchMouseEvent', { type: 'mousePressed', x: P.x, y: P.y, button: 'left', clickCount: 1, buttons: 1 });
for (let i = 1; i <= 16; i++) {
  const y = P.y + (P.ty - P.y) * (i / 16);
  await call('Input.dispatchMouseEvent', { type: 'mouseMoved', x: P.x, y, button: 'none', buttons: 1 });
  console.log('step', i, 'y', y.toFixed(1), 'order', await ev2(`Array.from(document.querySelector('.disc-list').children).map(x=>x.dataset.type).join('')`),
    'ghost', await ev2(`!!document.querySelector('.disc-ghost')`),
    'reord', await ev2(`document.querySelector('.disc-list .disc-item.is-reordering') ? 'yes' : 'no'`));
  await sleep(20);
}
await call('Input.dispatchMouseEvent', { type: 'mouseReleased', x: P.x, y: P.ty, button: 'left', clickCount: 1 });
await sleep(150);
console.log('final order:', await ev2(`Array.from(document.querySelector('.disc-list').children).map(x=>x.dataset.type).join('')`));
console.log('insert sequence:', await ev2(`JSON.stringify(window.__seq)`));
ws.close(); chrome.kill();
