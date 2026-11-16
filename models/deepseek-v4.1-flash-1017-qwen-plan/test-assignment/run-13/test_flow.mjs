import { spawn } from 'node:child_process';
const port=9555;const chrome=spawn('google-chrome',['--headless=new','--disable-gpu','--no-sandbox',`--remote-debugging-port=${port}`,'--user-data-dir=/tmp/disc-flow','file://'+process.cwd()+'/index.html'],{stdio:['ignore','ignore','ignore']});
const sleep=ms=>new Promise(r=>setTimeout(r,ms));let target;for(let i=0;i<60;i++){try{const l=await(await fetch(`http://127.0.0.1:${port}/json`)).json();target=l.find(x=>x.type==='page'&&x.url.includes('index.html'));if(target)break;}catch{}await sleep(150);}
const ws=new WebSocket(target.webSocketDebuggerUrl);await new Promise((r,j)=>{ws.onopen=r;ws.onerror=j;});let id=0;const p=new Map();const events=[];ws.onmessage=e=>{const m=JSON.parse(e.data);if(m.id){const q=p.get(m.id);if(q){p.delete(m.id);m.error?q.j(new Error(JSON.stringify(m.error))):q.r(m.result);}}else events.push(m);};
const send=(method,params={})=>new Promise((r,j)=>{const n=++id;p.set(n,{r,j});ws.send(JSON.stringify({id:n,method,params}));});const ev=async expression=>{const r=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true,userGesture:true});if(r.exceptionDetails)throw new Error(JSON.stringify(r.exceptionDetails));return r.result.value;};
await send('Runtime.enable');await sleep(400);
const states=[];
for(let i=0;i<7;i++){
  states.push(JSON.parse(await ev(`JSON.stringify({counter:document.querySelector('#stepCounter').textContent,pct:document.querySelector('#progressPercent').textContent,width:document.querySelector('#discProgress').style.width,activeTab:document.querySelector('.step-tab.is-active').textContent,prevDisabled:document.querySelector('#prevBtn').disabled,nextHidden:document.querySelector('#nextBtn').hidden,finishHidden:document.querySelector('#finishBtn').hidden,visiblePanes:Array.from(document.querySelectorAll('.step-pane')).filter(p=>!p.hidden).map(p=>p.dataset.stepPane)})`)));
  await ev(`document.querySelector('#nextBtn').click()`);await sleep(120);
}
states.push(JSON.parse(await ev(`JSON.stringify({counter:document.querySelector('#stepCounter').textContent,pct:document.querySelector('#progressPercent').textContent,width:document.querySelector('#discProgress').style.width,activeTab:document.querySelector('.step-tab.is-active').textContent,prevDisabled:document.querySelector('#prevBtn').disabled,nextHidden:document.querySelector('#nextBtn').hidden,finishHidden:document.querySelector('#finishBtn').hidden,visiblePanes:Array.from(document.querySelectorAll('.step-pane')).filter(p=>!p.hidden).map(p=>p.dataset.stepPane)})`)));
console.log(JSON.stringify(states,null,2));
console.log('errors', events.filter(e=>e.method==='Runtime.exceptionThrown').length);
ws.close();chrome.kill();
