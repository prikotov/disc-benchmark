const { WebSocket } = require('ws');
const { spawn } = require('child_process');
const http = require('http');

const PORT = 9232;
const pageFile = process.cwd() + '/index.html';
const chrome = spawn('google-chrome', [
  '--headless=new', '--no-sandbox', '--disable-gpu',
  '--remote-debugging-port=' + PORT, '--window-size=1400,900',
  '--allow-file-access-from-files', pageFile
], { stdio: 'ignore' });

function getJson() {
  return new Promise((res, rej) => {
    http.get('http://127.0.0.1:' + PORT + '/json', (r) => {
      let d = ''; r.on('data', c => d += c); r.on('end', () => res(JSON.parse(d)));
    }).on('error', rej);
  });
}
function pollJson() {
  return new Promise((res, rej) => {
    let t = 0;
    (function tick() {
      getJson().then((targets) => {
        const page = targets.find(x => x.type === 'page' && x.url && x.url.includes('index.html'));
        if (page) return res(page);
        t++;
        if (t > 40) return rej(new Error('no page'));
        setTimeout(tick, 400);
      }).catch(() => { t++; if (t > 40) return rej(new Error('poll fail')); setTimeout(tick, 400); });
    })();
  });
}

let ws;
let idCounter = 0;
function call(method, params) {
  return new Promise((res, rej) => {
    const id = ++idCounter;
    let done = false;
    const h = ws.on('message', (m) => {
      try {
        const r = JSON.parse(m.toString());
        if (r && r.id === id) {
          if (!done) { done = true; ws.removeEventListener('message', h); res(r); }
        }
      } catch (e) {}
    });
    ws.send(JSON.stringify({ id, method, params: params || {} }));
    setTimeout(() => {
      try { ws.removeEventListener('message', h); } catch (e) {}
      if (!done) rej(new Error('timeout ' + method));
    }, 5000);
  });
}

pollJson().then((page) => {
  ws = new WebSocket(page.webSocketDebuggerUrl);
  ws.on('open', async () => {
    console.log('ws open, sending enables + navigate (fire and forget)...');
    ws.send(JSON.stringify({ id: 999, method: 'Page.enable', params: {} }));
    ws.send(JSON.stringify({ id: 999, method: 'DOM.enable', params: {} }));
    ws.send(JSON.stringify({ id: 999, method: 'Runtime.enable', params: {} }));
    ws.send(JSON.stringify({ id: 999, method: 'Page.navigate', params: { url: pageFile } }));
    console.log('waiting 2500ms for load...');
    await new Promise(r => setTimeout(r, 2500));
    // diagnostics
    const diag = [
      { label: 'title', expr: 'document.title' },
      { label: 'readyState', expr: 'document.readyState' },
      { label: 'modalEl', expr: 'document.getElementById("wizardmodal") ? "y" : "n"' },
      { label: 'modalClass', expr: 'document.getElementById("wizardmodal") ? document.getElementById("wizardmodal").className : "N/A"' },
      { label: 'list1Exists', expr: 'document.querySelector("#draggable-list1") ? "y" : "n"' },
      { label: 'list1Children', expr: 'document.querySelector("#draggable-list1") ? document.querySelector("#draggable-list1").children.length : -1' },
      { label: 'list1Items', expr: "document.querySelector('#draggable-list1') ? Array.from(document.querySelector('#draggable-list1').children).map(e=>({type:e.dataset.type,text:e.textContent.replace(/<[^>]*>/g,'').trim()})) : -1" },
    ];
    const results = {};
    for (const d of diag) {
      results[d.label] = await call('Runtime.evaluate', { expression: d.expr, returnByValue: true });
    }
    for (const k of Object.keys(results)) {
      const r = results[k];
      console.log(k + ':', JSON.stringify(r.result));
    }
    chrome.kill();
    process.exit(0);
  });
  ws.on('error', e => { console.log('ws error', e.message); chrome.kill(); process.exit(1); });
  ws.on('close', () => { console.log('ws closed'); chrome.kill(); process.exit(2); });
}).catch((e) => { console.log('poll fail', e.message); chrome.kill(); process.exit(3); });