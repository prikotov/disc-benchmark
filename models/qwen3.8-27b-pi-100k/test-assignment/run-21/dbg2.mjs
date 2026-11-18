import { spawn } from 'node:child_process';
import { setTimeout as sleep } from 'node:timers/promises';
import fs from 'node:fs';
const PORT = 9343;
const chrome = spawn('/usr/bin/google-chrome', ['--headless=new','--no-sandbox','--disable-gpu','--disable-dev-shm-usage','--remote-debugging-port='+PORT,'--user-data-dir='+fs.mkdtempSync('/tmp/chrome-dbg-'),'about:blank'], { stdio: 'ignore' });
async function getJson(p){ return (await fetch('http://127.0.0.1:'+PORT+p)).json(); }
let ws, idc=0; const pending=new Map();
function send(m,p={}){ return new Promise((res,rej)=>{ const id=++idc; pending.set(id,{res,rej}); ws.send(JSON.stringify({id,method:m,params:p})); }); }
const events=[];
try {
  let targets; for(let i=0;i<60;i++){ await sleep(300); try{ targets=await getJson('/json/list'); if(targets.length)break; }catch(e){} }
  const page = targets.find(t=>t.type==='page');
  ws = new WebSocket(page.webSocketDebuggerUrl);
  await new Promise((r,j)=>{ws.onopen=r;ws.onerror=j;});
  ws.onmessage=(ev)=>{ const m=JSON.parse(ev.data); if(m.id&&pending.has(m.id)){const{res,rej}=pending.get(m.id);pending.delete(m.id); m.error?rej(new Error(JSON.stringify(m.error))):res(m.result);} else if(m.method) events.push(m); };
  await send('Runtime.enable'); await send('Page.enable');
  await send('Page.navigate',{url:'file://'+process.cwd()+'/index.html'});
  await sleep(1500);
  async function ev(e){ const r=await send('Runtime.evaluate',{expression:e,returnByValue:true,awaitPromise:true});
    if(r.exceptionDetails) console.log('EXC:', JSON.stringify(r.exceptionDetails).slice(0,600));
    return r.result && r.result.value; }
  await ev(`document.getElementById('btnStart').click(); true`);
  // exact drag attempt from smoke (target = ul!)
  await ev(`(() => {
    function fire(el, type, x, y) { el.dispatchEvent(new PointerEvent(type, { clientX: x, clientY: y, bubbles: true, cancelable: true, pointerId: 7, pointerType: 'mouse', button: 0, isPrimary: true })); }
    const ul = document.getElementById('draggable-list1');
    const lis = Array.from(ul.children).filter(n => n.tagName === 'LI');
    const li = lis[3];
    const r = li.getBoundingClientRect();
    const sx = r.left + 30, sy = r.top + r.height / 2;
    const target = lis[0].getBoundingClientRect();
    const tx = target.left + 30, ty = target.top + 4;
    fire(ul, 'pointerdown', sx, sy);
    for (let i = 1; i <= 8; i++) fire(window, 'pointermove', sx + (tx - sx) * i / 8, sy + (ty - sy) * i / 8);
    fire(window, 'pointerup', tx, ty);
    return 'drag-attempted';
  })()`);
  for (let i = 1; i <= 6; i++) {
    await ev(`document.querySelector('[data-disc-next]').click(); true`);
    console.log('after next #'+i, 'active pane =', await ev(`document.querySelector('.disc-pane.is-active') ? document.querySelector('.disc-pane.is-active').id : 'NONE'`));
  }
  const errEvents = events.filter(e=>e.method==='Runtime.exceptionThrown');
  console.log('exceptions:', errEvents.length, errEvents.map(e=>JSON.stringify(e.params).slice(0,200)));
} finally { chrome.kill('SIGKILL'); }
