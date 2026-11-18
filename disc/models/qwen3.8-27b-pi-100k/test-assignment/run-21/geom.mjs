import { spawn } from 'node:child_process';
import { setTimeout as sleep } from 'node:timers/promises';
import fs from 'node:fs';
const PORT = 9349;
const chrome = spawn('/usr/bin/google-chrome', ['--headless=new','--no-sandbox','--disable-gpu','--disable-dev-shm-usage','--remote-debugging-port='+PORT,'--user-data-dir='+fs.mkdtempSync('/tmp/chrome-geom-'),'about:blank'], { stdio: 'ignore' });
async function getJson(p){ return (await fetch('http://127.0.0.1:'+PORT+p)).json(); }
let ws, idc=0; const pending=new Map();
function send(m,p={}){ return new Promise((res,rej)=>{ const id=++idc; pending.set(id,{res,rej}); ws.send(JSON.stringify({id,method:m,params:p})); }); }
const R = [];
function check(cond, msg){ R.push([!!cond, msg]); console.log((cond?'PASS':'FAIL'), '—', msg); }
try {
  let targets; for(let i=0;i<60;i++){ await sleep(300); try{ targets=await getJson('/json/list'); if(targets.length)break; }catch(e){} }
  const page = targets.find(t=>t.type==='page');
  ws = new WebSocket(page.webSocketDebuggerUrl);
  await new Promise((r,j)=>{ws.onopen=r;ws.onerror=j;});
  ws.onmessage=(ev)=>{ const m=JSON.parse(ev.data); if(m.id&&pending.has(m.id)){const{res,rej}=pending.get(m.id);pending.delete(m.id); m.error?rej(new Error(JSON.stringify(m.error))):res(m.result);} };
  await send('Page.enable'); await send('Emulation.setDeviceMetricsOverride',{width:1024,height:900,deviceScaleFactor:1,mobile:false});
  await send('Page.navigate',{url:'file://'+process.cwd()+'/index.html'});
  await sleep(1200);
  async function ev(e){ const r=await send('Runtime.evaluate',{expression:e,returnByValue:true,awaitPromise:true});
    if(r.exceptionDetails) console.log('EXC', JSON.stringify(r.exceptionDetails).slice(0,300)); return r.result && r.result.value; }
  const rect = (sel) => ev(`(() => { const el = document.querySelector('${sel}'); if(!el) return null; const r = el.getBoundingClientRect(); const cs = getComputedStyle(el); return { w: Math.round(r.width), h: Math.round(r.height), x: Math.round(r.left), y: Math.round(r.top), bg: cs.backgroundColor, color: cs.color, display: cs.display, visibility: cs.visibility }; })()`);
  // start screen
  const start = await rect('#startView');
  const startBtn = await rect('#btnStart');
  check(start && start.display !== 'none' && start.h > 100, 'start view visible, size ' + JSON.stringify(start && {w:start.w,h:start.h}));
  check(startBtn && startBtn.w > 50 && /rgba?\(/.test(startBtn.bg || ''), 'кнопка «Пройти тест DISC» видима: ' + JSON.stringify(startBtn));
  // progress to result
  await ev(`document.getElementById('btnStart').click(); true`);
  for (let i = 0; i < 7; i++) await ev(`document.querySelector('[data-disc-next]').click(); true`);
  await ev(`document.querySelector('[data-disc-finish]').click(); true`);
  await sleep(300);
  const title = await ev(`document.querySelector('.result__link-title').textContent`);
  const icon = await ev(`(() => { const el = document.querySelector('.copyfield__icon'); const r = el.getBoundingClientRect(); return { w: Math.round(r.width), h: Math.round(r.height), y: Math.round(r.top) }; })()`);
  const input = await rect('#discLink');
  const btn = await rect('.copyfield__btn');
  const btnIcon = await rect('.copyfield__btn .copyfield__btnIcon svg');
  check(title === 'Поделиться результатами теста:', 'заголовок «' + title + '»');
  check(icon && icon.w > 0, 'copyfield: иконка ссылки ' + JSON.stringify(icon));
  check(input && input.w > 100, 'copyfield: input ' + JSON.stringify(input && {w:input.w,h:input.h,y:input.y}));
  check(btn && btn.w > 60 && btn.h > 25, 'copyfield: кнопка ' + JSON.stringify(btn));
  check(btnIcon && btnIcon.w >= 20 && btnIcon.w <= 40, 'иконка документа в кнопке ' + JSON.stringify(btnIcon));
  if (icon && input && btn) {
    const dy = Math.max(icon.y, input.y, btn.y) - Math.min(icon.y, input.y, btn.y);
    check(dy <= 6, 'иконка/input/кнопка на одной линии (dy=' + dy + ')');
  }
  const btnLabel = await ev(`document.querySelector('.copyfield__btnText').textContent`);
  const inputVal = await ev(`document.getElementById('discLink').value`);
  check(btnLabel === 'Copy', 'кнопка по умолчанию: «' + btnLabel + '» (как в оригинале)');
  check(/^D:-?\d+, I:-?\d+, S:-?\d+, C:-?\d+$/.test(inputVal), 'input со значением: «' + inputVal + '»');
  const dark = btn && /rgb\((?:[0-3]\d?|[0-9])\s*,\s*(?:[0-3]\d?|[0-9])\s*,\s*(?:[0-3]\d?|[0-9])/.test(btn.bg);
  check(dark, 'кнопка тёмная (белая иконка читаема): ' + (btn && btn.bg));
  const score = await ev(`document.getElementById('discScore').textContent`);
  check(/^D:-?\d+, I:-?\d+, S:-?\d+, C:-?\d+$/.test(score), 'блок результата: «' + score + '»');
  const restart = await rect('#btnRestart');
  check(restart && restart.w > 50, '«Пройти ещё раз» видима: ' + JSON.stringify(restart));
  const note = await ev(`document.querySelector('.disc-note').textContent.length > 100`);
  check(note, 'дисклеймер присутствует полностью');
  console.log(R.every(r=>r[0]) ? 'GEOM: ALL PASS' : 'GEOM: FAILURES');
} finally { try { chrome.kill('SIGKILL'); } catch(e){} }
setTimeout(()=>process.exit(0), 9000);
