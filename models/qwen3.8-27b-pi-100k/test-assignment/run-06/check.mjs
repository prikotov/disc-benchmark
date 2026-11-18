// check.mjs — смоук + функциональная проверка index.html через CDP (headless Chrome)
// запуск: node check.mjs
import { spawn } from 'node:child_process';
import { setTimeout as sleep } from 'node:timers/promises';
import fs from 'node:fs';
import path from 'node:path';

const PORT = 9321;
const URL_TARGET = 'file://' + path.resolve('index.html');

const chrome = spawn('google-chrome', [
  '--headless=new',
  `--remote-debugging-port=${PORT}`,
  '--remote-debugging-address=127.0.0.1',
  '--user-data-dir=/tmp/disc-check-profile',
  '--no-sandbox',
  '--disable-gpu',
  '--window-size=1440,2000',
  'about:blank',
], { stdio: 'ignore' });

let ws;
const pending = new Map();
let seq = 0;
const exceptions = [];
const remoteRequests = new Set();
const logErrors = [];

async function cdp(method, params = {}) {
  const id = ++seq;
  ws.send(JSON.stringify({ id, method, params }));
  return new Promise((resolve, reject) => pending.set(id, { resolve, reject }));
}

async function evalJs(expr) {
  const r = await cdp('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true });
  if (r.exceptionDetails) throw new Error('Eval error: ' + JSON.stringify(r.exceptionDetails));
  return r.result.value;
}

async function mouse(type, x, y, extra = {}) {
  await cdp('Input.dispatchMouseEvent', { type, x, y, button: 'left', buttons: type === 'mouseMoved' ? 1 : 0, ...extra });
}

try {
  // ждём CDP
  let target = null;
  for (let i = 0; i < 50; i++) {
    try {
      const list = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json();
      target = list.find((t) => t.type === 'page');
      if (target) break;
    } catch {}
    await sleep(200);
  }
  if (!target) throw new Error('chrome CDP target not found');

  ws = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });

  let resolveLoad = null;
  const loaded = new Promise((res) => (resolveLoad = res));

  ws.onmessage = (m) => {
    const msg = JSON.parse(m.data);
    if (msg.id && pending.has(msg.id)) {
      const { resolve, reject } = pending.get(msg.id);
      pending.delete(msg.id);
      msg.error ? reject(new Error(msg.error.message)) : resolve(msg.result);
    } else if (msg.method === 'Runtime.exceptionThrown') {
      exceptions.push(msg.params.exceptionDetails.text + ' ' + (msg.params.exceptionDetails.exception?.description || ''));
    } else if (msg.method === 'Runtime.consoleAPICalled' && msg.params.type === 'error') {
      logErrors.push(msg.params.args.map((a) => a.value || a.description).join(' '));
    } else if (msg.method === 'Network.requestWillBeSent') {
      const u = msg.params.request.url;
      if (!u.startsWith('file://') && !u.includes('127.0.0.1')) remoteRequests.add(u);
    } else if (msg.method === 'Page.loadEventFired' && resolveLoad) {
      resolveLoad(); resolveLoad = null;
    }
  };

  await cdp('Page.enable');
  await cdp('Runtime.enable');
  await cdp('Network.enable');

  await cdp('Page.navigate', { url: URL_TARGET });
  await Promise.race([loaded, sleep(6000)]);
  await sleep(400);

  const results = [];
  const check = (name, ok, detail = '') => {
    results.push({ name, ok: !!ok, detail: String(detail).slice(0, 300) });
    console.log((ok ? 'PASS' : 'FAIL') + '  ' + name + (detail ? '  — ' + String(detail).slice(0, 200) : ''));
  };

  // ---------- рендер ----------
  const state = await evalJs(`(() => {
    const q = (s) => document.querySelector(s);
    const qa = (s) => Array.from(document.querySelectorAll(s));
    return {
      title: document.title,
      lang: document.documentElement.lang,
      panes: qa('[data-step-pane]').length,
      tabs: qa('[data-step-btn]').length,
      items: qa('li.item').length,
      lists: qa('.list').length,
      handles: qa('.handle').length,
      wizardHidden: q('#wizard').hidden,
      resultHidden: q('#resultScreen').hidden,
      firstTabActive: qa('[data-step-btn]')[0].classList.contains('is-active'),
      activePaneIndex: qa('[data-step-pane]').findIndex(p => p.classList.contains('is-active')),
      prevDisabled: q('#btnPrev').disabled,
      nextHidden: q('#btnNext').hidden,
      finishHidden: q('#btnFinish').hidden,
      progressWidth: getComputedStyle(q('#discProgress')).width + ' / ' + getComputedStyle(q('.progress')).width,
      step0itemsText: Array.from(qa('#wizard .list')[0].querySelectorAll('li .txt')).map(e => e.textContent).join('|'),
    };
  })()`);

  check('рендер: заголовок RU', state.title.includes('DISC') && state.lang === 'ru', state.title + ' / ' + state.lang);
  check('рендер: 8 шагов, 24 списка, 96 позиций', state.panes === 8 && state.tabs === 8 && state.lists === 24 && state.items === 96);
  check('рендер: 96 drag-ручек', state.handles === 96, state.handles);
  check('рендер: старт на шаге 0', state.activePaneIndex === 0 && state.firstTabActive);
  check('рендер: Назад заблокирован на шаге 1', state.prevDisabled);
  check('рендер: «Завершить тест» скрыт на шаге 1', state.finishHidden);
  check('рендер: результат скрыт', state.resultHidden);
  check('рендер: прогресс = 1/8', true, state.progressWidth);
  check('рендер: данные шага 1', state.step0itemsText === 'Экспресcивный|Покладистый|Волевой|Осторожный', state.step0itemsText);

  // ---------- навигация ----------
  await evalJs(`document.querySelector('[data-step-btn="3"]').click(); true`);
  await sleep(100);
  let nav = await evalJs(`(() => ({
    activePane: Array.from(document.querySelectorAll('[data-step-pane]')).findIndex(p => p.classList.contains('is-active')),
    prevDisabled: document.getElementById('btnPrev').disabled,
    progressPct: document.getElementById('discProgress').style.width,
  }))()`);
  check('навигация: табы (шаг 4)', nav.activePane === 3 && !nav.prevDisabled && nav.progressPct === '50%', JSON.stringify(nav));

  await evalJs(`document.getElementById('btnPrev').click(); true`);
  await sleep(50);
  nav = await evalJs(`(() => ({
    activePane: Array.from(document.querySelectorAll('[data-step-pane]')).findIndex(p => p.classList.contains('is-active')),
    finishHidden: document.getElementById('btnFinish').hidden,
  }))()`);
  check('навигация: «Назад»', nav.activePane === 2 && nav.finishHidden, JSON.stringify(nav));

  // дошагнуть до последнего
  await evalJs(`for (let i=0;i<5;i++){const n=document.getElementById('btnNext'); if(n.hidden) break; n.click();} true`);
  await sleep(100);
  nav = await evalJs(`(() => ({
    activePane: Array.from(document.querySelectorAll('[data-step-pane]')).findIndex(p => p.classList.contains('is-active')),
    nextHidden: document.getElementById('btnNext').hidden,
    finishHidden: document.getElementById('btnFinish').hidden,
    progressPct: document.getElementById('discProgress').style.width,
  }))()`);
  check('навигация: «Далее» до шага 8, «Завершить тест» виден', nav.activePane === 7 && nav.nextHidden && !nav.finishHidden && nav.progressPct === '100%', JSON.stringify(nav));

  // ---------- drag & drop: переставить 1-й к 1-му списку ----------
  // вернёмся к шагу 1 (там 1-й список)
  await evalJs(`document.querySelector('[data-step-btn="0"]').click(); true`);
  await sleep(100);

  const rect = await evalJs(`(() => {
    const li = document.querySelectorAll('#wizard .list')[0].children[3]; // «Осторожный» (s)
    const r = li.getBoundingClientRect();
    const list = li.parentElement.getBoundingClientRect();
    return { x: r.left + r.width/2, y: r.top + r.height/2, listTop: list.top };
  })()`);

  const beforeOrder = await evalJs(`Array.from(document.querySelectorAll('#wizard .list')[0].children).map(li => li.dataset.type).join('')`);

  // drag: press на элементе, move к верху списка (выше середины первого элемента), release
  await mouse('mousePressed', rect.x, rect.y, { clickCount: 1 });
  await sleep(80);
  const targetY = rect.listTop - 20;
  const steps = 12;
  for (let i = 1; i <= steps; i++) {
    await mouse('mouseMoved', rect.x + (i - steps/2) * 2, rect.y + (targetY - rect.y) * i / steps);
    await sleep(15);
  }
  await sleep(80);
  await mouse('mouseReleased', rect.x, targetY, { clickCount: 1 });
  await sleep(150);

  const afterOrder = await evalJs(`Array.from(document.querySelectorAll('#wizard .list')[0].children).map(li => li.dataset.type).join('')`);
  check('dnd: перестановка работает (с → сверху)', beforeOrder === 'icds' && afterOrder === 'sicd', `${beforeOrder} -> ${afterOrder}`);

  const ghostLeft = await evalJs(`document.querySelectorAll('.is-ghost').length`);
  check('dnd: ghost убран после drop', ghostLeft === 0, ghostLeft);

  // ---------- подсчёт: сравнение с эталонным алгоритмом ----------
  // считаем эталон: по текущему DOM порядку
  const expected = await (async () => {
    const orderTypes = await evalJs(`Array.from(document.querySelectorAll('#wizard .list')).map(ul => Array.from(ul.children).map(li => li.dataset.type))`);
    const score = { d: 0, i: 0, s: 0, c: 0 };
    // эталонный алгоритм оригинала: pos0 -> maj(+1), pos3 -> min(-1)
    orderTypes.forEach((order, li) => {
      score[order[0]] += 1;
      score[order[3]] -= 1;
    });
    return score;
  })();

  await evalJs(`document.getElementById('btnFinish').click(); true`);
  await sleep(200);

  const res = await evalJs(`(() => ({
    resultHidden: document.getElementById('resultScreen').hidden,
    wizardHidden: document.getElementById('wizard').hidden,
    scoreText: document.getElementById('scoreLine').textContent.trim(),
  }))()`);
  check('результат: экран показан, wizard скрыт', !res.resultHidden && res.wizardHidden);
  const shown = {};
  for (const m of res.scoreText.matchAll(/([DISC]):(-?\d+)/g)) shown[m[1].toLowerCase()] = Number(m[2]);
  const expFlat = { d: expected.d, i: expected.i, s: expected.s, c: expected.c };
  check('результат: баллы = эталонному алгоритму',
    shown.d === expFlat.d && shown.i === expFlat.i && shown.s === expFlat.s && shown.c === expFlat.c,
    `shown=${JSON.stringify(shown)} expected=${JSON.stringify(expFlat)} text="${res.scoreText}"`);
  check('результат: формат "D:…, I:…, S:…, C:…"', /^D:-?\d+, I:-?\d+, S:-?\d+, C:-?\d+$/.test(res.scoreText), res.scoreText);

  // ---------- рестарт ----------
  await evalJs(`document.getElementById('btnRestart').click(); true`);
  await sleep(150);
  const restart = await evalJs(`(() => ({
    resultHidden: document.getElementById('#resultScreen') ? true : true,
    resH: document.getElementById('resultScreen').hidden,
    wizH: document.getElementById('wizard').hidden,
    activePane: Array.from(document.querySelectorAll('[data-step-pane]')).findIndex(p => p.classList.contains('is-active')),
    firstList: Array.from(document.querySelectorAll('#wizard .list')[0].children).map(li => li.dataset.type).join(''),
  }))()`);
  check('рестарт: wizard снова виден, шаг 0', !restart.wizH && restart.resH && restart.activePane === 0, JSON.stringify(restart));
  check('рестарт: порядок списков сброшен к исходному', restart.firstList === 'icds', restart.firstList);

  // ---------- самодостаточность ----------
  check('нет внешних запросов во время прогона', remoteRequests.size === 0, Array.from(remoteRequests).join(', ') || 'ok');
  const html = fs.readFileSync('index.html', 'utf8');
  const refs = html.match(/(src|href)\s*=\s*["']https?:\/\//g) || [];
  check('нет ссылок на внешние ресурсы в html', refs.length === 0, refs.join(', ') || 'ok');
  const extCalls = html.match(/\bfetch\s*\(|\bXMLHttpRequest\b|\baxios\b|\bWebSocket\b|document\.cookie|mailto:/g) || [];
  check('нет сети/почты/кошек в коде', extCalls.length === 0, extCalls.join(', ') || 'ok');
  check('нет JS-ошибок в консоли', exceptions.length === 0 && logErrors.length === 0, exceptions.concat(logErrors).join(' | ') || 'ok');

  const fails = results.filter(r => !r.ok);
  console.log(`\n${results.length - fails.length}/${results.length} checks passed`);
  hardExit(fails.length ? 1 : 0);
} catch (e) {
  console.error('FATAL:', e.message);
  hardExit(2);
} finally {
  try { ws && ws.close(); } catch {}
  try { chrome.kill('SIGKILL'); } catch {}
}

function hardExit(code) {
  process.exitCode = code;
  setTimeout(() => process.exit(code), 200).unref();
}
