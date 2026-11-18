const { spawn } = require('child_process');
const path = require('path'); const fs = require('fs'); const os = require('os');
const PORT=9335; const userDir=fs.mkdtempSync(path.join(os.tmpdir(),'disc-chrome-'));
const chrome=spawn('google-chrome',['--headless=new','--no-sandbox','--disable-gpu','--hide-scrollbars','--disable-dev-shm-usage','--no-first-run',`--remote-debugging-port=${PORT}`,`--user-data-dir=${userDir}`,'--window-size=1440,1100','about:blank'],{stdio:'ignore'});
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
async function wait(){for(let i=0;i<100;i++){try{const r=await fetch(`http://127.0.0.1:${PORT}/json`);if(r.ok)return await r.json();}catch{}await sleep(100)}throw Error('no chrome')}
(async()=>{
 const t=(await wait()).find(t=>t.type==='page'); const ws=new WebSocket(t.webSocketDebuggerUrl);
 const pending=new Map(); const events=[]; let seq=0;
 await new Promise((res,rej)=>{ws.onopen=res;ws.onerror=rej});
 ws.onmessage=e=>{const m=JSON.parse(e.data); if(m.id){const p=pending.get(m.id);if(p){pending.delete(m.id);m.error?p.reject(Error(JSON.stringify(m.error))):p.resolve(m.result)}}else events.push(m)};
 const send=(method,params={})=>new Promise((resolve,reject)=>{const id=++seq;pending.set(id,{resolve,reject});ws.send(JSON.stringify({id,method,params}))});
 const ev=async expression=>{const r=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true,userGesture:true});if(r.exceptionDetails)throw Error(JSON.stringify(r.exceptionDetails));return r.result.value};
 const mouse=(type,x,y,extra={})=>send('Input.dispatchMouseEvent',{type,x,y,...extra});
 await send('Runtime.enable'); await send('Page.enable'); await send('Page.navigate',{url:'file://'+path.resolve('index.html')}); await sleep(900);

 const rects=await ev(`[...document.querySelectorAll('#draggable-list1 .disc-item')].map(li=>{const r=li.getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2,top:r.top,bottom:r.bottom}})`);
 // click without moving should not reorder
 const r0=rects[0];
 await mouse('mouseMoved',r0.x,r0.y,{button:'none',buttons:0});
 await mouse('mousePressed',r0.x,r0.y,{button:'left',buttons:1,clickCount:1});
 await sleep(100);
 const duringClick=await ev(`({ghost:!!document.querySelector('.disc-drag-ghost'), ghostSource:!!document.querySelector('.is-ghost-source'), order:[...document.querySelectorAll('#draggable-list1 .disc-item')].map(x=>x.textContent.trim())})`);
 await mouse('mouseReleased',r0.x,r0.y,{button:'left',buttons:0,clickCount:1});
 await sleep(150);
 const afterClick=await ev(`({ghost:!!document.querySelector('.disc-drag-ghost'), ghostSource:!!document.querySelector('.is-ghost-source'), order:[...document.querySelectorAll('#draggable-list1 .disc-item')].map(x=>x.textContent.trim()), focus:document.activeElement.className})`);
 // drag last to top
 const last=rects[3];
 const first=rects[0];
 await mouse('mouseMoved',last.x,last.y,{button:'none',buttons:0});
 await mouse('mousePressed',last.x,last.y,{button:'left',buttons:1,clickCount:1});
 await sleep(50);
 for(let i=1;i<=8;i++){const y=last.y+(first.top-4-last.y)*i/8;await mouse('mouseMoved',last.x,y,{button:'none',buttons:1});await sleep(25)}
 await mouse('mouseReleased',last.x,first.top-4,{button:'left',buttons:0,clickCount:1});
 await sleep(200);
 const afterDrag=await ev(`({order:[...document.querySelectorAll('#draggable-list1 .disc-item')].map(x=>x.textContent.trim()), types:[...document.querySelectorAll('#draggable-list1 .disc-item')].map(x=>x.dataset.type), ghost:!!document.querySelector('.disc-drag-ghost'), marks:document.querySelectorAll('.is-drop-before,.is-drop-end').length, focus:document.activeElement.className})`);
 // keyboard reorder
 await ev(`document.querySelector('#draggable-list1 .disc-item').focus()`);
 await send('Input.dispatchKeyEvent',{type:'keyDown',key:'ArrowDown',code:'ArrowDown',windowsVirtualKeyCode:40,nativeVirtualKeyCode:40,modifiers:1});
 await send('Input.dispatchKeyEvent',{type:'keyUp',key:'ArrowDown',code:'ArrowDown',windowsVirtualKeyCode:40,nativeVirtualKeyCode:40,modifiers:1});
 await sleep(100);
 const afterKey=await ev(`({order:[...document.querySelectorAll('#draggable-list1 .disc-item')].map(x=>x.textContent.trim()), focus:document.activeElement.textContent.trim(), live:document.querySelector('#live-status').textContent})`);
 console.log('DURING CLICK',JSON.stringify(duringClick));
 console.log('AFTER CLICK',JSON.stringify(afterClick));
 console.log('AFTER DRAG',JSON.stringify(afterDrag));
 console.log('AFTER KEY',JSON.stringify(afterKey));
 const errors=events.filter(e=>['Runtime.exceptionThrown','Log.entryAdded'].includes(e.method));
 console.log('ERRORS',JSON.stringify(errors.map(e=>({m:e.method,p:e.params})),null,2));
 ws.close();chrome.kill('SIGKILL');
})().catch(e=>{console.error(e);chrome.kill('SIGKILL');process.exit(1)});
