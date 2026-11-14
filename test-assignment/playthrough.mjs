#!/usr/bin/env node
// Универсальный драйвер прохождения решения: поток «старт → 8 шагов →
// результат» + скриншоты для отчёта.
//
// Что делает: грузит index.html в headless Chrome; находит видимые
// «списки-вопросы» (контейнер с ровно 4 детьми, чей набор текстов совпадает
// с эталонным вопросом — без привязки к тегам), переставляет детей по
// сценарию, жмёт «Далее»/«Завершить тест», читает экран результата.
//
// Честное ограничение (проверено экспериментами 2026-11-14): автоматическая
// симуляция drag&drop не даёт воспроизводимой раскладки на произвольных
// реализациях (реальный mouse-drag зависит от SortableJS-fallback/скроллов/
// хендлов и откатывается библиотекой). Поэтому ПОТОК и РЕНДЕР — вердикт
// драйвера, а показанные баллы — справочно: их сверяют судьи по коду.
//
// Запуск: node playthrough.mjs --html <index.html> --ref questions.json \
//            --out-dir <run>/screenshots --json <run>/playthrough.json

import puppeteer from 'puppeteer-core';
import fs from 'node:fs';
import path from 'node:path';

const arg = (name, def = undefined) => {
  const i = process.argv.indexOf('--' + name);
  return i >= 0 ? process.argv[i + 1] : def;
};

const htmlPath = path.resolve(arg('html'));
const refPath = path.resolve(arg('ref'));
const outDir = path.resolve(arg('out-dir', './screenshots'));
const jsonPath = arg('json') ? path.resolve(arg('json')) : path.join(outDir, 'playthrough.json');
fs.mkdirSync(outDir, { recursive: true });

const ref = JSON.parse(fs.readFileSync(refPath, 'utf-8'));
// известные опечатки оригинала — нормализуем при сопоставлении наборов
// (решение владельца: исправление — плюс модели, не дефект)
const KNOWN_QUIRKS = { 'Экспресcивный': 'Экспрессивный' };
const quirksJson = JSON.stringify(KNOWN_QUIRKS);
const bySet = new Map();
for (const q of ref.questions) {
  bySet.set(q.items.map(i => (KNOWN_QUIRKS[i.text] || i.text)).sort().join('|'),
            Object.fromEntries(q.items.map(i => [(KNOWN_QUIRKS[i.text] || i.text), i.type])));
}
const refKeysJson = JSON.stringify([...bySet.keys()]);

const result = {
  ran: true, html: htmlPath,
  steps: [], questions_processed: 0,
  displayed: null, raw_result_text: null,
  screenshots: [], notes: [], console_errors: [], incomplete: false,
};

const sleep = (ms) => new Promise(r => setTimeout(r, ms));

const shot = async (page, name) => {
  const p = path.join(outDir, name + '.png');
  await page.screenshot({ path: p, fullPage: false });
  result.screenshots.push(path.basename(p));
};

// строгая видимость: display/visibility/opacity по всей цепочке предков
// (offsetParent/getClientRects пропускают visibility:hidden и opacity:0)
const VISIBLE_FN = `(el) => {
  for (let e = el; e; e = e.parentElement) {
    const cs = getComputedStyle(e);
    if (cs.display === 'none' || cs.visibility === 'hidden' || Number(cs.opacity) === 0) return false;
  }
  const r = el.getBoundingClientRect();
  return r.width > 0 && r.height > 0;
}`;
const clickByText = async (page, reSrc) => {
  return page.evaluate((pattern, visFn) => {
    const rx = new RegExp(pattern, 'i');
    const visible = new Function('return ' + visFn)();
    const btns = [...document.querySelectorAll('button, a[role=button], [role=button], input[type=submit], input[type=button], a')]
      .filter((b) => visible(b));
    const hit = btns.find((b) => rx.test((b.textContent || b.value || '').trim()));
    if (hit) { hit.click(); return (hit.textContent || hit.value || '').trim().slice(0, 40); }
    return null;
  }, reSrc, VISIBLE_FN);
};

// страница: число видимых списков-вопросов (4 ребёнка, набор текстов из эталона)
const FIND_LISTS = (keysJson, quirksJson) => {
  // мягкая видимость: скрытые будущие панели тоже обрабатываем —
  // события дойдут до состояния/порядка в любом случае
  const vis = (el) => !!(el.offsetParent || el.getClientRects().length);
  const norm = (s) => { s = (s || '').replace(/\s+/g, ' ').trim(); s = s.replace(/^[^\p{L}]+/u, ''); const q = JSON.parse(quirksJson); return q[s] || s; };
  const keys = new Set(JSON.parse(keysJson));
  let n = 0;
  for (const el of document.querySelectorAll('body *')) {
    if (!vis(el) || el.children.length !== 4) continue;
    const texts = [...el.children].map((c) => norm(c.textContent));
    if (texts.some((t) => !t || t.length > 40)) continue;
    if (keys.has([...texts].sort().join('|'))) n++;
  }
  return n;
};

