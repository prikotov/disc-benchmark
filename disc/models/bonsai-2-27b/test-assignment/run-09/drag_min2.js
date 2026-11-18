const { WebSocket } = require('ws');
const { spawn } = require('child_process');
const http = require('http');

const PORT = 9237;
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

let ws, nextId = 1, msgCount = 0;
function call(method, params) {
  return new Promise((res, rej) => {
    const id = nextId++;
    const h = function onmsg(m) {
      msgCount++;
      const raw = m.toString();
      console.log('[MSG#' + msgCount + ']', raw.slice(0, 150));
      try {
        const r = JSON.parse(raw);
        if (r && r.id === id) {
          console.log('[call] id=' + id + ' MATCHED result=', JSON.stringify(r.result || r).slice(0,120));
          res(r);
        }
      } catch (e) {}
    };
    ws.addEventListener('message', h);
    console.log('[call] sending id=' + id + ' method=' + method);
    ws.send(JSON.stringify({ id, method, params: params || {} }));
    setTimeout(() => {
      ws.removeEventListener('message', h);
      console.log('[call] id=' + id + ' TIMEOUT (msgs seen so far: ' + msgCount + ')');
      rej(new Error('timeout ' + method));
    }, 6000);
  });
}

pollJson().then((page) => {
  ws = new WebSocket(page.webSocketDebuggerUrl);
  ws.on('open', () => {
    console.log('ws open, sending Runtime.enable...');
    // add a listener to see ALL messages before the call
    ws.addEventListener('message', (m) => { console.log('[ALLMSG]', m.toString().slice(0,150)); });
    setTimeout(() => {
      ws.removeAllListeners('message');
      console.log('re-listening via call...');
      call('Runtime.enable', {}).then(() => {
        console.log('--- Runtime.enable resolved ---');
      }).catch((e) => {
        console.log('--- ERROR: ' + e.message);
        chrome.kill();
        process.exit(1);
      });
    }, 1200);
  });
  ws.on('error', e => { console.log('ws error', e.message); chrome.kill(); process.exit(2); });
  ws.on('close', () => { console.log('ws closed'); chrome.kill(); process.exit(3); });
}).catch((e) => { console.log('poll fail', e.message); chrome.kill(); process.exit(4); });