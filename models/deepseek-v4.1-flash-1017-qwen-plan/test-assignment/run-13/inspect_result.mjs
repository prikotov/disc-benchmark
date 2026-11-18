import { spawn } from 'node:child_process';
const width = Number(process.argv[2] || 1440);
const port = 9900 + Math.floor(Math.random()*90);
const chrome = spawn('google-chrome', ['--headless=new','--disable-gpu','--no-sandbox','--hide-scrollbars',`--remote-debugging-port=${port}`,`--user-data-dir=/tmp/disc-result-${port}`,`--window-size=${width},1000`,'file://' + process.cwd() + '/index.html'], {stdio:['ignore','ignore','ignore']});
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
let target;for(let i=0;i<60;i++){try{const l=await(await fetch(`http://127.0.0.1:${port}/json`)).json();target=l.find(x=>x.type==='page'&&x.url.includes('index.html'));if(target)break;}catch{}await sleep(150);}
const ws=new WebSocket(target.webSocketDebuggerUrl);await new Promise((r,j)=>{ws.onopen=r;ws.onerror=j;});
let id=0;const p=new Map();ws.onmessage=e=>{const m=JSON.parse(e.data);if(m.id){const q=p.get(m.id);if(q){p.delete(m.id);m.error?q.j(new Error(JSON.stringify(m.error))):q.r(m.result);}}};
const send=(method,params={})=>new Promise((r,j)=>{const n=++id;p.set(n,{r,j});ws.send(JSON.stringify({id:n,method,params}));});
const ev=async expression=>{const r=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true,userGesture:true});if(r.exceptionDetails)throw new Error(JSON.stringify(r.exceptionDetails));return r.result.value;};
await send('Runtime.enable');
if(width<700){await send('Emulation.setDeviceMetricsOverride',{width,height:844,deviceScaleFactor:2,mobile:true});await send('Emulation.setTouchEmulationEnabled',{enabled:true,maxTouchPoints:5});await send('Page.reload',{ignoreCache:true});await sleep(500);} else await sleep(500);
await ev(`document.querySelectorAll('.step-tab')[7].click();document.querySelector('#finishBtn').click();`);
await sleep(600);
const info=await ev(`(()=>{const box=s=>{const e=document.querySelector(s);if(!e)return null;const r=e.getBoundingClientRect();return {s,x:+r.x.toFixed(1),y:+r.y.toFixed(1),w:+r.width.toFixed(1),h:+r.height.toFixed(1)}};return JSON.stringify({vp:{w:innerWidth,h:innerHeight,docW:document.documentElement.scrollWidth,docH:document.documentElement.scrollHeight,scrollY},boxes:['#result','.result-inner','.result-top','.result-title','.score-line','.dim-grid','.dim-card','.result-note','.result-actions','#restartBtn','.site-footer'].map(box),dim:[...document.querySelectorAll('.dim-card')].map(e=>{const r=e.getBoundingClientRect();return {x:+r.x.toFixed(1),y:+r.y.toFixed(1),w:+r.width.toFixed(1),h:+r.height.toFixed(1),v:e.querySelector('.dim-value').textContent}}),marker:['D','I','S','C'].map(k=>document.querySelector('#marker'+k).style.left),overflow:document.documentElement.scrollWidth-innerWidth},null,2);})()`);
console.log(info);ws.close();chrome.kill();