// страница: перетасовать видимые списки (дети вверх/вниз + события) —
// чтобы шагивизарда прошли, точный порядок не критичен
const SHUFFLE = (mapJson, quirksJson) => {
  const vis = (el) => !!(el.offsetParent || el.getClientRects().length);
  const norm = (s) => { s = (s || '').replace(/\s+/g, ' ').trim(); s = s.replace(/^[^\p{L}]+/u, ''); const q = JSON.parse(quirksJson); return q[s] || s; };
  const refMap = new Map(JSON.parse(mapJson));
  for (const el of document.querySelectorAll('body *')) {
    if (!vis(el) || el.children.length !== 4) continue;
    const children = [...el.children];
    const texts = children.map((c) => norm(c.textContent));
    if (texts.some((t) => !t || t.length > 40)) continue;
    if (!refMap.has([...texts].sort().join('|'))) continue;
    const first = children[0], last = children[3];
    el.insertBefore(children[2], first); // произвольная перестановка верх/низ
    el.appendChild(children[1]);
    for (const child of [first, last]) {
      for (const type of ['dragstart', 'dragend', 'mouseup', 'change']) {
        child.dispatchEvent(new Event(type, { bubbles: true }));
      }
    }
    for (const type of ['input', 'change']) el.dispatchEvent(new Event(type, { bubbles: true }));
  }
};

(async () => {
  const browser = await puppeteer.launch({
    executablePath: '/usr/bin/google-chrome',
    headless: true,
    args: ['--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage'],
  });
  const page = await browser.newPage();
  await page.setViewport({ width: 1280, height: 900 });
  page.on('pageerror', (e) => result.console_errors.push(String(e).slice(0, 200)));
  try {
    await page.goto('file://' + htmlPath, { waitUntil: 'load', timeout: 30000 });
    await sleep(500);
    await shot(page, 'start');

    // стартовый экран может отсутствовать (приложение сразу показывает тест)
    const clicked = await clickByText(page, 'пройти\\s*тест|начать\\s*тест|начнем|прошли\\s*тест');
    if (clicked) result.notes.push('старт: клик по «' + clicked + '»');
    await sleep(600);

    for (let step = 0; step < 60; step++) {
      let nLists = await page.evaluate(FIND_LISTS, refKeysJson, quirksJson);
      if (nLists === 0 && result.questions_processed < 24) {
        // панель могла ещё рендериться — подождать и перечитать
        await sleep(700);
        nLists = await page.evaluate(FIND_LISTS, refKeysJson, quirksJson);
      }
      if (nLists > 0) {
        await page.evaluate(SHUFFLE, JSON.stringify([...bySet.entries()]), quirksJson);
        result.questions_processed += nLists;
        result.steps.push({ step, lists: nLists });
        if (!result.screenshots.includes('step.png') && nLists > 0) await shot(page, 'step');
      }

      if (result.questions_processed >= 24) {
        const fin = await clickByText(page, 'заверш|finish|результат|узнать результат');
        if (fin) { result.notes.push('клик «' + fin + '»'); break; }
      }
      const nxt = await clickByText(page, 'далее|дальше|next|следующ|→|›|»');
      if (!nxt) {
        const fin = await clickByText(page, 'заверш|finish|результат|узнать результат');
        if (fin) { result.notes.push('клик «' + fin + '» (dead-end)'); break; }
        if (result.questions_processed < 24) result.incomplete = true;
        result.notes.push('навигация остановилась: шаг ' + step + ', обработано ' + result.questions_processed);
        break;
      }
      await sleep(450);
    }

    await sleep(1200);
    const bodyText = await page.evaluate(() => document.body.innerText);
    result.raw_result_text = (bodyText || '').slice(-600);
    result.has_scores_on_screen = /D\s*[:=–-]\s*-?\d+|^\s*[+−–-]?\d+\s*$/m.test(bodyText || '');
    await shot(page, 'result');
  } catch (e) {
    result.incomplete = true;
    result.notes.push('ошибка драйвера: ' + String(e).slice(0, 200));
  } finally {
    await browser.close();
  }

  result.flow_ok = !result.incomplete && result.questions_processed >= 24
                 && result.screenshots.includes('result.png');
  fs.writeFileSync(jsonPath, JSON.stringify(result, null, 2) + '\n');
  console.log(JSON.stringify({
    ran: result.ran, flow_ok: result.flow_ok,
    questions_processed: result.questions_processed, steps: result.steps.length,
    has_scores_on_screen: result.has_scores_on_screen,
    incomplete: result.incomplete, console_errors: result.console_errors.length,
    screenshots: result.screenshots, notes: result.notes,
  }, null, 2));
})();
