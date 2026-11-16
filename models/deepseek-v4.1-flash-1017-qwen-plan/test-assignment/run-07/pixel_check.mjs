import { spawn } from 'node:child_process';
import { writeFileSync } from 'node:fs';
const PORT = 9444;
const chrome = spawn('google-chrome', ['--headless=new', `--remote-debugging-port=${PORT}`, `--user-data-dir=/tmp/px-${Date.now()}`, '--no-first-run', '--disable-gpu', '--hide-scrollbars', '--window-size=1280,900', 'about:blank'], { stdio: 'ignore' });
const sleep = ms => new Promise(r => setTimeout(r, ms));
let page; for (let i=0;i<80;i++){ try{ const l=await(await fetch(`http://127.0.0.1:${PORT}/json/list`)).json(); page=l.find(t=>t.type==='page'); if(page) break;}catch{} await sleep(250);}
const ws = new WebSocket(page.webSocketDebuggerUrl); await new Promise((r,j)=>{ws.onopen=r;ws.onerror=j;});
let id=0; const pend=new Map(); ws.onmessage=m=>{const x=JSON.parse(m.data); if(x.id&&pend.has(x.id)){const{r,j}=pend.get(x.id);pend.delete(x.id);x.error?j(new Error(JSON.stringify(x.error))):r(x.result);} };
const send=(m,p={})=>new Promise((r,j)=>{const i=++id;pend.set(i,{r,j});ws.send(JSON.stringify({id:i,method:m,params:p}));});
const ev=async e=>(await send('Runtime.evaluate',{expression:e,returnByValue:true,awaitPromise:true})).result.value;
await send('Page.enable'); await send('Runtime.enable');
await send('Page.navigate',{url:'file://'+process.cwd()+'/index.html'}); await sleep(900);
await ev(`document.getElementById('btn-start').click()`); await sleep(400);
const rects = await ev(`[...document.querySelectorAll('[data-step-pane="0"] .item')].slice(0,4).map(li=>{const r=li.getBoundingClientRect();return {x:Math.round(r.x),y:Math.round(r.y),w:Math.round(r.width),h:Math.round(r.height),t:li.textContent.trim()}})`);
const shot = await send('Page.captureScreenshot',{format:'png'});
writeFileSync('px.png', Buffer.from(shot.data,'base64'));
console.log(JSON.stringify(rects));
console.log('url', await ev('location.href'), 'viewport', await ev('innerWidth+"x"+innerHeight'), 'dpr', await ev('devicePixelRatio'));
ws.close(); chrome.kill('SIGKILL'); process.exit(0);
