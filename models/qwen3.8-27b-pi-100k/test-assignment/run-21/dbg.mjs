import { spawn } from 'node:child_process';
import { setTimeout as sleep } from 'node:timers/promises';
import fs from 'node:fs';
const PORT = 9342;
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
    if(r.exceptionDetails) console.log('EXC:', JSON.stringify(r.exceptionDetails).slice(0,500));
    return r.result && r.result.value; }
  console.log('btnStart listener? clicking...');
  console.log('after start click, testView hidden =', await ev(`document.getElementById('testView').hidden`));
  console.log('next btn exists =', await ev(`!!document.querySelector('[data-disc-next]')`));
  // attach a probe listener to see if click event even reaches
  await ev(`window.__probe=[]; document.querySelector('[data-disc-next]').addEventListener('click', function(){ window.__probe.push('next-click-fired'); }); 'ok'`);
  await ev(`document.querySelector('[data-disc-next]').click(); 'clicked'`);
  console.log('probe =', await ev(`JSON.stringify(window.__probe)`));
  console.log('active pane =', await ev(`document.querySelector('.disc-pane.is-active') ? document.querySelector('.disc-pane.is-active').id : 'NONE'`));
  // check the app's step by progress width
  console.log('progress width =', await ev(`document.getElementById('discProgress').style.width`));
  console.log('prev disabled =', await ev(`document.querySelector('[data-disc-prev]').disabled`));
  // any page errors
  for (const e of events) if (e.method==='Runtime.exceptionThrown' || (e.method==='Runtime.consoleAPICalled'&&e.params.type==='error')) console.log('PAGE ERROR:', JSON.stringify(e.params).slice(0,400));
  // inspect window.onerror capture: list all events
  const errEvents = events.filter(e=>['Runtime.exceptionThrown','Runtime.consoleAPICalled','Log.entryAdded'].includes(e.method));
  console.log('error-ish events:', errEvents.length);
  for (const e of errEvents) console.log(' ', JSON.stringify(e.params).slice(0,300));
} finally { chrome.kill('SIGKILL'); }
