import { spawn } from 'node:child_process';
import { writeFileSync } from 'node:fs';
const chrome = spawn('google-chrome', [
  '--headless=new', '--disable-gpu', '--no-sandbox', '--hide-scrollbars',
  '--remote-debugging-port=9223', '--user-data-dir=/tmp/disc-chrome-mobile',
  '--window-size=390,844', 'file://' + process.cwd() + '/index.html'
], { stdio: ['ignore', 'ignore', 'ignore'] });
const sleep = (ms) => new Promise(r => setTimeout(r, ms));
let target;
for (let i = 0; i < 60; i++) {
  try {
    const list = await (await fetch('http://127.0.0.1:9223/json')).json();
    target = list.find(x => x.type === 'page' && x.url.includes('index.html'));
    if (target) break;
  } catch {}
  await sleep(150);
}
if (!target) { console.error('no target'); chrome.kill(); process.exit(1); }
const ws = new WebSocket(target.webSocketDebuggerUrl);
await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });
let id = 0; const pending = new Map(); const events = [];
ws.onmessage = (e) => {
  const m = JSON.parse(e.data);
  if (m.id) { const p = pending.get(m.id); if (p) { pending.delete(m.id); m.error ? p.reject(new Error(JSON.stringify(m.error))) : p.resolve(m.result); } }
  else events.push(m);
};
const send = (method, params = {}) => new Promise((resolve, reject) => { const n = ++id; pending.set(n, { resolve, reject }); ws.send(JSON.stringify({ id: n, method, params })); });
async function evalJS(expression) { const r = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true, userGesture: true }); if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails)); return r.result.value; }
await send('Page.enable'); await send('Runtime.enable'); await send('Network.enable'); await send('Log.enable');
await send('Emulation.setDeviceMetricsOverride', { width: 390, height: 844, deviceScaleFactor: 2, mobile: true });
await send('Emulation.setTouchEmulationEnabled', { enabled: true, maxTouchPoints: 5 });
await send('Page.reload', { ignoreCache: true });
await sleep(800);
const checks = {};
checks.viewport = await evalJS(`JSON.stringify({w:innerWidth,h:innerHeight,dpr:devicePixelRatio,coarse:matchMedia('(pointer: coarse)').matches,bodyScrollWidth:document.body.scrollWidth,docScrollWidth:document.documentElement.scrollWidth})`);
checks.layout = await evalJS(`(()=>{const g=getComputedStyle(document.querySelector('.questions-grid'));const card=document.querySelector('.q-card').getBoundingClientRect();const steps=document.querySelector('.steps');const touch=getComputedStyle(document.querySelector('.touch-word')).display;return JSON.stringify({gridCols:g.gridTemplateColumns,cardW:card.width,stepsScrollW:steps.scrollWidth,stepsClientW:steps.clientWidth,touchWord:touch,bodyOverflow:document.documentElement.scrollWidth-innerWidth})})()`);
checks.tabs = await evalJS(`JSON.stringify({tabCount:document.querySelectorAll('.step-tab').length,active:document.querySelector('.step-tab.is-active')?.textContent})`);
const shotStart = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false });
writeFileSync('shot-mobile-start.png', Buffer.from(shotStart.data, 'base64'));

// Touch drag first card first item by handle to bottom of list
await evalJS(`window.scrollTo(0, document.querySelector('.panes').getBoundingClientRect().top + scrollY - 90)`);
await sleep(200);
const info = await evalJS(`(()=>{const l=document.querySelector('.rank-list');const h=l.children[0].querySelector('.option-handle').getBoundingClientRect();const b=l.children[3].getBoundingClientRect();return {sx:h.left+h.width/2,sy:h.top+h.height/2,ex:b.left+b.width/2,ey:b.bottom-3,order:[...l.children].map(li=>li.querySelector('.option-text').textContent)}})()`);
await send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [{ x: info.sx, y: info.sy, id: 1, radiusX: 2, radiusY: 2, force: 1 }] });
for (let i = 1; i <= 14; i++) {
  await send('Input.dispatchTouchEvent', { type: 'touchMove', touchPoints: [{ x: info.sx + (info.ex-info.sx)*i/14, y: info.sy + (info.ey-info.sy)*i/14, id: 1, radiusX: 2, radiusY: 2, force: 1 }] });
  await sleep(18);
}
const during = await evalJS(`JSON.stringify({ghosts:document.querySelectorAll('.drag-ghost').length,dragging:document.querySelectorAll('.is-dragging').length,order:[...document.querySelector('.rank-list').children].map(li=>li.querySelector('.option-text').textContent)})`);
await send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
await sleep(200);
checks.touchDrag = { before: info.order, during: JSON.parse(during), after: await evalJS(`JSON.stringify([...document.querySelector('.rank-list').children].map(li=>li.querySelector('.option-text').textContent))`) };
checks.touchDragCleanup = await evalJS(`JSON.stringify({ghosts:document.querySelectorAll('.drag-ghost').length,dragging:document.querySelectorAll('.is-dragging').length,bodyClass:document.body.className})`);

// Test page scroll on text touch: record scrollY, touch drag from text upward
await evalJS(`document.querySelector('#restartBtn'); window.scrollTo(0,0);`);
await sleep(100);
const textInfo = await evalJS(`(()=>{const r=document.querySelector('.rank-list .option-text').getBoundingClientRect();return {x:r.left+r.width/2,y:r.top+r.height/2}})()`);
const beforeScroll = await evalJS('scrollY');
await send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [{ x: textInfo.x, y: textInfo.y, id: 2, radiusX: 2, radiusY: 2, force: 1 }] });
for (let i = 1; i <= 8; i++) {
  await send('Input.dispatchTouchEvent', { type: 'touchMove', touchPoints: [{ x: textInfo.x, y: textInfo.y - i*20, id: 2, radiusX: 2, radiusY: 2, force: 1 }] });
  await sleep(20);
}
await send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
await sleep(300);
checks.textTouchScroll = { before: beforeScroll, after: await evalJS('scrollY'), ghosts: await evalJS('document.querySelectorAll(".drag-ghost").length') };

// Finish and inspect result mobile overflow
await evalJS(`document.querySelectorAll('.step-tab')[7].click(); document.querySelector('#finishBtn').click()`);
await sleep(400);
checks.result = await evalJS(`JSON.stringify({score:document.querySelector('#scoreLine').textContent,resultHidden:document.querySelector('#result').hidden,docScrollWidth:document.documentElement.scrollWidth,innerWidth:innerWidth,dimCols:getComputedStyle(document.querySelector('.dim-grid')).gridTemplateColumns,overflow:document.documentElement.scrollWidth-innerWidth})`);
const shotResult = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false });
writeFileSync('shot-mobile-result.png', Buffer.from(shotResult.data, 'base64'));
checks.errors = events.filter(e => e.method === 'Runtime.exceptionThrown' || (e.method === 'Log.entryAdded' && ['error','warning'].includes(e.params.entry.level))).map(e => e.method === 'Runtime.exceptionThrown' ? e.params.exceptionDetails.text : e.params.entry.text);
checks.requests = events.filter(e => e.method === 'Network.requestWillBeSent').map(e => e.params.request.url).filter(u => !u.startsWith('file:') && !u.startsWith('data:'));
console.log(JSON.stringify(checks, null, 2));
ws.close(); chrome.kill();
