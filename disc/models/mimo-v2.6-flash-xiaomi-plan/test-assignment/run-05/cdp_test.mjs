// Функциональный тест index.html в headless Chrome (CDP без зависимостей).
// Запуск: node cdp_test.mjs <path-to-index.html>
import { spawn } from 'node:child_process';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { pathToFileURL } from 'node:url';

const fileArg = process.argv[2] || 'index.html';
const url = pathToFileURL(fileArg).href;
const PORT = 9333 + (process.pid % 500);
const profile = mkdtempSync(join(tmpdir(), 'cdp-'));

const chrome = spawn('google-chrome', [
  '--headless=new', `--remote-debugging-port=${PORT}`, `--user-data-dir=${profile}`,
  '--no-sandbox', '--disable-gpu', '--window-size=1400,1000', 'about:blank',
], { stdio: 'ignore' });

const sleep = (ms) => new Promise(r => setTimeout(r, ms));

async function getWsUrl() {
  for (let i = 0; i < 50; i++) {
    try {
      const res = await fetch(`http://127.0.0.1:${PORT}/json/list`);
      const list = await res.json();
      const page = list.find(t => t.type === 'page');
      if (page && page.webSocketDebuggerUrl) return page.webSocketDebuggerUrl;
    } catch {}
    await sleep(200);
  }
  throw new Error('CDP не поднялся');
}

const ws = new WebSocket(await getWsUrl());
await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });

let id = 0;
const pending = new Map();
ws.onmessage = (ev) => {
  const msg = JSON.parse(ev.data);
  if (msg.id && pending.has(msg.id)) {
    const { resolve, reject } = pending.get(msg.id);
    pending.delete(msg.id);
    if (msg.error) reject(new Error(msg.error.message));
    else resolve(msg.result);
  }
};
function send(method, params = {}) {
  const mid = ++id;
  ws.send(JSON.stringify({ id: mid, method, params }));
  return new Promise((resolve, reject) => pending.set(mid, { resolve, reject }));
}

const results = [];
function check(name, cond, detail = '') {
  results.push({ name, ok: !!cond, detail });
  console.log(`${cond ? 'PASS' : 'FAIL'}  ${name}${detail ? ' — ' + detail : ''}`);
}

