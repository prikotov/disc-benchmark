const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');
const os = require('os');

const PORT = 9333;
const userDir = fs.mkdtempSync(path.join(os.tmpdir(), 'disc-chrome-'));
const chrome = spawn('google-chrome', [
  '--headless=new', '--no-sandbox', '--disable-gpu', '--hide-scrollbars',
  '--disable-dev-shm-usage', '--no-first-run', '--no-default-browser-check',
  `--remote-debugging-port=${PORT}`, `--user-data-dir=${userDir}`,
  '--window-size=1440,1100', 'about:blank'
], { stdio: 'ignore' });

const sleep = (ms) => new Promise(r => setTimeout(r, ms));

async function waitForJson() {
  for (let i = 0; i < 100; i++) {
    try {
      const r = await fetch(`http://127.0.0.1:${PORT}/json`);
      if (r.ok) return await r.json();
    } catch {}
    await sleep(100);
  }
  throw new Error('chrome did not start');
}

(async () => {
  const targets = await waitForJson();
  const target = targets.find(t => t.type === 'page');
  const ws = new WebSocket(target.webSocketDebuggerUrl);
  const pending = new Map();
  const events = [];
  let seq = 0;
  await new Promise((resolve, reject) => {
    ws.onopen = resolve;
    ws.onerror = reject;
  });
  ws.onmessage = (ev) => {
    const msg = JSON.parse(ev.data);
    if (msg.id) {
      const p = pending.get(msg.id);
      if (p) {
        pending.delete(msg.id);
        if (msg.error) p.reject(new Error(JSON.stringify(msg.error)));
        else p.resolve(msg.result);
      }
    } else {
      events.push(msg);
    }
  };
  const send = (method, params = {}) => new Promise((resolve, reject) => {
    const id = ++seq;
    pending.set(id, { resolve, reject });
    ws.send(JSON.stringify({ id, method, params }));
  });
  const evaluate = async (expression) => {
    const res = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true, userGesture: true });
    if (res.exceptionDetails) throw new Error('Eval exception: ' + JSON.stringify(res.exceptionDetails));
    return res.result.value;
  };
  await send('Runtime.enable');
  await send('Page.enable');
  await send('Log.enable');
  const url = 'file://' + path.resolve('index.html');
  await send('Page.navigate', { url });
  await sleep(1200);

  const initial = await evaluate(`(() => {
    const r = (el) => { const b = el.getBoundingClientRect(); return {x:+b.x.toFixed(1),y:+b.y.toFixed(1),w:+b.width.toFixed(1),h:+b.height.toFixed(1)}; };
    const active = document.querySelector('.disc-pane.is-active');
    const shell = document.querySelector('.test-shell');
    const cards = [...active.querySelectorAll('.disc-card')].map(r);
    const list = active.querySelector('.disc-list');
    return {
      title: document.title,
      viewport: {w: innerWidth, h: innerHeight},
      doc: {scrollW: document.documentElement.scrollWidth, scrollH: document.documentElement.scrollHeight, bodyW: document.body.scrollWidth},
      shell: r(shell), cards,
      list: r(list),
      items: [...active.querySelectorAll('.disc-item')].slice(0,4).map(r),
      activePanes: document.querySelectorAll('.disc-pane.is-active').length,
      hiddenPanes: [...document.querySelectorAll('.disc-pane')].filter(p=>p.hidden).length,
      visibleItems: [...document.querySelectorAll('.disc-item')].filter(el => el.getBoundingClientRect().height > 0).length,
      progress: getComputedStyle(document.querySelector('#discProgress')).width,
      progressTrack: r(document.querySelector('#progress-track')),
      next: {hidden: document.querySelector('#next-btn').hidden, text: document.querySelector('#next-btn').innerText.trim()},
      finishHidden: document.querySelector('#finish-btn').hidden,
      tabFont: getComputedStyle(document.querySelector('.disc-tab')).fontSize,
      bodyBg: getComputedStyle(document.body).backgroundColor,
      fontFamily: getComputedStyle(document.body).fontFamily,
      cardTitleFont: getComputedStyle(document.querySelector('.test-title')).fontFamily,
      itemText: [...document.querySelectorAll('.disc-pane.is-active .disc-item__text')].map(x=>x.textContent)
    };
  })()`);
  console.log(JSON.stringify(initial, null, 2));

  const consoleEvents = events.filter(e => ['Runtime.exceptionThrown','Log.entryAdded','Runtime.consoleAPICalled'].includes(e.method));
  console.log('EVENTS', JSON.stringify(consoleEvents.map(e => ({method:e.method, params:e.params})), null, 2));

  ws.close();
  chrome.kill('SIGKILL');
})().catch(err => {
  console.error(err);
  chrome.kill('SIGKILL');
  process.exit(1);
});
