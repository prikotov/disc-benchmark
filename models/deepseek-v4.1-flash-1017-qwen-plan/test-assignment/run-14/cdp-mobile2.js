const {spawn}=require('child_process'); const path=require('path'),fs=require('fs'),os=require('os');
const PORT=9337, userDir=fs.mkdtempSync(path.join(os.tmpdir(),'disc-chrome-'));
const chrome=spawn('google-chrome',['--headless=new','--no-sandbox','--disable-gpu','--hide-scrollbars','--disable-dev-shm-usage','--no-first-run',`--remote-debugging-port=${PORT}`,`--user-data-dir=${userDir}`,'about:blank'],{stdio:'ignore'});
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
async function wait(){for(let i=0;i<100;i++){try{const r=await fetch(`http://127.0.0.1:${PORT}/json`);if(r.ok)return await r.json();}catch{}await sleep(100)}throw Error('no chrome')}
(async()=>{
 const t=(await wait()).find(t=>t.type==='page'); const ws=new WebSocket(t.webSocketDebuggerUrl);
 const pending=new Map(),events=[]; let seq=0;
 await new Promise((res,rej)=>{ws.onopen=res;ws.onerror=rej});
 ws.onmessage=e=>{const m=JSON.parse(e.data);if(m.id){const p=pending.get(m.id);if(p){pending.delete(m.id);m.error?p.reject(Error(JSON.stringify(m.error))):p.resolve(m.result)}}else events.push(m)};
 const send=(method,params={})=>new Promise((resolve,reject)=>{const id=++seq;pending.set(id,{resolve,reject});ws.send(JSON.stringify({id,method,params}))});
 const ev=async expression=>{const r=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true,userGesture:true});if(r.exceptionDetails)throw Error(JSON.stringify(r.exceptionDetails));return r.result.value};
 await send('Runtime.enable'); await send('Page.enable');
 await send('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:2,mobile:true,screenWidth:390,screenHeight:844});
 await send('Emulation.setTouchEmulationEnabled',{enabled:true,maxTouchPoints:5});
 await send('Page.navigate',{url:'file://'+path.resolve('index.html')}); await sleep(900);
 // click through to last via tabs and next
 for(let i=0;i<7;i++){await ev(`document.querySelector('#next-btn').click()`);await sleep(250)}
 const info=await ev(`(() => {const t=document.querySelector('.disc-tab.is-active');const tr=t.getBoundingClientRect();const c=document.querySelector('#steps').getBoundingClientRect();return {step:document.querySelector('#rootwizard').dataset.step, scrollLeft:document.querySelector('#steps').scrollLeft, scrollW:document.querySelector('#steps').scrollWidth, clientW:document.querySelector('#steps').clientWidth, tab:{left:tr.left,right:tr.right}, container:{left:c.left,right:c.right}, tabText:t.textContent, finishHidden:document.querySelector('#finish-btn').hidden, nextHidden:document.querySelector('#next-btn').hidden, actionsY:document.querySelector('.disc-actions').getBoundingClientRect().top, winY:scrollY};})()`);
 console.log('LAST STEP',JSON.stringify(info,null,2));
 // finish and inspect result mobile
 await ev(`document.querySelector('#finish-btn').click()`); await sleep(400);
 const result=await ev(`(() => {const r=el=>{const b=el.getBoundingClientRect();return{x:+b.x.toFixed(1),y:+b.y.toFixed(1),w:+b.width.toFixed(1),h:+b.height.toFixed(1)}};return {score:document.querySelector('#score-string').textContent, scrollW:document.documentElement.scrollWidth, shell:r(document.querySelector('.result-shell')), cards:[...document.querySelectorAll('.score-card')].map(r), grid:r(document.querySelector('.score-grid')), scrollH:document.documentElement.scrollHeight, title:document.title, focused:document.activeElement.id};})()`);
 console.log('RESULT MOBILE',JSON.stringify(result,null,2));
 const errors=events.filter(e=>['Runtime.exceptionThrown','Log.entryAdded'].includes(e.method));
 console.log('ERRORS',JSON.stringify(errors.map(e=>({m:e.method,p:e.params})),null,2));
 ws.close();chrome.kill('SIGKILL');
})().catch(e=>{console.error(e);chrome.kill('SIGKILL');process.exit(1)});
