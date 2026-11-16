import { spawn } from 'node:child_process';
import { setTimeout as sleep } from 'node:timers/promises';
import fs from 'node:fs';
const PORT = 9346;
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
  const order = (id) => ev(`Array.from(document.getElementById('${id}').children).filter(n=>n.tagName==='LI').map(n=>n.getAttribute('data-type')).join('')`);
  await ev(`document.getElementById('btnStart').click(); true`);
  const drag = (listId, fromIdx, toIdx) => `(() => {
    function fire(el, type, x, y) { el.dispatchEvent(new PointerEvent(type, { clientX: x, clientY: y, bubbles: true, cancelable: true, pointerId: 7, pointerType: 'mouse', button: 0, isPrimary: true })); }
    const ul = document.getElementById('${listId}');
    const lis = () => Array.from(ul.children).filter(n => n.tagName === 'LI');
    const li = lis()[${fromIdx}];
    const r = li.getBoundingClientRect();
    const sx = r.left + 40, sy = r.top + r.height / 2;
    const t = lis()[${toIdx}].getBoundingClientRect();
    const tx = t.left + 40, ty = ${toIdx} === 0 ? (t.top + 5) : (t.top + t.height - 5);
    fire(li, 'pointerdown', sx, sy);
    for (let i = 1; i <= 24; i++) fire(window, 'pointermove', sx + (tx - sx) * i / 24, sy + (ty - sy) * i / 24);
    fire(window, 'pointerup', tx, ty);
    return lis().map(n => n.getAttribute('data-type')).join('');
  }()`;
  console.log('after drag A list1:', await ev(drag('draggable-list1', 3, 0)));
  console.log('after drag B list2:', await ev(drag('draggable-list2', 0, 3)));
  for (let i = 0; i < 7; i++) await ev(`document.querySelector('[data-disc-next]').click(); true`);
  console.log('step now:', await ev(`document.querySelector('.disc-pane.is-active').id`));
  await ev(`document.querySelector('[data-step-btn="0"]').click(); true`);
  await ev(`document.querySelector('[data-step-btn="7"]').click(); true`);
  await ev(`document.querySelector('[data-disc-finish]').click(); true`);
  console.log('score:', await ev(`document.getElementById('discScore').textContent`));
  await ev(`document.querySelector('[data-copy]').click(); true`);
  await sleep(300);
  console.log('list2 before restart:', await order('draggable-list2'));
  await ev(`document.getElementById('btnRestart').click(); true`);
  console.log('list1 after restart :', await order('draggable-list1'));
  console.log('list2 after restart :', await order('draggable-list2'));
} finally { try { chrome.kill('SIGKILL'); } catch (e) {} }
setTimeout(()=>process.exit(0), 8000);
