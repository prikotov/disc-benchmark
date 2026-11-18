const {spawn}=require('child_process'); const path=require('path'),fs=require('fs'),os=require('os');
const PORT=9339, userDir=fs.mkdtempSync(path.join(os.tmpdir(),'disc-chrome-'));
const chrome=spawn('google-chrome',['--headless=new','--no-sandbox','--disable-gpu','--hide-scrollbars','--disable-dev-shm-usage','--no-first-run',`--remote-debugging-port=${PORT}`,`--user-data-dir=${userDir}`,'about:blank'],{stdio:'ignore'});
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
(async()=>{
 let targets;for(let i=0;i<100;i++){try{const r=await fetch(`http://127.0.0.1:${PORT}/json`);if(r.ok){targets=await r.json();break}}catch{}await sleep(100)}
 const ws=new WebSocket(targets.find(t=>t.type==='page').webSocketDebuggerUrl);const pending=new Map(),events=[];let seq=0;
 await new Promise((res,rej)=>{ws.onopen=res;ws.onerror=rej});
 ws.onmessage=e=>{const m=JSON.parse(e.data);if(m.id){const p=pending.get(m.id);if(p){pending.delete(m.id);m.error?p.reject(Error(JSON.stringify(m.error))):p.resolve(m.result)}}else events.push(m)};
 const send=(method,params={})=>new Promise((resolve,reject)=>{const id=++seq;pending.set(id,{resolve,reject});ws.send(JSON.stringify({id,method,params}))});
 const ev=async expression=>{const r=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true,userGesture:true});if(r.exceptionDetails)throw Error(JSON.stringify(r.exceptionDetails));return r.result.value};
 await send('Runtime.enable');await send('Page.enable');await send('Network.enable');
 const reqs=[];ws.addEventListener('message',e=>{const m=JSON.parse(e.data);if(m.method==='Network.requestWillBeSent')reqs.push(m.params.request.url)});
 await send('Page.navigate',{url:'file://'+path.resolve('index.html')});await sleep(1200);
 console.log('REQUESTS',JSON.stringify(reqs,null,2));
 console.log('RESOURCES',JSON.stringify(await ev(`({perf:performance.getEntriesByType('resource').map(x=>x.name),imgs:document.images.length,links:document.querySelectorAll('link').length,externalScripts:[...document.scripts].filter(s=>s.src).map(s=>s.src),iframes:document.querySelectorAll('iframe').length,text:document.querySelectorAll('.disc-item').length,lists:document.querySelectorAll('.disc-list').length,panes:document.querySelectorAll('.disc-pane').length,tabs:document.querySelectorAll('.disc-tab').length})`),null,2));
 const errors=events.filter(e=>['Runtime.exceptionThrown','Log.entryAdded'].includes(e.method));console.log('ERRORS',JSON.stringify(errors.map(e=>({m:e.method,p:e.params})),null,2));
 ws.close();chrome.kill('SIGKILL');
})().catch(e=>{console.error(e);chrome.kill('SIGKILL');process.exit(1)});
