const { WebSocket } = require('ws');
const { spawn } = require('child_process');
const http = require('http');

const PORT = 9229;
const pageFile = process.cwd() + '/index.html';

const chrome = spawn('google-chrome', [
  '--headless=new', '--no-sandbox', '--disable-gpu',
  '--remote-debugging-port=' + PORT, '--window-size=1400,900',
  '--allow-file-access-from-files', pageFile
], { stdio: 'ignore' });

function getJson() {
  return new Promise((res, rej) => {
    http.get('http://127.0.0.1:' + PORT + '/json', (r) => {
      let d = '';
      r.on('data', (c) => d += c);
      r.on('end', () => { res(JSON.parse(d)); });
    }).on('error', rej);
  });
}

function pollJson(maxTries) {
  return new Promise((res, rej) => {
    let t = 0;
    function tick(){
      getJson().then((targets) => {
        const page = targets.find((x) => x.type === 'page' && x.url && x.url.includes('index.html') && x.webSocketDebuggerUrl);
        if (page) return res(page);
        t++;
        if (t > 50) return rej(new Error('no page target after ' + t + ' tries'));
        setTimeout(tick, 400);
      }).catch(() => { t++; if (t > 50) return rej(new Error('poll fail')); setTimeout(tick, 400); });
    }
    tick();
  });
}

let ws = null;
function send(method, params, callback) {
  ws.send(JSON.stringify({ id: Math.random().toString(36).slice(2), method, params: params || {} }));
}
let nextId = 1;
function call(method, params) {
  return new Promise((res, rej) => {
    const id = nextId++;
    let done = false;
    const h = function onmsg(m) {
      try {
        const raw = Buffer.isBuffer(m) ? m.toString('utf8') : (typeof m === 'string' ? m : JSON.stringify(m));
        const r = JSON.parse(raw);
        if (r && r.id === id) {
          if (!done) { done = true; ws.removeEventListener('message', h); res(r); }
        }
      } catch (e) {}
    };
    ws.on('message', h);
    ws.send(JSON.stringify({ id: id, method, params: params || {} }));
    setTimeout(() => {
      try { ws.removeEventListener('message', h); } catch (e) {}
      if (!done) rej(new Error('timeout ' + method));
    }, 10000);
  });
}

// DevTools evaluate responses here nest the Value under r.result.result;
// tolerate both single and double nesting.
function evalVal(r) {
  const rr = (r && r.result) ? r.result : {};
  const inner = (rr && rr.result) ? rr.result : rr;
  return inner && inner.value;
}

function onReady() {
  console.log('[0] page ws ready; enabling Runtime + polling...');
  // page is already loaded (Chrome launched with the URL). Use call() for everything (unique ids, no fire-and-forget).
  return call('Runtime.enable', {}).then(() => {
    call('DOM.enable', {}).then(() => {
      console.log('[1] domains ready, polling for list1...');
      pollReady().then(() => run()).catch(err => { console.log(err.message); kill(); process.exit(2); });
    });
  }).catch(err => { console.log('enable err:', err.message); kill(); process.exit(2); });
}

function pollReady() {
  return new Promise((res, rej) => {
    let t = 0;
    function tick(){
      call('Runtime.evaluate', { expression: 'document.querySelector("#draggable-list1") ? document.querySelector("#draggable-list1").children.length : -1', returnByValue: true }).then((r) => {
        const n = evalVal(r);
        console.log('[poll] list1 children = ' + n);
        if (n === 4) { res(true); return; }
        t += 200;
        if (t > 6000) return rej(new Error('list1 not ready after ' + t + 'ms (children=' + n + ')'));
        setTimeout(tick, 200);
      }).catch(rej);
    }
    tick();
  });
}

function run() {
  return call('Runtime.evaluate', {
    expression: `(()=>{const ul=document.querySelector('#draggable-list1');if(!ul)return null;return Array.from(ul.children).map((el,i)=>{const r=el.getBoundingClientRect();return {i,x:Math.round(r.left+r.width/2),y:Math.round(r.top+r.height/2),type:el.dataset.type,text:el.textContent.replace(/<[^>]*>/g,'').trim()};})})()`,
    returnByValue: true
  }).then((r) => {
    const items = evalVal(r);
    if (!items || !items.length) { console.log('FAIL: no list1 items'); kill(); process.exit(2); }
    console.log('[2] list1 initial (idx:text:type):', JSON.stringify(items.map((i) => i.i + ':' + i.text)));

    // open modal
    return call('Runtime.evaluate', {
      expression: 'document.getElementById("btnStart").click()',
      returnByValue: true
    }).then(() => {
      // verify open
      return call('Runtime.evaluate', {
        expression: 'document.getElementById("wizardmodal").classList.contains("is-open")',
        returnByValue: true
      }).then((r) => {
        if (evalVal(r) !== true) { console.log('FAIL: modal not open: ' + JSON.stringify(evalVal(r))); kill(); process.exit(2); }
        console.log('[3] modal open=true');
        setTimeout(drag, 300);
        return Promise.resolve();
      });
    }).catch((e) => { console.log('ERR open modal', e.message); kill(); process.exit(2); });
  }).catch((e) => { console.log('ERR run', e.message); kill(); process.exit(2); });
}

