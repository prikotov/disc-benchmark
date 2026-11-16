import { spawn } from 'node:child_process';
const PORT = 9433;
const chrome = spawn('google-chrome', ['--headless=new', `--remote-debugging-port=${PORT}`, `--user-data-dir=/tmp/geom-${Date.now()}`, '--no-first-run', '--disable-gpu', '--hide-scrollbars', 'about:blank'], { stdio: 'ignore' });
const sleep = ms => new Promise(r => setTimeout(r, ms));
let page; for (let i=0;i<80;i++){ try{ const l=await(await fetch(`http://127.0.0.1:${PORT}/json/list`)).json(); page=l.find(t=>t.type==='page'); if(page) break;}catch{} await sleep(250);}
const ws = new WebSocket(page.webSocketDebuggerUrl); await new Promise((r,j)=>{ws.onopen=r;ws.onerror=j;});
let id=0; const pend=new Map(); ws.onmessage=m=>{const x=JSON.parse(m.data); if(x.id&&pend.has(x.id)){const{r,j}=pend.get(x.id);pend.delete(x.id);x.error?j(new Error(JSON.stringify(x.error))):r(x.result);} };
const send=(m,p={})=>new Promise((r,j)=>{const i=++id;pend.set(i,{r,j});ws.send(JSON.stringify({id:i,method:m,params:p}));});
const ev=async e=>(await send('Runtime.evaluate',{expression:e,returnByValue:true,awaitPromise:true})).result.value;
await send('Page.enable'); await send('Runtime.enable');
await send('Page.navigate',{url:'file://'+process.cwd()+'/index.html'}); await sleep(900);

const dump = `(sel) => { const e = document.querySelector(sel); if (!e) return null; const r = e.getBoundingClientRect(); const c = getComputedStyle(e); return {sel, x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height), fs: c.fontSize, display: c.display}; }`;
await ev(`window.__d = ${dump}`);

for (const [w,h] of [[1440,900],[1024,768],[390,844]]) {
  await send('Emulation.setDeviceMetricsOverride', {width:w,height:h,deviceScaleFactor:1,mobile:w<500});
  await sleep(300);
  console.log('== viewport', w, h);
  console.log('START', JSON.stringify(await ev(`[__d('.shell'),__d('#screen-start'),__d('.intro__title'),__d('.intro__subtitle'),__d('.facts'),__d('.rules'),__d('#btn-start')]`)));
  await ev(`document.getElementById('btn-start').click()`); await sleep(250);
  console.log('QUIZ ', JSON.stringify(await ev(`[__d('#screen-quiz'),__d('.quiz__title'),__d('.tabs'),__d('.grid3'),__d('.group'),__d('.group__title'),__d('.item'),__d('.nav'),__d('#btn-next'),__d('#btn-prev')]`)));
  await ev(`window.scrollTo(0, document.documentElement.scrollHeight)`); await sleep(150);
  console.log('QUIZ bottom', JSON.stringify(await ev(`[__d('.nav'),__d('#btn-next'),__d('.foot')]`)));
  await ev(`window.scrollTo(0, 400)`); await sleep(200);
  console.log('QUIZ mid   ', JSON.stringify(await ev(`[__d('.nav'),__d('#btn-next'),__d('.item')]`)));
  await ev(`window.scrollTo(0,0)`);
  for (let i=0;i<7;i++) await ev(`document.getElementById('btn-next').click()`);
  await ev(`document.getElementById('btn-finish').click()`); await sleep(350);
  console.log('RES  ', JSON.stringify(await ev(`[__d('#screen-result'),__d('.result__title'),__d('.score'),__d('#score-line'),__d('.bars'),__d('.bar'),__d('.bar__track'),__d('.result__note'),__d('#btn-restart')]`)));
  await ev(`document.getElementById('btn-restart').click()`);
  await ev(`document.getElementById('screen-quiz').hidden = true; document.getElementById('screen-start').hidden = false; window.scrollTo(0,0)`);
  await sleep(100);
}
ws.close(); chrome.kill('SIGKILL'); process.exit(0);
