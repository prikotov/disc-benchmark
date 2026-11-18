// Screenshot tour: landing -> modal step 0 -> mid-drag -> result. CDP, no deps.
import { spawn } from 'node:child_process';
import { writeFileSync } from 'node:fs';
import { setTimeout as sleep } from 'node:timers/promises';

const PORT = 9334;
const FILE = new URL('./index.html', import.meta.url).pathname;
const chrome = spawn('google-chrome', [
  '--headless=new', '--disable-gpu', '--no-sandbox',
  `--remote-debugging-port=${PORT}`, '--window-size=1400,1000', '--hide-scrollbars', 'about:blank',
], { stdio: 'ignore' });
const die = (m) => { console.error('FAIL:', m); chrome.kill(); process.exit(1); };

let version;
for (let i = 0; i < 50; i++) {
  try { version = await (await fetch(`http://127.0.0.1:${PORT}/json/version`)).json(); break; }
  catch { await sleep(200); }
}
if (!version) die('no devtools');
const ws = new WebSocket(version.webSocketDebuggerUrl);
await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });
let msgId = 0; const pending = new Map(); const sessions = new Map();
ws.onmessage = (ev) => {
  const m = JSON.parse(ev.data);
  if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); }
};
const send = (method, params = {}, sessionId) => new Promise((resolve) => {
  const id = ++msgId; pending.set(id, resolve);
  ws.send(JSON.stringify({ id, method, params, ...(sessionId ? { sessionId } : {}) }));
});
const { result: tgt } = await send('Target.createTarget', { url: 'about:blank' });
const { result: att } = await send('Target.attachToTarget', { targetId: tgt.targetId, flatten: true });
const sid = att.sessionId; sessions.set(sid, sid);
await send('Page.enable', {}, sid);
await send('Runtime.enable', {}, sid);
await send('Page.navigate', { url: 'file://' + FILE }, sid);
await sleep(1200);

const evl = async (expr) => {
  const r = await send('Runtime.evaluate', { expression: expr, awaitPromise: true, returnByValue: true }, sid);
  if (r.result?.exceptionDetails) die(JSON.stringify(r.result.exceptionDetails));
  return r.result?.result?.value;
};
const shot = async (name) => {
  const r = await send('Page.captureScreenshot', { format: 'png' }, sid);
  writeFileSync(name, Buffer.from(r.result.data, 'base64'));
  console.log('shot:', name);
};

await shot('shot-1-landing.png');

await evl(`document.querySelector('[data-disc-open]').click()`);
await sleep(400);
await shot('shot-2-step1.png');

// step 4 via tab click
await evl(`document.querySelector('[data-step-btn="3"]').click()`);
await sleep(300);
await shot('shot-3-step4.png');

// jump to last step and finish
await evl(`document.querySelector('[data-step-btn="7"]').click()`);
await sleep(300);
await evl(`document.querySelector('[data-disc-finish]').click()`);
await sleep(400);
await shot('shot-4-result.png');

// mobile viewport check
await send('Emulation.setDeviceMetricsOverride', { width: 390, height: 844, deviceScaleFactor: 2, mobile: true }, sid);
await evl(`document.querySelector('[data-disc-restart]').click()`);
await sleep(400);
await shot('shot-5-mobile-step1.png');

chrome.kill(); process.exit(0);
