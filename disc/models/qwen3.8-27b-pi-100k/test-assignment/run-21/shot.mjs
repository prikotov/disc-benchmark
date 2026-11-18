import { spawn } from 'node:child_process';
import { setTimeout as sleep } from 'node:timers/promises';
import fs from 'node:fs';
const PORT = 9348;
const chrome = spawn('/usr/bin/google-chrome', ['--headless=new','--no-sandbox','--disable-gpu','--disable-dev-shm-usage','--remote-debugging-port='+PORT,'--user-data-dir='+fs.mkdtempSync('/tmp/chrome-shot-'),'about:blank'], { stdio: 'ignore' });
async function getJson(p){ return (await fetch('http://127.0.0.1:'+PORT+p)).json(); }
let ws, idc=0; const pending=new Map();
function send(m,p={}){ return new Promise((res,rej)=>{ const id=++idc; pending.set(id,{res,rej}); ws.send(JSON.stringify({id,method:m,params:p})); }); }
try {
  let targets; for(let i=0;i<60;i++){ await sleep(300); try{ targets=await getJson('/json/list'); if(targets.length)break; }catch(e){} }
  const page = targets.find(t=>t.type==='page');
  ws = new WebSocket(page.webSocketDebuggerUrl);
  await new Promise((r,j)=>{ws.onopen=r;ws.onerror=j;});
  ws.onmessage=(ev)=>{ const m=JSON.parse(ev.data); if(m.id&&pending.has(m.id)){const{res,rej}=pending.get(m.id);pending.delete(m.id); m.error?rej(new Error(JSON.stringify(m.error))):res(m.result);} };
  await send('Page.enable'); await send('Runtime.enable');
  await send('Emulation.setDeviceMetricsOverride',{width:1024,height:900,deviceScaleFactor:2,mobile:false});
  await send('Page.navigate',{url:'file://'+process.cwd()+'/index.html'});
  await sleep(1200);
  async function ev(e){ const r=await send('Runtime.evaluate',{expression:e,returnByValue:true,awaitPromise:true});
    if(r.exceptionDetails) console.log('EXC', JSON.stringify(r.exceptionDetails).slice(0,300)); return r.result && r.result.value; }
  const shot = async (name) => { const r = await send('Page.captureScreenshot',{format:'png'}); fs.writeFileSync(name, Buffer.from(r.data, 'base64')); };
  await shot('shot-start.png');
  await ev(`document.getElementById('btnStart').click(); true`);
  await sleep(200);
  // reorder list1: move last to first
  const drag = `(() => {
    function fire(el, type, x, y) { el.dispatchEvent(new PointerEvent(type, { clientX: x, clientY: y, bubbles: true, cancelable: true, pointerId: 7, pointerType: 'mouse', button: 0, isPrimary: true })); }
    const ul = document.getElementById('draggable-list1');
    const lis = () => Array.from(ul.children).filter(n => n.tagName === 'LI');
    const li = lis()[3];
    const r = li.getBoundingClientRect();
    const sx = r.left + 40, sy = r.top + r.height / 2;
    const t = lis()[0].getBoundingClientRect();
    const tx = t.left + 40, ty = t.top + 5;
    fire(li, 'pointerdown', sx, sy);
    for (let i = 1; i <= 24; i++) fire(window, 'pointermove', sx + (tx - sx) * i / 24, sy + (ty - sy) * i / 24);
    fire(window, 'pointerup', tx, ty);
    return true;
  }())`;
  await ev(drag);
  for (let i = 0; i < 7; i++) await ev(`document.querySelector('[data-disc-next]').click(); true`);
  await sleep(150);
  await shot('shot-test-laststep.png');
  await ev(`document.querySelector('[data-disc-finish]').click(); true`);
  await sleep(400);
  await shot('shot-result.png');
  console.log('score:', await ev(`document.getElementById('discScore').textContent`));
  console.log('copy label:', await ev(`document.querySelector('.copyfield__btnText').textContent`));
} finally { try { chrome.kill('SIGKILL'); } catch(e){} }
setTimeout(()=>process.exit(0), 9000);
