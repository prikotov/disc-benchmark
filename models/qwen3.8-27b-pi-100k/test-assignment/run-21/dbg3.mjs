import { spawn } from 'node:child_process';
import { setTimeout as sleep } from 'node:timers/promises';
import fs from 'node:fs';
const PORT = 9344;
const chrome = spawn('/usr/bin/google-chrome', ['--headless=new','--no-sandbox','--disable-gpu','--disable-dev-shm-usage','--remote-debugging-port='+PORT,'--user-data-dir='+fs.mkdtempSync('/tmp/chrome-dbg-'),'about:blank'], { stdio: 'ignore' });
async function getJson(p){ return (await fetch('http://127.0.0.1:'+PORT+p)).json(); }
let ws, idc=0; const pending=new Map();
function send(m,p={}){ return new Promise((res,rej)=>{ const id=++idc; pending.set(id,{res,rej}); ws.send(JSON.stringify({id,method:m,params:p})); }); }
try {
  let targets; for(let i=0;i<60;i++){ await sleep(300); try{ targets=await getJson('/json/list'); if(targets.length)break; }catch(e){} }
  const page = targets.find(t=>t.type==='page');
  ws = new WebSocket(page.webSocketDebuggerUrl);
  await new Promise((r,j)=>{ws.onopen=r;ws.onerror=j;});
  ws.onmessage=(ev)=>{ const m=JSON.parse(ev.data); if(m.id&&pending.has(m.id)){const{res,rej}=pending.get(m.id);pending.delete(m.id); m.error?rej(new Error(JSON.stringify(m.error))):res(m.result);} };
  await send('Runtime.enable'); await send('Page.enable');
  await send('Page.navigate',{url:'file://'+process.cwd()+'/index.html'});
  await sleep(1200);
  async function ev(e){ const r=await send('Runtime.evaluate',{expression:e,returnByValue:true,awaitPromise:true});
    if(r.exceptionDetails) console.log('EXC:', JSON.stringify(r.exceptionDetails).slice(0,400));
    return r.result && r.result.value; }
  await ev(`document.getElementById('btnStart').click(); true`);
  // geometry report
  console.log(await ev(`(() => {
    const ul = document.getElementById('draggable-list1');
    const l = Array.from(ul.children).filter(n => n.tagName === 'LI');
    return JSON.stringify(l.map(n => ({ t: n.getAttribute('data-type'), text: n.textContent.trim().slice(0,14), rect: [Math.round(n.getBoundingClientRect().top), Math.round(n.getBoundingClientRect().height)] })));
  })()`));
  // fine-grained drag: 24 steps, log order after each
  console.log(await ev(`(() => {
    function fire(el, type, x, y) { el.dispatchEvent(new PointerEvent(type, { clientX: x, clientY: y, bubbles: true, cancelable: true, pointerId: 7, pointerType: 'mouse', button: 0, isPrimary: true })); }
    const ul = document.getElementById('draggable-list1');
    const lis = Array.from(ul.children).filter(n => n.tagName === 'LI');
    const li = lis[3];
    const r = li.getBoundingClientRect();
    const sx = r.left + 40, sy = r.top + r.height / 2;
    const t0 = lis[0].getBoundingClientRect();
    const tx = t0.left + 40, ty = t0.top + 6;
    const order = () => Array.from(ul.children).filter(n => n.tagName === 'LI').map(n => n.getAttribute('data-type')).join('');
    const log = [order()];
    fire(li, 'pointerdown', sx, sy);
    const steps = 24;
    for (let i = 1; i <= steps; i++) {
      fire(window, 'pointermove', sx + (tx - sx) * i / steps, sy + (ty - sy) * i / steps);
      log.push(order());
    }
    fire(window, 'pointerup', tx, ty);
    log.push('UP:' + order());
    return log.join(' | ');
  })()`));
} finally { chrome.kill('SIGKILL'); }
