// CDP-драйвер: автопрохождение index.html с реальными mouse-событиями (pointer drag)
const { spawn } = require('child_process');
const fs = require('fs');

const CHROME = '/usr/bin/google-chrome';
const URL = process.argv[2] || 'file://' + process.cwd() + '/index.html';

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

async function main() {
  const port = 9333 + Math.floor(Math.random() * 100);
  const userDataDir = fs.mkdtempSync('/tmp/cdp-disc-');
  const chrome = spawn(CHROME, [
    '--headless=new', '--no-sandbox', '--disable-gpu', '--force-device-scale-factor=1',
    `--remote-debugging-port=${port}`, `--user-data-dir=${userDataDir}`,
    '--window-size=1280,900', 'about:blank'
  ], { stdio: 'ignore' });

  // подождать target
  let target = null;
  for (let i = 0; i < 50 && !target; i++) {
    await sleep(200);
    try {
      const r = await fetch(`http://127.0.0.1:${port}/json`);
      const list = await r.json();
      target = list.find(t => t.type === 'page');
    } catch (_) {}
  }
  if (!target) { chrome.kill(); throw new Error('no chrome target'); }

  const ws = new WebSocket(target.webSocketDebuggerUrl);
  let id = 0;
  const pending = new Map();
  const send = (method, params = {}) => new Promise((res, rej) => {
    const mid = ++id;
    pending.set(mid, { res, rej });
    ws.send(JSON.stringify({ id: mid, method, params }));
  });
  ws.onmessage = (m) => {
    const msg = JSON.parse(m.data);
    if (msg.id && pending.has(msg.id)) {
      const { res, rej } = pending.get(msg.id);
      pending.delete(msg.id);
      msg.error ? rej(new Error(JSON.stringify(msg.error))) : res(msg.result);
    }
  };
  await new Promise(r => ws.onopen = r);

  await send('Runtime.enable');
  await send('Page.enable');
  try { await send('Emulation.setDeviceMetricsOverride', { width: 1280, height: 1400, deviceScaleFactor: 1, mobile: false }); } catch (_) {}

  const evalJs = async (expr) => {
    const r = await send('Runtime.evaluate', { expression: expr, returnByValue: true });
    if (r.exceptionDetails) throw new Error('page error: ' + JSON.stringify(r.exceptionDetails) + ' || expr: ' + expr.slice(0,100).replace(/\n/g,'\\n'));
    return r.result.value;
  };

  // навигация
  await send('Page.navigate', { url: URL });
  await sleep(800);

  const clickCenter = async (sel) => {
    const r = await evalJs(`(() => {
      const el = document.querySelector(${JSON.stringify(sel)});
      if (!el) return null;
      const b = el.getBoundingClientRect();
      return { x: b.left + b.width/2, y: b.top + b.height/2 };
    })()`);
    if (!r) throw new Error('selector not found: ' + sel);
    await mouse(r.x, r.y, 'down');
    await mouse(r.x, r.y, 'up');
  };
  const mouse = async (x, y, action, steps = 1, pressed = false) => {
    if (action === 'down') await send('Input.dispatchMouseEvent', { type: 'mousePressed', x, y, button: 'left', clickCount: 1 });
    else if (action === 'up') await send('Input.dispatchMouseEvent', { type: 'mouseReleased', x, y, button: 'left', clickCount: 1 });
    else if (action === 'move') await send('Input.dispatchMouseEvent', { type: 'mouseMoved', x, y, button: pressed ? 'left' : 'none' });
    else throw new Error('unknown mouse action: ' + action);
  };

  const rect = async (sel) => evalJs(`(() => {
    const el = document.querySelector(${JSON.stringify(sel)});
    if (!el) return null;
    const b = el.getBoundingClientRect();
    return { l: b.left, t: b.top, r: b.right, b: b.bottom, w: b.width, h: b.height };
  })()`);

  const order = async (sel) => evalJs(`Array.from(document.querySelectorAll(${JSON.stringify(sel + ' .list > li')})).map(li => li.querySelector('.text').textContent)`);
  const visibleList = async () => evalJs(`(() => {
    const lists = Array.from(document.querySelectorAll('.card .list')).filter(l => l.offsetParent !== null);
    return lists.map((ul, idx) => Array.from(ul.children).map(li => li.querySelector('.text').textContent));
  })()`);

  // === Тест 1: без перетаскиваний — дефолтный порядок ===
  // пройти 7 раз "Далее"
  const btnNextSel = '#btnNext';
  for (let s = 1; s <= 7; s++) {
    await clickCenter(btnNextSel);
    await sleep(120);
  }
  const stepLabel = await evalJs(`document.querySelector('#stepCaption').textContent`);
  console.log('Тест 1 шаг:', stepLabel);

  await clickCenter('#btnFinish');
  await sleep(200);
  let chips = await evalJs(`Array.from(document.querySelectorAll('#chips .chip')).map(c => ({L: c.querySelector('.letter').textContent, V: +c.querySelector('.val').textContent}))`);
  let score = {}; chips.forEach(c => score[c.L] = c.V);
  console.log('Тест 1 (без drag) score:', JSON.stringify(score), 'expected D-1 I0 S-3 C4 ->',
    score.D === -1 && score.I === 0 && score.S === -3 && score.C === 4 ? 'PASS' : 'FAIL');

  const textFmt = await evalJs(`(() => {
    const ch = Array.from(document.querySelectorAll('#chips .chip'));
    const get = L => +ch.find(c => c.querySelector('.letter').textContent === L).querySelector('.val').textContent;
    return 'D:' + get('D') + ', I:' + get('I') + ', S:' + get('S') + ', C:' + get('C');
  })()`);
  console.log('Тест 1 формат:', textFmt);

  // === Тест 2: заново, перетащить в первой карте первый элемент вниз (двойной обмен) ===
  await clickCenter('#btnRestart');
  await sleep(200);

  // позиции li в первой видимой карте
  const items = await evalJs(`(() => {
    const ul = Array.from(document.querySelectorAll('.card .list')).find(l => l.offsetParent !== null);
    return Array.from(ul.children).map(li => { const b = li.getBoundingClientRect();
      return { text: li.querySelector('.text').textContent, x: b.left + b.width/2, top: b.top, h: b.height }; });
  })()`);
  console.log('Тест 2 исходный порядок карты 1:', items.map(i => i.text).join(' | '));

  // drag li[0] к позиции li[3] (центр)
  const from = items[0], to = items[3];
  await mouse(from.x + 40, from.top + from.h/2, 'move'); await sleep(120); // hover warmup
  await mouse(from.x, from.top + from.h/2, 'down');
  const steps = 12;
  for (let i = 1; i <= steps; i++) {
    const y = from.top + from.h/2 + (to.top - from.top - from.h/2) * (i / steps);
    await mouse(from.x, y, 'move', 1, true); // move со сжатым левым — иначе headless не шлёт pointermove
    await sleep(15);
  }
  await mouse(from.x, to.top + to.h, 'move', 1, true);
  await mouse(from.x, to.top + to.h, 'move', 1, true); await sleep(80);
  await mouse(from.x, to.top + to.h, 'move', 1, true); // extra нажатия в конце: headless может сбросить последний move
  await sleep(120);
  await mouse(from.x, to.top + to.h, 'up'); // ниже середины последнего: элемент встаёт на 4-ю позицию
  await sleep(300);

  const after = await evalJs(`(() => {
    const ul = Array.from(document.querySelectorAll('.card .list')).find(l => l.offsetParent !== null);
    return Array.from(ul.children).map(li => li.querySelector('.text').textContent);
  })()`);
  console.log('Тест 2 после drag:', after.join(' | '));
  const t0 = items[0].text;
  console.log('Тест 2 (drag вниз):', after[3] === t0 && after[0] === items[1].text ? 'PASS (первый ушёл вниз)' : 'FAIL',
    'transform чист?', await evalJs(`Array.from(document.querySelectorAll('.list li')).every(li => !li.style.transform || li.style.transform === 'none')`));

  // довести до результата
  for (let s = 1; s <= 7; s++) { await clickCenter(btnNextSel); await sleep(100); }
  await clickCenter('#btnFinish');
  await sleep(200);
  chips = await evalJs(`Array.from(document.querySelectorAll('#chips .chip')).map(c => +c.querySelector('.val').textContent)`);
  const dDelta = 0;
  // карта 1: i,c,d,s → top i(+1) bottom s(−1). Drag i вниз → c,d,s,i → top c(+1) bottom i(−1).
  // I: +1→−1 (Δ−2) =−2; S: −1→0 (Δ+1) =−2; C: 0→+1 =+5; D не меняет =−1
  // Итог [D,I,S,C] = [-1,-2,-2,5]
  console.log('Тест 2 score после одного drag:', JSON.stringify(chips), '(ожидаемо [D,I,S,C]=[-1,-2,-2,5])',
    JSON.stringify(chips) === JSON.stringify([-1, -2, -2, 5]) ? 'PASS' : 'FAIL (ожидался [-1,-2,-2,5])');

  // === Тест 3: обратный drag (последний вверх) ===
  await clickCenter('#btnRestart');
  await sleep(200);
  const items3 = await evalJs(`(() => {
    const ul = Array.from(document.querySelectorAll('.card .list')).find(l => l.offsetParent !== null);
    return Array.from(ul.children).map(li => { const b = li.getBoundingClientRect();
      return { text: li.querySelector('.text').textContent, x: b.left + b.width/2, top: b.top, h: b.height }; });
  })()`);
  const from3 = items3[3], to3 = items3[0];
  await mouse(from3.x + 40, from3.top + from3.h/2, 'move'); await sleep(120);
  await mouse(from3.x, from3.top + from3.h/2, 'down');
  for (let i = 1; i <= 12; i++) {
    const y = from3.top + from3.h/2 + (to3.top - from3.top - from3.h/2) * (i / 12);
    await mouse(from3.x, y, 'move', 1, true); // move со сжатым левым — иначе headless не шлёт pointermove
    await sleep(15);
  }
  await mouse(from3.x, to3.top, 'move', 1, true);
  await mouse(from3.x, to3.top, 'move', 1, true); await sleep(80);
  await mouse(from3.x, to3.top, 'move', 1, true); // extra нажатия в конце
  await sleep(120);
  await mouse(from3.x, to3.top, 'up');
  await sleep(300);
  const after3 = await evalJs(`(() => {
    const ul = Array.from(document.querySelectorAll('.card .list')).find(l => l.offsetParent !== null);
    return Array.from(ul.children).map(li => li.querySelector('.text').textContent);
  })()`);
  console.log('Тест 3 после drag вверх:', after3.join(' | '));
  const last = items3[3].text;
  console.log('Тест 3 (drag вверх):', after3[0] === last ? 'PASS (последний поднялся)' : 'FAIL');

  // скриншот на каждом экране для отчёта
  await clickCenter('#btnRestart');
  await sleep(200);
  const shot = async (name) => {
    const r = await send('Page.captureScreenshot', { format: 'png' });
    fs.writeFileSync(name, Buffer.from(r.data, 'base64'));
  };
  await shot('shot-step1.png');
  for (let s = 1; s <= 7; s++) { await clickCenter(btnNextSel); await sleep(100); }
  await shot('shot-step8.png');
  await clickCenter('#btnFinish');
  await sleep(300);
  await shot('shot-result.png');
  console.log('снимки сохранены');

  ws.close();
  chrome.kill();
  console.log('DONE');
  process.exit(0);
}

main().catch(e => { console.error('ERROR:', e.message || e); process.exit(1); });