try {
  const s = send; // подключаемся напрямую к странице (без sessionId)

  await s('Page.enable');
  await s('Runtime.enable');
  const errs = [];
  await s('Page.addScriptToEvaluateOnNewDocument', {
    source: `window.__errors = [];
      window.addEventListener('error', e => window.__errors.push(String(e.message)));
      window.addEventListener('unhandledrejection', e => window.__errors.push('rejection: ' + String(e.reason)));
      const origErr = console.error; console.error = (...a) => { window.__errors.push(a.join(' ')); origErr(...a); };`,
  });

  await s('Page.navigate', { url });
  await sleep(700);

  const evalJs = async (expr) => {
    const r = await s('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true });
    if (r.exceptionDetails) throw new Error('eval: ' + JSON.stringify(r.exceptionDetails.exception));
    return r.result.value;
  };

  // --- структура ---
  check('24 списка', await evalJs(`document.querySelectorAll('.disc-list').length`) === 24);
  check('96 пунктов', await evalJs(`document.querySelectorAll('.disc-item').length`) === 96);
  check('8 панелей', await evalJs(`document.querySelectorAll('[data-step-pane]').length`) === 8);
  check('нет внешних запросов (resourcetiming)',
    await evalJs(`performance.getEntriesByType('resource').filter(r => !r.name.startsWith('file:')).length`) === 0);
  check('ручки drag добавлены', await evalJs(`document.querySelectorAll('.disc-handle').length`) === 96);

  // --- открытие модалки ---
  await evalJs(`document.querySelector('[data-open-wizard]').click()`);
  check('модалка открыта', await evalJs(`document.getElementById('wizardmodal').classList.contains('is-open')`));
  check('scroll заблокирован', await evalJs(`document.body.classList.contains('no-scroll')`));
  check('шаг 0: прогресс 12.5%', await evalJs(`document.getElementById('discProgress').style.width`) === '12.5%');
  check('Назад disabled на шаге 0', await evalJs(`document.querySelector('[data-disc-prev]').disabled`) === true);
  check('Финиш скрыт на шаге 0', await evalJs(`document.querySelector('[data-disc-finish]').hidden`) === true);

  // --- навигация вперёд до последнего шага ---
  for (let i = 0; i < 7; i++) await evalJs(`document.querySelector('[data-disc-next]').click()`);
  check('шаг 7 активен', await evalJs(`document.querySelector('[data-step-btn="7"]').classList.contains('is-active')`));
  check('прогресс 100%', await evalJs(`document.getElementById('discProgress').style.width`) === '100%');
  check('Далее скрыт на шаге 7', await evalJs(`document.querySelector('[data-disc-next]').hidden`) === true);
  check('Финиш виден на шаге 7', await evalJs(`document.querySelector('[data-disc-finish]').hidden`) === false);

  // --- переход по табу назад ---
  await evalJs(`document.querySelector('[data-step-btn="2"]').click()`);
  check('таб 3 (шаг 2) активен', await evalJs(`document.querySelector('[data-step-btn="2"]').classList.contains('is-active')`));
  await evalJs(`document.querySelector('[data-step-btn="7"]').click()`);

  // --- drag & drop через синтетические PointerEvent ---
  // перетащить 1-й пункт списка 22 (шаг 7) в конец: pos0 -> pos3
  const dragRes = await evalJs(`(function () {
    const ul = document.getElementById('draggable-list22');
    const items = () => Array.from(ul.children);
    const first = items()[0];
    const last = items()[3];
    const r1 = first.getBoundingClientRect();
    const r2 = last.getBoundingClientRect();
    const opt = (x, y, extra = {}) => Object.assign({
      bubbles: true, cancelable: true, pointerId: 7, pointerType: 'mouse',
      clientX: x, clientY: y, button: 0, buttons: 1, isPrimary: true,
    }, extra);
    first.dispatchEvent(new PointerEvent('pointerdown', opt(r1.left + 30, r1.top + r1.height / 2)));
    window.dispatchEvent(new PointerEvent('pointermove', opt(r1.left + 30, r1.top + 5)));
    window.dispatchEvent(new PointerEvent('pointermove', opt(r2.left + 30, r2.top + r2.height - 3)));
    window.dispatchEvent(new PointerEvent('pointerup', opt(r2.left + 30, r2.top + r2.height - 3, { buttons: 0 })));
    const order = items().map(li => li.textContent.trim());
    return { order, firstType: first.getAttribute('data-type'), lastType: last.getAttribute('data-type') };
  })()`);
  check('drag: пункт ушёл в конец списка',
    dragRes.order[3].includes('Соглашающийся') && dragRes.order[0].includes('Владеющий собой'),
    JSON.stringify(dragRes.order));
  check('drag: clone удалён после отпускания', await evalJs(`document.querySelectorAll('.disc-clone').length`) === 0);
  check('drag: классы очищены', await evalJs(`document.body.classList.contains('is-drag-active')`) === false);

  // --- подсчёт: вручную выставим порядок и проверим формулу ---
  // список 22: pos0 = i (Настойчивый), pos3 = c (Соглашающийся) после drag? проверим фактический payload
  const payloadCheck = await evalJs(`(function () {
    const lists = Array.from(document.querySelectorAll('.disc-list'));
    const maj = [], min = [];
    lists.forEach(ul => {
      const lis = Array.from(ul.children);
      maj.push(lis[0].getAttribute('data-type'));
      min.push(lis[3].getAttribute('data-type'));
    });
    const count = (a, ch) => a.filter(v => v === ch).length;
    return {
      d: count(maj,'d') - count(min,'d'), i: count(maj,'i') - count(min,'i'),
      s: count(maj,'s') - count(min,'s'), c: count(maj,'c') - count(min,'c'),
    };
  })()`);

  // --- завершение ---
  await evalJs(`document.querySelector('[data-disc-finish]').click()`);
  await sleep(200);
  check('модалка теста закрыта после финиша',
    await evalJs(`!document.getElementById('wizardmodal').classList.contains('is-open')`));
  check('экран результата открыт',
    await evalJs(`document.getElementById('resultModal').classList.contains('is-open')`));
  const scoreText = await evalJs(`document.getElementById('resultScore').textContent`);
  const expected = `D:${payloadCheck.d}, I:${payloadCheck.i}, S:${payloadCheck.s}, C:${payloadCheck.c}`;
  check('баллы совпадают с независимым расчётом', scoreText === expected,
    `получено "${scoreText}", ожидалось "${expected}"`);
  check('формат баллов D/I/S/C',
    /^D:-?\d+, I:-?\d+, S:-?\d+, C:-?\d+$/.test(scoreText), scoreText);
  check('сумма баллов = 0',
    payloadCheck.d + payloadCheck.i + payloadCheck.s + payloadCheck.c === 0);

  // --- рестарт ---
  await evalJs(`document.querySelector('[data-restart]').click()`);
  await sleep(100);
  check('после «Пройти заново» модалка открыта на шаге 0',
    await evalJs(`document.getElementById('wizardmodal').classList.contains('is-open') && document.getElementById('discProgress').style.width === '12.5%'`));
  const firstList = await evalJs(`Array.from(document.getElementById('draggable-list22').children).map(li => li.textContent.trim())`);
  check('порядок списков сброшен',
    firstList[0].includes('Соглашающийся') && firstList[3].includes('Настойчивый'),
    JSON.stringify(firstList));

  // --- Esc закрывает ---
  await evalJs(`document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))`);
  check('Esc закрывает модалку', await evalJs(`!document.getElementById('wizardmodal').classList.contains('is-open')`));
  check('scroll разблокирован', await evalJs(`!document.body.classList.contains('no-scroll')`));

  // --- touch: перетаскивание только за ручку (как в оригинале) ---
  await evalJs(`document.querySelector('[data-open-wizard]').click()`);
  await sleep(200);
  const touchRes = await evalJs(`(function () {
    const ul = document.getElementById('draggable-list2');
    const items = () => Array.from(ul.children);
    const first = items()[0];
    const last = items()[3];
    const r1 = first.getBoundingClientRect();
    const r2 = last.getBoundingClientRect();
    const opt = (x, y) => ({ bubbles: true, cancelable: true, pointerId: 9, pointerType: 'touch',
      clientX: x, clientY: y, button: 0, buttons: 1, isPrimary: true });
    const before = items().map(li => li.textContent.trim());
    // 1) касание телом пункта (не за ручку) — не должно начинать drag
    first.dispatchEvent(new PointerEvent('pointerdown', opt(r1.left + 30, r1.top + r1.height / 2)));
    window.dispatchEvent(new PointerEvent('pointermove', opt(r1.left + 30, r1.top + 100)));
    window.dispatchEvent(new PointerEvent('pointerup', opt(r1.left + 30, r1.top + 100)));
    const afterBodyTouch = items().map(li => li.textContent.trim());
    // 2) касание за ручку — должно перетащить в конец
    const handle = first.querySelector('.disc-handle');
    const hr = handle.getBoundingClientRect();
    handle.dispatchEvent(new PointerEvent('pointerdown', opt(hr.left + hr.width / 2, hr.top + hr.height / 2)));
    window.dispatchEvent(new PointerEvent('pointermove', opt(r2.left + 60, r2.top + r2.height - 4)));
    window.dispatchEvent(new PointerEvent('pointerup', opt(r2.left + 60, r2.top + r2.height - 4)));
    const afterHandleDrag = items().map(li => li.textContent.trim());
    return { before, afterBodyTouch, afterHandleDrag,
      clones: document.querySelectorAll('.disc-clone').length };
  })()`);
  check('touch: касание телом пункта не двигает список',
    JSON.stringify(touchRes.before) === JSON.stringify(touchRes.afterBodyTouch),
    JSON.stringify(touchRes.afterBodyTouch));
  check('touch: перетаскивание за ручку работает',
    touchRes.afterHandleDrag[3] === touchRes.before[0] && touchRes.afterHandleDrag[0] === touchRes.before[1],
    JSON.stringify(touchRes.afterHandleDrag));
  check('touch: clone удалён', touchRes.clones === 0);
  await evalJs(`document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))`);
  await sleep(100);

  // --- ошибки JS ---
  const jsErrors = await evalJs(`window.__errors`);
  check('нет ошибок JS', jsErrors.length === 0, JSON.stringify(jsErrors));

  // --- сетевые запросы ---
  const netEntries = await evalJs(`performance.getEntriesByType('resource').map(r => r.name)`);
  check('только file:// ресурсы', netEntries.every(n => n.startsWith('file:')), JSON.stringify(netEntries));
} finally {
  try { ws.close(); } catch {}
  chrome.kill('SIGKILL');
  rmSync(profile, { recursive: true, force: true });
}

const failed = results.filter(r => !r.ok);
console.log(`\nИтого: ${results.length - failed.length}/${results.length} passed`);
process.exit(failed.length ? 1 : 0);
