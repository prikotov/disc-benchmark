'use strict';
const http = require('http');
const { WebSocket } = require('ws');
const PORT = 9229, URL = 'file://' + __dirname + '/index.html';

function sleep(ms){ return new Promise(r=>setTimeout(r,ms)); }
function evalVal(r){
  const rr = (r && r.result) ? r.result : {};
  const inner = (rr && rr.result) ? rr.result : rr;
  return inner && inner.value;
}

function main(){
  let ws, nextId = 1;
  const state = { startPos: null };

  function call(method, params){
    return new Promise((res,reject)=>{
      const id = nextId++;
      const h = function onmsg(m){
        try{
          const raw = Buffer.isBuffer(m) ? m.toString('utf8') : (typeof m === 'string' ? m : JSON.stringify(m));
          const r = JSON.parse(raw);
          if (r && r.id === id){ res(r); ws.removeEventListener('message', h); }
        }catch(e){}
      };
      ws.on('message', h);
      ws.send(JSON.stringify({ id:id, method, params: params||{} }));
    });
  }
  function kill(code){ try{ if(ws) ws.close(); }catch(e){} process.exit(code || 0); }
  const fail = (msg) => { console.log('FAIL ' + msg); kill(1); };

  function launchChrome(){
    return new Promise((resolve)=>{
      require('child_process').spawn('google-chrome', [
        '--headless=new','--disable-gpu','--window-size=1280,900',
        '--remote-debugging-port='+PORT,
        '--no-sandbox','--disable-dev-shm-usage','--allow-file-access-from-files','--no-first-run','--lang=ru','--start-maximized', URL
      ], { stdio: ['ignore','ignore','inherit'] });
      let n = 0;
      (function poll(){
        n++;
        http.get('http://127.0.0.1:'+PORT+'/json',(r)=>{
          r.on('data', d => r.on('end', () => {
            try{
              const t = JSON.parse(d.toString());
              const page = t.find(x => x.type === 'page');
              if (page){ console.log('[1] wsUrl found'); resolve(page.webSocketDebuggerUrl); }
              else if (n < 15) setTimeout(poll, 400);
              else { console.log('no page'); resolve(); }
            }catch(e){ if (n < 15) setTimeout(poll, 400); else { console.log('poll fail'); resolve(); } }
          }));
        }).catch(() => { if (n < 15) setTimeout(poll, 400); else { console.log('poll fail'); resolve(); } });
      })();
    });
  }
  const ptr = (type,x,y,pressed) => call('Input.dispatchPointerEvent', {
    eventType: type, x, y, button:'Left', pressed, pointerType:'mouse', pointerId: 1
  });
  const stateProbe = (label) => call('Runtime.evaluate',{ expression:'!!window.__discDrag.state()', returnByValue:true })
    .then(r => { const a = evalVal(r); console.log(label, 'ACTIVE=' + a); return a; });
  const orderProbe = (label) => call('Runtime.evaluate',{
    expression:`(() => { const ul=document.querySelector('#draggable-list1'); if(!ul) return null; return Array.from(ul.children).map((el,i)=> i+':'+el.textContent.replace(/<[^>]*>/g,'').trim()); })()`,
    returnByValue:true
  }).then(r => { const o=evalVal(r); console.log(label, JSON.stringify(o)); return o; });
  const geomProbe = (label, idx) => call('Runtime.evaluate',{
    expression:`(() => { const ul=document.querySelector('#draggable-list1'); if(!ul) return null; const it=Array.from(ul.children)[${idx}]; if(!it) return null; const r=it.getBoundingClientRect(); return {x:Math.round(r.left+r.width/2), y:Math.round(r.top+r.height/2)}; })()`,
    returnByValue:true
  }).then(r => { const g=evalVal(r); console.log(label, JSON.stringify(g)); return g; });

  return launchChrome()
    .then(wsUrl => new Promise((resolve)=>{
      ws = new WebSocket(wsUrl);
      ws.on('open', () => { console.log('[2] ws open'); resolve(); });
      ws.on('error', e => { console.log('ws err', e.message); kill(2); });
    }))
    .then(() => call('Page.enable').then(()=>call('DOM.enable')).then(()=>call('Runtime.enable'))
      .then(() => new Promise(resolve => {
        let n = 0;
        (function poll(){
          n++;
          call('Runtime.evaluate',{expression:"document.querySelector('#draggable-list1')?1:0",returnByValue:true})
            .then(r => { if(evalVal(r)===1){ console.log('[3] ready'); resolve(); } else if(n<40) setTimeout(poll,300); else kill(2); })
            .catch(()=>{ if(n<40) setTimeout(poll,300); else kill(2); });
        })();
      }))
    )
    .then(() => {
      return call('Runtime.evaluate',{expression:'document.getElementById("btnStart").click()',returnByValue:true})
        .then(()=>sleep(300)).then(() => {
          return call('Runtime.evaluate',{expression:'document.getElementById("wizardmodal").classList.contains("is-open")',returnByValue:true}).then(r => {
            if(evalVal(r)!==true) fail('modal not open');
            console.log('[4] modal open');
          });
        });
    })
    .then(() => geomProbe('[5] item2', 2).then(g => { state.startPos = g; return g; }))
    .then(() => {
      console.log('[6] pointerdown at (' + state.startPos.x + ',' + state.startPos.y + ')');
      return ptr('pointerdown', state.startPos.x, state.startPos.y, true).then(()=>sleep(100));
    })
    .then(() => stateProbe('[7] after pointerdown'))
    .then(active => {
      if(!active){ fail('drag not started after pointerdown'); return; }
      console.log('[7] ok drag started');
      return ptr('pointermove', state.startPos.x, Math.round(state.startPos.y - 40), true).then(()=>sleep(100));
    })
    .then(() => Promise.all([stateProbe('[8] after move1'), orderProbe('[9] order after move1')]))
    .then(() => {
      return ptr('pointermove', state.startPos.x, Math.round(state.startPos.y - 90), true).then(()=>sleep(100));
    })
    .then(() => orderProbe('[10] order after move2'))
    .then(() => {
      console.log('[11] pointerup');
      return ptr('pointerup', state.startPos.x, Math.round(state.startPos.y - 90), false).then(()=>sleep(150));
    })
    .then(() => Promise.all([stateProbe('[12] after pointerup'), orderProbe('[13] FINAL order')]
      )
      .then(res => {
        const final = res[1];
        const moved = final && final[0].split(':')[1] === 'Волевой';
        console.log('[14] did Волевой move to index0? ' + String(moved));
        if (moved) { console.log('[15] PASS drag works'); kill(0); } else { console.log('[15] FAIL drag not moved'); kill(1); }
      })
    );
}
main().catch(e => { console.log('unhandled', e); process.exit(2); });