function drag() {
  return call('Runtime.evaluate', {
    expression: `(()=>{const ul=document.querySelector('#draggable-list1');return Array.from(ul.children).map((el,i)=>{const r=el.getBoundingClientRect();return {i,x:Math.round(r.left+r.width/2),y:Math.round(r.top+r.height/2),type:el.dataset.type,text:el.textContent.replace(/<[^>]*>/g,'').trim()};})})()`,
    returnByValue: true
  }).then((r) => {
    const items = evalVal(r);
    if (!items || !items.length) { console.log('FAIL: geometry read failed'); kill(); process.exit(2); }
    const dragFrom = items[2];
    const targetTop = items[0];
    const startX = dragFrom.x, startY = dragFrom.y;
    const endY = targetTop.y;
    const xEnd = targetTop.x;
    const xMid = Math.round(startX - 6);
    const y1 = Math.round(startY - (startY - endY) * 0.4);
    const y2 = Math.round(startY - (startY - endY) * 0.7);
    const y3 = Math.round(startY - (startY - endY) * 0.9);
    console.log('[4] drag: start(' + startX + ',' + startY + ') -> mid(' + xMid + ',' + y1 + '),(' + xMid + ',' + y2 + '),(' + xMid + ',' + y3 + ')->end(' + xEnd + ',' + endY + ')  [item: ' + dragFrom.text + ']');

    const events = [
      { type: 'pointerdown', x: startX, y: startY, button: 'Left', pressed: true },
      { type: 'pointermove', x: xMid, y: y1, pressed: true },
      { type: 'pointermove', x: xMid, y: y2, pressed: true },
      { type: 'pointermove', x: xMid, y: y3, pressed: true },
      { type: 'pointermove', x: xEnd, y: endY, pressed: true },
      { type: 'pointerup', x: xEnd, y: endY, button: 'Left', pressed: false }
    ];
    return new Promise((resolve, reject) => {
      let i = 0;
      function next(){
        if (i >= events.length) { resolve(); return; }
        const e = events[i++];
        call('Input.dispatchPointerEvent', {
          eventType: e.type, x: e.x, y: e.y, button: e.button, pressed: e.pressed,
          pointerType: 'mouse', pointerId: 1
        }).catch(reject);
        setTimeout(next, 40);
      }
      next();
    }).then(() => {
      setTimeout(() => {
        return call('Runtime.evaluate', {
          expression: `(()=>{const ul=document.querySelector('#draggable-list1');return Array.from(ul.children).map((el,i)=>({i,text:el.textContent.replace(/<[^>]*>/g,'').trim(),type:el.dataset.type}));})()`,
          returnByValue: true
        }).then((r) => {
          const final = evalVal(r);
          console.log('[5] list1 FINAL order:', JSON.stringify(final.map((f) => f.i + ':' + f.text)));
          const dragText = dragFrom.text;
          const moved = final && final[0].text === dragText;
          console.log('[6] did ' + dragText + ' move to index0? ' + String(moved));
          console.log('[7] RESULT: ' + (moved ? 'PASS (drag reordering works)' : 'FAIL (drag did not reorder)'));
          kill();
          process.exit(moved ? 0 : 1);
        });
      }, 250);
    });
  }).catch((e) => { console.log('ERR drag', e.message); kill(); process.exit(2); });
}

function kill() {
  try { chrome.kill(); } catch (e) {}
}
process.on('exit', () => { try { chrome.kill(); } catch (e) {} });
process.on('unhandledRejection', (e) => { console.log('unhandledRejection', e.message); });

// main
console.log('[0] launching chrome...');
pollJson(50).then((page) => {
  console.log('[1] found page target wsUrl: ' + page.webSocketDebuggerUrl);
  ws = new WebSocket(page.webSocketDebuggerUrl);
  ws.on('open', () => { onReady(); });
  ws.on('error', (e) => { console.log('ws error', e.message); kill(); process.exit(4); });
  ws.on('close', () => { console.log('ws closed'); kill(); process.exit(3); });
}).catch((e) => { console.log('pollJson fail', e.message); kill(); process.exit(5); });