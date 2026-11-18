import { spawn } from 'node:child_process';
import { writeFileSync } from 'node:fs';
const port=9669;const chrome=spawn('google-chrome',['--headless=new','--disable-gpu','--no-sandbox',`--remote-debugging-port=${port}`,'--user-data-dir=/tmp/disc-dump','file://'+process.cwd()+'/index.html'],{stdio:['ignore','ignore','ignore']});
const sleep=ms=>new Promise(r=>setTimeout(r,ms));let target;for(let i=0;i<60;i++){try{const l=await(await fetch(`http://127.0.0.1:${port}/json`)).json();target=l.find(x=>x.type==='page'&&x.url.includes('index.html'));if(target)break;}catch{}await sleep(150);}
const ws=new WebSocket(target.webSocketDebuggerUrl);await new Promise((r,j)=>{ws.onopen=r;ws.onerror=j;});let id=0;const p=new Map();ws.onmessage=e=>{const m=JSON.parse(e.data);if(m.id){const q=p.get(m.id);if(q){p.delete(m.id);m.error?q.j(new Error(JSON.stringify(m.error))):q.r(m.result);}}};
const send=(method,params={})=>new Promise((r,j)=>{const n=++id;p.set(n,{r,j});ws.send(JSON.stringify({id:n,method,params}));});const ev=async expression=>{const r=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw new Error(JSON.stringify(r.exceptionDetails));return r.result.value;};
await send('Runtime.enable');await sleep(400);
const data=await ev(`JSON.stringify([...document.querySelectorAll('.disc-list')].map(l=>[...l.children].map(li=>({type:li.dataset.type,text:li.textContent.trim(),inner:li.innerText.trim(),id:l.id}))))`);
writeFileSync('/tmp/dom_data.json',data);
console.log('written',data.length);
ws.close();chrome.kill();
