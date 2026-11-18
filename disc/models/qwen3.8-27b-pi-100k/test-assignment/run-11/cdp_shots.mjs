import { spawn } from 'node:child_process';
import { setTimeout as sleep } from 'node:timers/promises';
import fs from 'node:fs';

const PORT = 9335;
const BASE = `http://127.0.0.1:${PORT}`;
const chrome = spawn('/usr/bin/google-chrome', [
  '--headless=new', `--remote-debugging-port=${PORT}`,
  '--no-first-run', '--disable-gpu', '--window-size=1280,900',
  '--user-data-dir=/tmp/disc-shot-' + Date.now(), 'about:blank'
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
const shot = async (name) => { const r = await call('Page.captureScreenshot', { format: 'png' }); if (r.result && r.result.data) fs.writeFileSync(name, Buffer.from(r.result.data, 'base64')); };

for (let i = 0; i < 40 && !(await ev2(`document.querySelectorAll('.disc-list').length === 24`)); i++) await sleep(150);
await sleep(300);
await call('Emulation.setDeviceMetricsOverride', { width: 1280, height: 900, deviceScaleFactor: 1, mobile: false });
await shot('shot_start.png');

await ev2(`document.querySelector('[data-disc-open]').click()`);
await sleep(350);
await shot('shot_test.png');

// deterministic finish: d all on top, i at bottom
await ev2(`(() => {
  document.querySelectorAll('.disc-list').forEach(ul => {
    const li = { d:null, i:null, s:null, c:null };
    Array.from(ul.children).forEach(x => li[x.dataset.type] = x);
    ul.innerHTML = '';
    ul.appendChild(li.d); ul.appendChild(li.s); ul.appendChild(li.c); ul.appendChild(li.i);
  });
})()`);
for (let i = 0; i < 7; i++) { await ev2(`document.querySelector('[data-disc-next]').click()`); await sleep(50); }
await ev2(`document.querySelector('[data-disc-finish]').click()`);
await sleep(400);
await call('Emulation.setDeviceMetricsOverride', { width: 900, height: 700, deviceScaleFactor: 1, mobile: false });
await sleep(150);
await shot('shot_result.png');

// mobile size check
await ev2(`document.getElementById('btnHome').click()`);
await sleep(200);
await call('Emulation.setDeviceMetricsOverride', { width: 390, height: 844, deviceScaleFactor: 1, mobile: true });
await sleep(250);
await ev2(`document.querySelector('[data-disc-open]').click()`);
await sleep(350);
await shot('shot_mobile.png');

ws.close(); chrome.kill();
console.log('done');
