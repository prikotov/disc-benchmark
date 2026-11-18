// Смоук + автопрохождение копии DISC через CDP (headless Chrome, без библиотек)
// Использование: node smoke.mjs /abs/path/to/index.html [outdir]
import { spawn } from 'node:child_process';
import { mkdtempSync, mkdirSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, dirname } from 'node:path';
import { setTimeout as sleep } from 'node:timers/promises';

import { resolve as pathResolve } from 'node:path';

const file = process.argv[2] ? pathResolve(process.argv[2]) : null;
const outdir = process.argv[3] || '.';
mkdirSync(outdir, { recursive: true });

if (!file) { console.error('usage: node smoke.mjs index.html [outdir]'); process.exit(2); }

const PORT = 9777 + Math.floor(Math.random() * 200);
const profile = mkdtempSync(join(tmpdir(), 'disc-smoke-'));

const chrome = spawn('google-chrome', [
  '--headless=new', '--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage',
  `--remote-debugging-port=${PORT}`, `--user-data-dir=${profile}`,
  '--window-size=1440,1000', 'about:blank',
], { stdio: ['ignore', 'pipe', 'pipe'] });

const log = [];
const say = (...a) => { const s = a.join(' '); log.push(s); console.log(s); };
let failed = false;
const check = (name, cond, extra = '') => {
  say(`${cond ? 'PASS' : 'FAIL'}  ${name}${extra ? '  [' + extra + ']' : ''}`);
  if (!cond) failed = true;
};

// --- CDP mini client ---
class CDP {
  static async connect() {
    for (let i = 0; i < 50; i++) {
      try {
        const res = await fetch(`http://127.0.0.1:${PORT}/json/list`);
        const tabs = await res.json();
        const page = tabs.find(t => t.type === 'page');
        if (page) return new CDP(page.webSocketDebuggerUrl);
      } catch (_) {}
      await sleep(200);
    }
    throw new Error('chrome not reachable');
  }
  constructor(url) { this.url = url; this.id = 0; this.pending = new Map(); this.handlers = []; }
  async open() {
    this.ws = new WebSocket(this.url);
    await new Promise((res, rej) => { this.ws.onopen = res; this.ws.onerror = rej; });
    this.ws.onmessage = (ev) => {
      const msg = JSON.parse(ev.data);
      if (msg.id && this.pending.has(msg.id)) {
        const { res, rej } = this.pending.get(msg.id);
        this.pending.delete(msg.id);
        msg.error ? rej(new Error(JSON.stringify(msg.error))) : res(msg.result);
      } else if (msg.method) {
        this.handlers.forEach(h => h(msg));
      }
    };
  }
  send(method, params = {}) {
    const id = ++this.id;
    this.ws.send(JSON.stringify({ id, method, params }));
    return new Promise((res, rej) => this.pending.set(id, { res, rej }));
  }
  on(fn) { this.handlers.push(fn); }
}

// Runtime.evaluate helper: returns JSON value
async function ev(cdp, expr) {
  const r = await cdp.send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true });
  if (r.exceptionDetails) throw new Error('page exception: ' + JSON.stringify(r.exceptionDetails));
  return r.result.value;
}

const consoleErrors = [];
const netRequests = [];

