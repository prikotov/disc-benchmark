import { spawn } from 'node:child_process';
import { setTimeout as sleep } from 'node:timers/promises';

const PORT = 9336;
const BASE = `http://127.0.0.1:${PORT}`;
const chrome = spawn('/usr/bin/google-chrome', [
  '--headless=new', `--remote-debugging-port=${PORT}`,
  '--no-first-run', '--disable-gpu', '--user-data-dir=/tmp/disc-geo-' + Date.now(), 'about:blank'
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
for (let i = 0; i < 40 && !(await ev2(`document.querySelectorAll('.disc-list').length === 24`)); i++) await sleep(150);

const geo = async (w, h, open) => {
  await call('Emulation.setDeviceMetricsOverride', { width: w, height: h, deviceScaleFactor: 1, mobile: false });
  await sleep(150);
  if (open) { await ev2(`document.getElementById('btnHome').click() || document.querySelector('[data-disc-open]').click()`); await sleep(200); }
  return await ev2(`(() => {
    const out = { vw: innerWidth, vh: innerHeight, overflowX: document.documentElement.scrollWidth > innerWidth + 1 };
    const dlg = document.querySelector('.disc-modal__dialog');
    const r = dlg.getBoundingClientRect();
    out.dialog = { w: r.width, h: r.height, fits: r.top >= -1 && r.bottom <= innerHeight + 1 };
    const items = Array.from(document.querySelectorAll('.disc-list .disc-item')).map(li => li.getBoundingClientRect());
    out.itemOverflow = items.some(b => b.left < 0 || b.right > innerWidth);
    const word = document.querySelector('.disc-list .disc-word').getBoundingClientRect();
    out.wordWidth = word.width;
    const tabs = document.querySelector('.disc-tabs');
    out.tabsScrollable = tabs.scrollWidth >= tabs.clientWidth;
    const btns = document.querySelector('.disc-actions');
    const br = btns.getBoundingClientRect();
    out.actionsVisible = br.top >= 0 && br.bottom <= innerHeight + 1;
    return JSON.stringify(out);
  })()`);
};

await ev2(`document.querySelector('[data-disc-open]').click()`);
await sleep(200);
console.log('desktop 1280x900 open :', await geo(1280, 900));
console.log('tablet  820x1180 open:', await geo(820, 1180));
console.log('mobile  390x844 open :', await geo(390, 844, true));
// result view geometry on mobile
await ev2(`(() => {
  document.querySelectorAll('.disc-list').forEach(ul => { const li={d:0,i:0,s:0,c:0}; Array.from(ul.children).forEach(x=>li[x.dataset.type]=x); ul.innerHTML=''; ul.appendChild(li.d); ul.appendChild(li.s); ul.appendChild(li.c); ul.appendChild(li.i); });
})()`);
for (let i = 0; i < 7; i++) await ev2(`document.querySelector('[data-disc-next]').click()`);
await ev2(`document.querySelector('[data-disc-finish]').click()`);
await sleep(300);
const resGeo = await ev2(`(() => {
  return JSON.stringify({
    vw: innerWidth, vh: innerHeight,
    overflowX: document.documentElement.scrollWidth > innerWidth + 1,
    scoreW: document.getElementById('scoreLine').getBoundingClientRect().width,
    cardW: document.querySelector('.result-card').getBoundingClientRect().width,
    actionsFit: document.querySelector('.result__actions').getBoundingClientRect().bottom <= innerHeight + 1
  });
})()`);
console.log('mobile result view   :', resGeo);
ws.close(); chrome.kill();
