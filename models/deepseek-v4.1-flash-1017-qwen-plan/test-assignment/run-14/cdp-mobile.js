const {spawn}=require('child_process'); const path=require('path'),fs=require('fs'),os=require('os');
const PORT=9336, userDir=fs.mkdtempSync(path.join(os.tmpdir(),'disc-chrome-'));
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
 const touch=(type,points)=>send('Input.dispatchTouchEvent',{type,touchPoints:points});
 await send('Runtime.enable'); await send('Page.enable');
 await send('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:2,mobile:true,screenWidth:390,screenHeight:844});
 await send('Emulation.setTouchEmulationEnabled',{enabled:true,maxTouchPoints:5});
 await send('Page.navigate',{url:'file://'+path.resolve('index.html')}); await sleep(1000);
 const metrics=await ev(`(() => {
   const r=el=>{const b=el.getBoundingClientRect();return{x:+b.x.toFixed(1),y:+b.y.toFixed(1),w:+b.width.toFixed(1),h:+b.height.toFixed(1)}};
   const active=document.querySelector('.disc-pane.is-active');
   return {inner:{w:innerWidth,h:innerHeight},scrollW:document.documentElement.scrollWidth,scrollH:document.documentElement.scrollHeight,
     shell:r(document.querySelector('.test-shell')),cards:[...active.querySelectorAll('.disc-card')].map(r),
     tabs:{w:r(document.querySelector('#steps')).w,scrollW:document.querySelector('#steps').scrollWidth,clientW:document.querySelector('#steps').clientWidth},
     items:[...active.querySelectorAll('.disc-item')].slice(0,4).map(r),
     handle:r(active.querySelector('.disc-handle')),
     actions:r(document.querySelector('.disc-actions')),
     footer:r(document.querySelector('.site-footer')),
     font:getComputedStyle(document.querySelector('.disc-item')).fontSize
   };
 })()`);
 console.log('MOBILE METRICS',JSON.stringify(metrics,null,2));
 // touch drag first item by handle to below last
 const h=await ev(`(() => {const li=document.querySelector('#draggable-list1 .disc-item');const h=li.querySelector('.disc-handle');const hr=h.getBoundingClientRect();const lr=li.getBoundingClientRect();return {hx:hr.x+hr.width/2,hy:hr.y+hr.height/2,itemY:lr.y+lr.height/2,items:[...document.querySelectorAll('#draggable-list1 .disc-item')].map(x=>{const r=x.getBoundingClientRect();return {top:r.top,bottom:r.bottom}})}})()`);
 console.log('TOUCH TARGET',JSON.stringify(h));
 await touch('touchStart',[{x:h.hx,y:h.hy,id:1,radiusX:2,radiusY:2,force:1}]);
 await sleep(60);
 for(let i=1;i<=10;i++){const y=h.hy+(h.items[3].bottom+8-h.hy)*i/10;await touch('touchMove',[{x:h.hx,y,id:1,radiusX:2,radiusY:2,force:1}]);await sleep(25)}
 await touch('touchEnd',[]);
 await sleep(250);
 console.log('AFTER TOUCH',JSON.stringify(await ev(`({order:[...document.querySelectorAll('#draggable-list1 .disc-item')].map(x=>x.textContent.trim()), ghost:!!document.querySelector('.disc-drag-ghost'), body:document.body.className, marks:document.querySelectorAll('.is-drop-before,.is-drop-end').length, live:document.querySelector('#live-status').textContent})`),null,2));
 // touch on text should not create ghost
 const text=await ev(`(() => {const li=document.querySelector('#draggable-list2 .disc-item');const r=li.getBoundingClientRect();return {x:r.x+100,y:r.y+r.height/2}})()`);
 await touch('touchStart',[{x:text.x,y:text.y,id:2,radiusX:2,radiusY:2,force:1}]); await sleep(80);
 console.log('TOUCH TEXT DOWN',JSON.stringify(await ev(`({ghost:!!document.querySelector('.disc-drag-ghost'), source:!!document.querySelector('.is-ghost-source')})`)));
 await touch('touchEnd',[]); await sleep(100);
 // tabs horizontal scroll info and active centering after next
 console.log('TAB STATE',JSON.stringify(await ev(`({scrollLeft:document.querySelector('#steps').scrollLeft, scrollWidth:document.querySelector('#steps').scrollWidth, clientWidth:document.querySelector('#steps').clientWidth, activeTab:document.querySelector('.disc-tab.is-active').textContent})`)));
 await ev(`document.querySelector('#next-btn').click()`); await sleep(400);
 console.log('TAB AFTER NEXT',JSON.stringify(await ev(`({step:document.querySelector('#rootwizard').dataset.step, scrollLeft:document.querySelector('#steps').scrollLeft, activeTab:document.querySelector('.disc-tab.is-active').textContent, activeLeft:(()=>{const b=document.querySelector('.disc-tab.is-active').getBoundingClientRect();const c=document.querySelector('#steps').getBoundingClientRect();return {tabLeft:b.left,tabRight:b.right,containerLeft:c.left,containerRight:c.right}})()})`),null,2));
 const errors=events.filter(e=>['Runtime.exceptionThrown','Log.entryAdded'].includes(e.method));
 console.log('ERRORS',JSON.stringify(errors.map(e=>({m:e.method,p:e.params})),null,2));
 ws.close();chrome.kill('SIGKILL');
})().catch(e=>{console.error(e);chrome.kill('SIGKILL');process.exit(1)});