try {
  const cdp = await CDP.connect();
  await cdp.open();
  cdp.on((msg) => {
    if (msg.method === 'Runtime.exceptionThrown')
      consoleErrors.push(msg.params.exceptionDetails?.exception?.description || 'exception');
    if (msg.method === 'Log.entryAdded' && msg.params.entry.level === 'error' && !/net::ERR_|favicon/.test(msg.params.entry.text))
      consoleErrors.push(msg.params.entry.text);
    if (msg.method === 'Network.requestWillBeSent' && /^https?:/i.test(msg.params.request.url))
      netRequests.push(msg.params.request.url);
  });
  await cdp.send('Runtime.enable');
  await cdp.send('Log.enable');
  await cdp.send('Page.enable');
  await cdp.send('Network.enable');
  await cdp.send('Emulation.setDeviceMetricsOverride', { width: 1440, height: 1000, deviceScaleFactor: 1, mobile: false });

  await cdp.send('Page.navigate', { url: 'file://' + file });
  await sleep(700);

  // 1) рендер лендинга
  const land = await ev(cdp, `({
    title: document.title,
    h1: !!document.querySelector('h1'),
    openBtns: document.querySelectorAll('.js-open-disc').length,
    externalImgs: [...document.images].length
  })`);
  check('landing rendered, h1 present', land.h1);
  check('test open buttons on landing', land.openBtns >= 2, 'btns=' + land.openBtns);
  check('no <img> elements (raster-free)', land.externalImgs === 0);

  // 2) открыть модалку
  await ev(cdp, `document.querySelector('.js-open-disc').click()`);
  await sleep(300);
  const wiz = await ev(cdp, `({
    open: document.querySelector('#wizardmodal').classList.contains('is-open'),
    panes: document.querySelectorAll('#rootwizard .disc-pane').length,
    lists: document.querySelectorAll('#rootwizard .disc-list').length,
    items: document.querySelectorAll('#rootwizard .disc-item').length,
    tabs: document.querySelectorAll('#discTabs .disc-tab').length,
    nextVisible: !document.querySelector('[data-disc-next]').hidden,
    finishHidden: document.querySelector('[data-disc-finish]').hidden,
    prevDisabled: document.querySelector('[data-disc-prev]').disabled,
    progress: document.querySelector('#discProgress').style.width,
    scrollLocked: document.documentElement.classList.contains('no-scroll')
  })`);
  check('wizard opened', wiz.open);
  check('8 panes / 24 lists / 96 items / 8 tabs', wiz.panes === 8 && wiz.lists === 24 && wiz.items === 96 && wiz.tabs === 8,
    `${wiz.panes}/${wiz.lists}/${wiz.items}/${wiz.tabs}`);
  check('step0: prev disabled, finish hidden, progress 12.5%', wiz.prevDisabled && wiz.finishHidden && wiz.progress === '12.5%',
    wiz.progress);
  check('scroll locked while modal open', wiz.scrollLocked);

  // скриншот старта
  const shot1 = await cdp.send('Page.captureScreenshot', { format: 'png' });
  writeFileSync(join(outdir, 'shot-start.png'), Buffer.from(shot1.data, 'base64'));

  // 3) реальный drag&drop: перетащить 2-й элемент 1-го списка на 1-ю позицию (мышь)
  const rect1 = await ev(cdp, `(() => {
    const li = document.querySelector('#draggable-list1 li:nth-child(2)');
    const r = li.getBoundingClientRect();
    return { x: r.left + r.width / 2, y: r.top + r.height / 2, word: li.textContent };
  })()`);
  say(`drag "${rect1.word}" to top of list1`);
  const step = 8;
  await cdp.send('Input.dispatchMouseEvent', { type: 'mouseMoved', x: rect1.x, y: rect1.y });
  await cdp.send('Input.dispatchMouseEvent', { type: 'mousePressed', x: rect1.x, y: rect1.y, button: 'left', clickCount: 1, pointerType: 'mouse' });
  await sleep(60);
  for (let i = 1; i <= step; i++) {
    const y = rect1.y - ((rect1.y - (rect1.y - 190)) * (i / step));
    await cdp.send('Input.dispatchMouseEvent', { type: 'mouseMoved', x: rect1.x, y: rect1.y - (190 * i / step) });
    await sleep(25);
  }
  await sleep(80);
  await cdp.send('Input.dispatchMouseEvent', { type: 'mouseReleased', x: rect1.x, y: rect1.y - 190, button: 'left', clickCount: 1, pointerType: 'mouse' });
  await sleep(150);

  const afterDrag = await ev(cdp, `(() => {
    const lis = [...document.querySelectorAll('#draggable-list1 li')].map(li => li.textContent);
    const ghosts = document.querySelectorAll('.disc-ghost').length;
    const dragging = document.querySelectorAll('.disc-item.is-dragging').length;
    return { lis, ghosts, dragging };
  })()`);
  check('drag&drop reordered list', afterDrag.lis[0] === rect1.word, afterDrag.lis.join(' | '));
  check('no leftover ghost/dragging state', afterDrag.ghosts === 0 && afterDrag.dragging === 0);

  // скриншот шага
  const shot2 = await cdp.send('Page.captureScreenshot', { format: 'png' });
  writeFileSync(join(outdir, 'shot-step.png'), Buffer.from(shot2.data, 'base64'));

  // 4) навигация по шагам: таб на шаг 7, назад на 6, потом вперёд до конца
  await ev(cdp, `[...document.querySelectorAll('.disc-tab')][7].click()`);
  await sleep(120);
  const step7 = await ev(cdp, `({
    activePane: document.querySelector('.disc-pane.is-active').dataset.stepPane,
    nextHidden: document.querySelector('[data-disc-next]').hidden,
    finishVisible: !document.querySelector('[data-disc-finish]').hidden,
    progress: document.querySelector('#discProgress').style.width
  })`);
  check('tab jump to step7', step7.activePane === '7' && step7.nextHidden && step7.finishVisible && step7.progress === '100%', step7.progress);
  await ev(cdp, `document.querySelector('[data-disc-prev]').click()`);
  await sleep(120);
  const step6 = await ev(cdp, `document.querySelector('.disc-pane.is-active').dataset.stepPane`);
  check('prev to step6', step6 === '6');

  // 5) пройти до конца: с шага 6 — Далее до 7, затем Завершить
  await ev(cdp, `document.querySelector('[data-disc-next]').click()`);
  await sleep(120);
  await ev(cdp, `document.querySelector('[data-disc-finish]').click()`);
  await sleep(300);

  const result = await ev(cdp, `(() => {
    const res = { d:0,i:0,s:0,c:0 };
    document.querySelectorAll('#rootwizard .disc-list').forEach(ul => {
      const lis = [...ul.querySelectorAll('li')];
      res[lis[0].dataset.type]++; res[lis[3].dataset.type]--;
    });
    return {
      shown: document.querySelector('#discScoreLine').textContent,
      expected: 'D:' + res.d + ', I:' + res.i + ', S:' + res.s + ', C:' + res.c,
      res,
      cells: ['valD','valI','valS','valC'].map(id => document.getElementById(id).textContent),
      resultOpen: document.querySelector('#resultmodal').classList.contains('is-open'),
      wizardClosed: !document.querySelector('#wizardmodal').classList.contains('is-open'),
      scrollLocked: document.documentElement.classList.contains('no-scroll')
    };
  })()`);
  check('result modal opened, wizard closed', result.resultOpen && result.wizardClosed);
  check('score line matches DOM-derived expectation', result.shown === result.expected, `${result.shown} vs ${result.expected}`);
  check('per-type cells match', ['valD','valI','valS','valC'].every((id, idx) => {
    const k = 'disc'[idx] === undefined ? null : ['d','i','s','c'][idx];
    return true;
  }) && result.cells.map(Number).join(',') === [result.res.d, result.res.i, result.res.s, result.res.c].join(','),
    result.cells.join('/'));

  // скриншот результата
  const shot3 = await cdp.send('Page.captureScreenshot', { format: 'png' });
  writeFileSync(join(outdir, 'shot-result.png'), Buffer.from(shot3.data, 'base64'));

  // 6) ещё раз: рестарт возвращает шаг 0 и исходный порядок
  await ev(cdp, `document.querySelector('#discRestart').click()`);
  await sleep(250);
  const re = await ev(cdp, `({
    wizardOpen: document.querySelector('#wizardmodal').classList.contains('is-open'),
    resultClosed: !document.querySelector('#resultmodal').classList.contains('is-open'),
    step0: document.querySelector('.disc-pane.is-active').dataset.stepPane,
    firstItem: document.querySelector('#draggable-list1 li').textContent,
    progress: document.querySelector('#discProgress').style.width
  })`);
  check('restart: wizard reopened at step 0 with initial order', re.wizardOpen && re.resultClosed && re.step0 === '0' && re.firstItem === 'Экспресcивный', re.firstItem);

  // 7) Esc закрывает
  await cdp.send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'Escape', code: 'Escape', windowsVirtualKeyCode: 27 });
  await cdp.send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'Escape', code: 'Escape', windowsVirtualKeyCode: 27 });
  await sleep(150);
  const escClosed = await ev(cdp, `!document.querySelector('#wizardmodal').classList.contains('is-open') && !document.documentElement.classList.contains('no-scroll')`);
  check('Escape closes wizard and unlocks scroll', escClosed);

  // ============ фаза 2: сенсорный режим (pointer: coarse) ============
  await cdp.send('Emulation.setTouchEmulationEnabled', { enabled: true, maxTouchPoints: 5 });
  await cdp.send('Page.navigate', { url: 'file://' + file });
  await sleep(700);
  await ev(cdp, `document.querySelector('.js-open-disc').click()`);
  await sleep(250);
  const coarse = await ev(cdp, `matchMedia('(pointer: coarse)').matches`);
  check('touch emulation: pointer: coarse is active', coarse === true);

  // 8a) тап по центру элемента НЕ перетаскивает (жест = скролл)
  const beforeA = await ev(cdp, `[...document.querySelectorAll('#draggable-list1 li')].map(l=>l.textContent).join('|')`);
  const t1 = await ev(cdp, `(() => { const li = document.querySelector('#draggable-list1 li:nth-child(2)'); const r = li.getBoundingClientRect(); return { x: r.left + r.width/2, y: r.top + r.height/2 }; })()`);
  await cdp.send('Input.dispatchMouseEvent', { type: 'mousePressed', x: t1.x, y: t1.y, button: 'left', clickCount: 1, pointerType: 'touch' });
  await sleep(60);
  for (let i = 1; i <= 6; i++) { await cdp.send('Input.dispatchMouseEvent', { type: 'mouseMoved', x: t1.x, y: t1.y - 120*i/6, pointerType: 'touch' }); await sleep(30); }
  await cdp.send('Input.dispatchMouseEvent', { type: 'mouseReleased', x: t1.x, y: t1.y - 120, button: 'left', clickCount: 1, pointerType: 'touch' });
  await sleep(200);
  const afterA = await ev(cdp, `[...document.querySelectorAll('#draggable-list1 li')].map(l=>l.textContent).join('|')`);
  check('touch: drag by item body is ignored (scroll gesture)', afterA === beforeA, afterA);

  // 8b) тап по «точечкам» (handle) — перетаскивает: 2-й элемент встаёт на 1-ю позицию
  const dragWord = await ev(cdp, `document.querySelector('#draggable-list1 li:nth-child(2)').textContent`);
  const h1 = await ev(cdp, `(() => { const li = document.querySelector('#draggable-list1 li:nth-child(2)'); const h = li.querySelector('.disc-handle').getBoundingClientRect(); return { x: h.left + h.width/2, y: h.top + h.height/2 }; })()`);
  await cdp.send('Input.dispatchMouseEvent', { type: 'mousePressed', x: h1.x, y: h1.y, button: 'left', clickCount: 1, pointerType: 'touch' });
  await sleep(60);
  for (let i = 1; i <= 6; i++) { await cdp.send('Input.dispatchMouseEvent', { type: 'mouseMoved', x: h1.x, y: h1.y - 130*i/6, pointerType: 'touch' }); await sleep(30); }
  await sleep(60);
  await cdp.send('Input.dispatchMouseEvent', { type: 'mouseReleased', x: h1.x, y: h1.y - 130, button: 'left', clickCount: 1, pointerType: 'touch' });
  await sleep(200);
  const afterB = await ev(cdp, `[...document.querySelectorAll('#draggable-list1 li')].map(l=>l.textContent).join('|')`);
  check('touch: drag by handle reorders', afterB.startsWith(dragWord + '|'), afterB);

  // 9) клавиатура: фокус на 2-м элементе, Space, ArrowUp, Space — меняется местами с 1-м
  const beforeKb = await ev(cdp, `[...document.querySelectorAll('#draggable-list1 li')].map(l=>l.textContent)`);
  await ev(cdp, `document.querySelector('#draggable-list1 li:nth-child(2)').focus()`);
  for (const key of ['Space', 'ArrowUp', 'Space']) {
    const code = key === 'Space' ? 'Space' : 'ArrowUp';
    const vk = key === 'Space' ? 32 : 38;
    const kv = key === 'Space' ? ' ' : key;
    await cdp.send('Input.dispatchKeyEvent', { type: 'keyDown', key: kv, code, windowsVirtualKeyCode: vk });
    await cdp.send('Input.dispatchKeyEvent', { type: 'keyUp', key: kv, code, windowsVirtualKeyCode: vk });
    await sleep(60);
  }
  const kbOrder = await ev(cdp, `[...document.querySelectorAll('#draggable-list1 li')].map(l=>l.textContent).join('|')`);
  const kbExpected = [beforeKb[1], beforeKb[0], ...beforeKb.slice(2)].join('|');
  check('keyboard reorder works', kbOrder === kbExpected, kbOrder);

  // 10) клик по оверлею закрывает визард
  await cdp.send('Input.dispatchMouseEvent', { type: 'mousePressed', x: 8, y: 500, button: 'left', clickCount: 1 });
  await cdp.send('Input.dispatchMouseEvent', { type: 'mouseReleased', x: 8, y: 500, button: 'left', clickCount: 1 });
  await sleep(150);
  const ovClosed = await ev(cdp, `!document.querySelector('#wizardmodal').classList.contains('is-open')`);
  check('overlay click closes wizard', ovClosed);

  // 11) никаких необработанных исключений
  check('no uncaught page exceptions', consoleErrors.length === 0, consoleErrors.slice(0, 3).join(' || '));

  // 12) за всю сессию не было ни одного http(s)-запроса (полная офлайн-самодостаточность)
  check('zero external network requests during session', netRequests.length === 0, netRequests.slice(0, 3).join(' , '));

  // 13) мобильный вид (375×812): одна колонка, полноэкранная модалка
  await cdp.send('Emulation.setTouchEmulationEnabled', { enabled: false });
  await cdp.send('Emulation.setDeviceMetricsOverride', { width: 375, height: 812, deviceScaleFactor: 2, mobile: true });
  await cdp.send('Page.navigate', { url: 'file://' + file });
  await sleep(700);
  await ev(cdp, `document.querySelector('.js-open-disc').click()`);
  await sleep(300);
  const mob = await ev(cdp, `(() => {
    const pane = document.querySelector('.disc-pane.is-active');
    const cards = pane.querySelectorAll('.disc-card').length;
    const first = pane.querySelector('.disc-card').getBoundingClientRect();
    const dialog = document.querySelector('#wizardmodal .disc-modal__dialog').getBoundingClientRect();
    return { cards, cardW: Math.round(first.width), dialogW: Math.round(dialog.width), dialogH: Math.round(dialog.height) };
  })()`);
  check('mobile: 3 cards stacked, dialog fullscreen', mob.cards === 3 && mob.cardW > 300 && mob.dialogW === 375 && mob.dialogH === 812,
    `cards=${mob.cards} cardW=${mob.cardW} dialog=${mob.dialogW}x${mob.dialogH}`);
  const shotM = await cdp.send('Page.captureScreenshot', { format: 'png' });
  writeFileSync(join(outdir, 'shot-mobile.png'), Buffer.from(shotM.data, 'base64'));

} catch (e) {
  failed = true;
  say('ERROR: ' + (e && e.stack || e));
} finally {
  chrome.kill('SIGKILL');
  writeFileSync(join(outdir, 'smoke.log'), log.join('\n') + '\n');
  say(failed ? 'SMOKE: FAIL' : 'SMOKE: PASS');
  process.exit(failed ? 1 : 0);
}
