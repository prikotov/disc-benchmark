import { spawn } from 'node:child_process';
const PORT = 9422;
const chrome = spawn('google-chrome', ['--headless=new', `--remote-debugging-port=${PORT}`, `--user-data-dir=/tmp/lay-${Date.now()}`, '--no-first-run', '--disable-gpu', '--hide-scrollbars', 'about:blank'], { stdio: 'ignore' });
const sleep = ms => new Promise(r => setTimeout(r, ms));
let page; for (let i=0;i<80;i++){ try{ const l=await(await fetch(`http://127.0.0.1:${PORT}/json/list`)).json(); page=l.find(t=>t.type==='page'); if(page) break;}catch{} await sleep(250);}
const ws = new WebSocket(page.webSocketDebuggerUrl); await new Promise((r,j)=>{ws.onopen=r;ws.onerror=j;});
let id=0; const pend=new Map(); ws.onmessage=m=>{const x=JSON.parse(m.data); if(x.id&&pend.has(x.id)){const{r,j}=pend.get(x.id);pend.delete(x.id);x.error?j(new Error(JSON.stringify(x.error))):r(x.result);} };
const send=(m,p={})=>new Promise((r,j)=>{const i=++id;pend.set(i,{r,j});ws.send(JSON.stringify({id:i,method:m,params:p}));});
const ev=async e=>(await send('Runtime.evaluate',{expression:e,returnByValue:true,awaitPromise:true})).result.value;
await send('Page.enable'); await send('Runtime.enable');
await send('Page.navigate',{url:'file://'+process.cwd()+'/index.html'}); await sleep(1000);

const audit = `(() => {
  const out = {};
  out.overflowX = document.documentElement.scrollWidth - innerWidth;
  out.overflowBody = document.body.scrollWidth - innerWidth;
  const clipped = [...document.querySelectorAll('.item__text,.btn,.tab,.facts__value,.intro__title,.quiz__title,.score__value')]
    .filter(e => e.scrollWidth > e.clientWidth + 1 || e.scrollHeight > e.clientHeight + 1)
    .map(e => (e.className||'') + ':' + (e.textContent||'').trim().slice(0,24));
  out.clipped = clipped;
  out.smallTargets = [...document.querySelectorAll('button')]
    .filter(b => b.offsetParent !== null && (b.getBoundingClientRect().height < 34 || b.getBoundingClientRect().width < 28))
    .map(b => (b.className||'') + ':' + Math.round(b.getBoundingClientRect().height));
  const grid = document.querySelector('.grid3');
  out.gridCols = grid ? getComputedStyle(grid).gridTemplateColumns.split(' ').length : null;
  out.itemHeights = [...document.querySelectorAll('[data-step-pane="0"] .item')].slice(0,4).map(i => Math.round(i.getBoundingClientRect().height));
  out.cardWidth = Math.round(document.querySelector('.card').getBoundingClientRect().width);
  out.bodyTextColor = getComputedStyle(document.body).color;
  out.fontFamily = getComputedStyle(document.body).fontFamily.slice(0,40);
  out.tabCount = document.querySelectorAll('.tab').length;
  out.pageHeight = document.documentElement.scrollHeight;
  return out;
})()`;

for (const w of [1440, 1024, 768, 390]) {
  await send('Emulation.setDeviceMetricsOverride', { width: w, height: 900, deviceScaleFactor: 1, mobile: w < 500 });
  await sleep(300);
  const start = await ev(audit);
  await ev(`document.getElementById('btn-start').click()`); await sleep(300);
  const quiz = await ev(audit);
  for (let i=0;i<7;i++) await ev(`document.getElementById('btn-next').click()`);
  await ev(`document.getElementById('btn-finish').click()`); await sleep(400);
  const res = await ev(audit);
  console.log(w, 'START', JSON.stringify(start));
  console.log(w, 'QUIZ ', JSON.stringify(quiz));
  console.log(w, 'RES  ', JSON.stringify(res));
  await ev(`document.getElementById('btn-restart').click()`);
  await ev(`document.getElementById('screen-quiz').hidden = true; document.getElementById('screen-start').hidden = false;`);
  await sleep(100);
}
ws.close(); chrome.kill('SIGKILL'); process.exit(0);
