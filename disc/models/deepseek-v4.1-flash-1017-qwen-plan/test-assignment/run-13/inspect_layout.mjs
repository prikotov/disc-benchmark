import { spawn } from 'node:child_process';
const width = Number(process.argv[2] || 1440), height = Number(process.argv[3] || 1000);
const port = 9300 + Math.floor(Math.random()*500);
const chrome = spawn('google-chrome', ['--headless=new','--disable-gpu','--no-sandbox','--hide-scrollbars',`--remote-debugging-port=${port}`,`--user-data-dir=/tmp/disc-layout-${port}`,`--window-size=${width},${height}`,'file://' + process.cwd() + '/index.html'], {stdio:['ignore','ignore','ignore']});
const sleep = ms => new Promise(r=>setTimeout(r,ms));
let target;
for(let i=0;i<60;i++){try{const l=await(await fetch(`http://127.0.0.1:${port}/json`)).json();target=l.find(x=>x.type==='page'&&x.url.includes('index.html'));if(target)break;}catch{}await sleep(150);}
if(!target){console.log('no target');chrome.kill();process.exit(1);}
const ws=new WebSocket(target.webSocketDebuggerUrl);await new Promise((r,j)=>{ws.onopen=r;ws.onerror=j;});
let id=0;const p=new Map();ws.onmessage=e=>{const m=JSON.parse(e.data);if(m.id){const q=p.get(m.id);if(q){p.delete(m.id);m.error?q.j(new Error(JSON.stringify(m.error))):q.r(m.result);}}};
const send=(method,params={})=>new Promise((r,j)=>{const n=++id;p.set(n,{r,j});ws.send(JSON.stringify({id:n,method,params}));});
const ev=async expression=>{const r=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw new Error(JSON.stringify(r.exceptionDetails));return r.result.value;};
await send('Runtime.enable');
if(width<700){await send('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:2,mobile:true});await send('Emulation.setTouchEmulationEnabled',{enabled:true,maxTouchPoints:5});await send('Page.enable');await send('Page.reload',{ignoreCache:true});}
await sleep(600);
const info = await ev(`(()=>{
 const box=(sel)=>{const e=document.querySelector(sel);if(!e)return null;const r=e.getBoundingClientRect();const cs=getComputedStyle(e);return {sel,x:+r.x.toFixed(1),y:+r.y.toFixed(1),w:+r.width.toFixed(1),h:+r.height.toFixed(1),font:cs.fontSize,display:cs.display,overflow:cs.overflow}};
 return JSON.stringify({viewport:{w:innerWidth,h:innerHeight,docW:document.documentElement.scrollWidth,docH:document.documentElement.scrollHeight,scrollY},
 boxes:['.site-header','.app-view','.test-top','.title','.hero-lead','.hero-meta','.stepper','.steps','.progress-wrap','.panes','.questions-grid','.q-card','.option','.drag-hint','.actions','#prevBtn','#nextBtn','.action-hint','.site-footer'].map(box),
 actions:[...document.querySelector('.actions').children].filter(e=>getComputedStyle(e).display!=='none').map(e=>{const r=e.getBoundingClientRect();return {tag:e.tagName,cls:e.className,text:e.textContent.trim().slice(0,30),x:+r.x.toFixed(1),w:+r.width.toFixed(1)}}),
 cards:[...document.querySelectorAll('.q-card')].slice(0,3).map(e=>{const r=e.getBoundingClientRect();return {x:+r.x.toFixed(1),y:+r.y.toFixed(1),w:+r.width.toFixed(1),h:+r.height.toFixed(1)}})
},null,2);})()`);
console.log(info);
ws.close();chrome.kill();
