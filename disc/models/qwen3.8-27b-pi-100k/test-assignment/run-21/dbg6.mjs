import { spawn } from 'node:child_process';
import { setTimeout as sleep } from 'node:timers/promises';
import fs from 'node:fs';
const PORT = 9347;
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
  await ev(`(() => {
    const li = Array.from(document.getElementById('draggable-list1').children).filter(n=>n.tagName==='LI')[3];
    li.focus();
    for (let i = 0; i < 3; i++) li.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowUp', bubbles: true, cancelable: true }));
    return true;
  })()`);
  console.log('keyboard ArrowUp×3 on last li of list1 →', await order('draggable-list1'), '(expect scid? s,i,c,d)');
  await ev(`(() => {
    const li = Array.from(document.getElementById('draggable-list1').children).filter(n=>n.tagName==='LI')[0];
    li.focus();
    for (let i = 0; i < 3; i++) li.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowDown', bubbles: true, cancelable: true }));
    return true;
  })()`);
  console.log('keyboard ArrowDown×3 on first li of list1 →', await order('draggable-list1'), '(expect icds)');
} finally { try { chrome.kill('SIGKILL'); } catch (e) {} }
setTimeout(()=>process.exit(0), 7000);
