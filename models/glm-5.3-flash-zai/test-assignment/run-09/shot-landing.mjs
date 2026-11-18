import { spawn } from 'node:child_process';
import fs from 'node:fs';
const PORT = 9334;
const FILE = 'file://' + process.cwd() + '/index.html';
const sleep = (ms) => new Promise(r => setTimeout(r, ms));
const chrome = spawn('google-chrome', ['--headless=new', `--remote-debugging-port=${PORT}`,
  '--window-size=1400,950', '--no-first-run', '--user-data-dir=/tmp/disc-land-' + Date.now(), 'about:blank'], { stdio: 'ignore' });
const getJson = (p) => new Promise((res, rej) => {
  import('node:http').then(({ default: http }) => {
    http.get({ host: '127.0.0.1', port: PORT, path: p }, r => { let d=''; r.on('data',c=>d+=c); r.on('end',()=>res(JSON.parse(d))); }).on('error', rej);
  });
});
let ws, id = 0; const pend = new Map();
const send = (m, p={}) => { const i=++id; ws.send(JSON.stringify({id:i,method:m,params:p})); return new Promise(r=>pend.set(i,r)); };
const list = await (async()=>{ for(let i=0;i<50;i++){ try{ return await getJson('/json/list'); }catch{ await sleep(200);} } })();
ws = new WebSocket(list.find(t=>t.type==='page').webSocketDebuggerUrl);
await new Promise(r=>ws.onopen=r);
ws.onmessage = e => { const m=JSON.parse(e.data); if(m.id&&pend.has(m.id)){ pend.get(m.id)(m.result); pend.delete(m.id);} };
await send('Runtime.enable'); await send('Page.enable');
await send('Page.navigate', { url: FILE }); await sleep(1200);
const r = await send('Page.captureScreenshot', { format: 'png' });
fs.writeFileSync('shot-landing.png', Buffer.from(r.data, 'base64'));
chrome.kill(); process.exit(0);
