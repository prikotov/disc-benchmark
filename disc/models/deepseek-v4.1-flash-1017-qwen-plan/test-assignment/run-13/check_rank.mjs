import { spawn } from 'node:child_process';
const port=9667;const chrome=spawn('google-chrome',['--headless=new','--disable-gpu','--no-sandbox',`--remote-debugging-port=${port}`,'--user-data-dir=/tmp/disc-rank','file://'+process.cwd()+'/index.html'],{stdio:['ignore','ignore','ignore']});
const sleep=ms=>new Promise(r=>setTimeout(r,ms));let target;for(let i=0;i<60;i++){try{const l=await(await fetch(`http://127.0.0.1:${port}/json`)).json();target=l.find(x=>x.type==='page'&&x.url.includes('index.html'));if(target)break;}catch{}await sleep(150);}
const ws=new WebSocket(target.webSocketDebuggerUrl);await new Promise((r,j)=>{ws.onopen=r;ws.onerror=j;});let id=0;const p=new Map();ws.onmessage=e=>{const m=JSON.parse(e.data);if(m.id){const q=p.get(m.id);if(q){p.delete(m.id);m.error?q.j(new Error(JSON.stringify(m.error))):q.r(m.result);}}};
const send=(method,params={})=>new Promise((r,j)=>{const n=++id;p.set(n,{r,j});ws.send(JSON.stringify({id:n,method,params}));});const ev=async expression=>{const r=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true,userGesture:true});if(r.exceptionDetails)throw new Error(JSON.stringify(r.exceptionDetails));return r.result.value;};
await send('Runtime.enable');await sleep(400);
async function rankInfo(){return await ev(`JSON.stringify([...document.querySelector('.rank-list').children].map(li=>({d:li.dataset.pos,t:li.querySelector('.option-text').textContent,c:getComputedStyle(li.querySelector('.option-rank'),'::before').content,r:li.querySelector('.option-rank').dataset.rank})))`);}
console.log('initial',await rankInfo());
await ev(`document.querySelector('.rank-list .option').focus()`);
await send('Input.dispatchKeyEvent',{type:'keyDown',key:'ArrowDown',code:'ArrowDown',windowsVirtualKeyCode:40,nativeVirtualKeyCode:40});
await send('Input.dispatchKeyEvent',{type:'keyUp',key:'ArrowDown',code:'ArrowDown',windowsVirtualKeyCode:40,nativeVirtualKeyCode:40});
await sleep(100);
console.log('after',await rankInfo());
ws.close();chrome.kill();
