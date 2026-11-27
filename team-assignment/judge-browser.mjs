#!/usr/bin/env node
// Браузерный судья team-assignment: автопрохождение продукта команды
// в headless Chrome по контракту задания (старт → 8 шагов × ранжирование
// 4 прилагательных → email → результат с интерпретацией), скриншоты
// этапов и функциональный вердикт. Эстетику оценивает judge-ui.py
// по скриншотам (внешняя vision-модель).
//
// Селекторы толерантные: известные id из контракта (#wizard, #emailStep,
// #resultStep) + фолбэки по ролям/текстам. Ранжирование — кнопки ↑/↓
// (задание разрешает «стрелки/клики»), drag не требуется.
//
// Запуск:
//   node judge-browser.mjs --url http://127.0.0.1:8099 \
//     --ref reference/questions.json --out-dir <run>/judgments/browser \
//     --json <run>/judgments/judge-browser.json [--email x@y.z] [--mobile]

import puppeteer from 'puppeteer-core';
import fs from 'node:fs';
import path from 'node:path';

const arg = (name, def = undefined) => {
  const i = process.argv.indexOf('--' + name);
  return i >= 0 ? (process.argv[i + 1] ?? true) : def;
};

const baseUrl = (arg('url') || 'http://127.0.0.1:8099').replace(/\/$/, '');
const refPath = path.resolve(arg('ref'));
const outDir = path.resolve(arg('out-dir', './judgments/browser'));
const jsonPath = path.resolve(arg('json') || path.join(outDir, 'judge-browser.json'));
const email = arg('email') || 'judge@example.com';
const mobile = arg('mobile') ? true : false;
fs.mkdirSync(outDir, { recursive: true });

const ref = JSON.parse(fs.readFileSync(refPath, 'utf-8'));
const canonBlocks = ref.questions; // 24 блока {id, items:[{type,text}]}
const canonQ = new Map(canonBlocks.map(b => [String(b.id), b]));

const checks = [];
const check = (name, ok, note = '') => {
  checks.push({ name, ok: !!ok, note });
  console.log(`${ok ? 'ok  ' : 'FAIL'} - ${name}${note ? ' — ' + note : ''}`);
};
const sleep = ms => new Promise(r => setTimeout(r, ms));
const shot = async (page, name) => {
  const f = path.join(outDir, `${mobile ? 'mobile-' : ''}${name}.png`);
  await page.screenshot({ path: f, fullPage: false });
  console.log('скриншот:', path.basename(f));
  return f;
};

const browser = await puppeteer.launch({
  executablePath: '/usr/bin/google-chrome',
  headless: 'new',
  args: ['--no-sandbox', '--disable-dev-shm-usage'],
});
const page = await browser.newPage();
await page.setViewport(mobile ? { width: 390, height: 844 } : { width: 1280, height: 900 });
const consoleErrors = [];
page.on('pageerror', e => consoleErrors.push(String(e)));
page.on('console', m => { if (m.type() === 'error') consoleErrors.push(m.text()); });

try {
  // --- 1. стартовая страница
  await page.goto(baseUrl + '/', { waitUntil: 'networkidle2', timeout: 30000 });
  await shot(page, 'start');
  const startText = await page.evaluate(() => document.body.innerText);
  check('старт: есть призыв начать', /пройти|начать|тест/i.test(startText));
  // ссылка на тест
  const link = await page.evaluateHandle(() =>
    document.querySelector('a[href*="test"], button') ||
    [...document.querySelectorAll('a,button')].find(a => /пройти|начать/i.test(a.textContent)));
  await link.asElement()?.click();
  await sleep(1200);
  // если клик не сработал — напрямую на /test
  if (!(await page.$('#wizard, .question, [class*="step"]'))) {
    await page.goto(baseUrl + '/test', { waitUntil: 'networkidle2' });
  }
  check('переход к шагам', !!(await page.$('#wizard, .question')));

  // --- 2. восемь шагов
  const stepsSeen = [];
  for (let step = 1; step <= 8; step++) {
    await page.waitForSelector('.question', { timeout: 15000 });
    const qs = await page.$$('.question');
    if (step === 1) {
      check('шаг: 3 вопроса на шаге', qs.length === 3, `найдено ${qs.length}`);
      const items = await qs[0].$$('.item');
      check('вопрос: 4 прилагательных', items.length === 4, `найдено ${items.length}`);
    }
    // ранжируем: первый item каждой карточки — вниз (3 клика ↓) => осмысленный профиль
    // DOM-клики со свежим запросом узла: приложение перерисовывает шаг после
    // каждого перемещения — puppeteer-хэндлы отрываются (Node is detached)
    for (let qi = 0; qi < qs.length; qi++) {
      const n = await page.$$eval('.question', els => els.length);
      if (qi >= n) break; // структура шага изменилась — не падаем
      for (let k = 0; k < 3; k++) {
        await page.evaluate(qi => {
          const q = document.querySelectorAll('.question')[qi];
          const btn = q?.querySelector('.item button[aria-label="Ниже"], .item button[aria-label*="ниж"]');
          btn?.click();
        }, qi);
        await sleep(120);
      }
    }
    if ([1, 4, 8].includes(step)) await shot(page, `step-${String(step).padStart(2, '0')}`);
    stepsSeen.push(await page.evaluate(() => document.getElementById('progressText')?.innerText || ''));
    // навигация туда-обратно на шаге 2: ответы должны сохраняться
    if (step === 2) {
      const before = await page.evaluate(() =>
        [...document.querySelectorAll('.item .item-text')].map(e => e.textContent));
      if (await page.$('#backBtn')) {
        await page.evaluate(() => document.getElementById('backBtn')?.click());
        await sleep(600);
        await page.evaluate(() => document.getElementById('nextBtn')?.click());
        await sleep(600);
        const after = await page.evaluate(() =>
          [...document.querySelectorAll('.item .item-text')].map(e => e.textContent));
        check('навигация назад/вперёд сохраняет ранжирование', JSON.stringify(before) === JSON.stringify(after));
      }
    }
    const hasNext = await page.evaluate(() => {
      const b = document.getElementById('nextBtn');
      return b && !b.disabled;
    });
    if (!hasNext) break;
    await page.evaluate(() => document.getElementById('nextBtn')?.click());
    await sleep(900);
    if (step < 8) {
      // email не должен показаться раньше времени
      const emailEarly = await page.$('#emailStep:not(.hidden)');
      if (step === 1) check('email не показывается до 8 шагов', !emailEarly);
    }
  }
  check('все 8 шагов пройдены', stepsSeen.length === 8, `пройдено ${stepsSeen.length}`);

  // --- 3. email
  await page.waitForSelector('#emailStep:not(.hidden), input[type="email"]', { timeout: 15000 });
  check('шаг email показан', true);
  await page.type('#email, input[type="email"]', email);
  await shot(page, 'email');
  await page.evaluate(() =>
    document.querySelector('#emailForm button[type="submit"], button[type="submit"]')?.click());

  // --- 4. результат + интерпретация (LLM может думать до ~2 минут)
  const started = Date.now();
  let interp = '';
  while (Date.now() - started < 180000) {
    await sleep(3000);
    interp = await page.evaluate(() =>
      document.getElementById('interpretationBlock')?.innerText || '').catch(() => '');
    const scoresVisible = await page.evaluate(() =>
      !!document.getElementById('resultStep') && !document.getElementById('resultStep').classList.contains('hidden'))
      .catch(() => false);
    if (scoresVisible && interp.trim().length > 100) break;
  }
  check('экран результата показан', !!(await page.$('#resultStep:not(.hidden), #scores')));
  check('интерпретация непустая (LLM ответил)', interp.trim().length > 100, `${interp.length} символов`);
  const htmlNow = await page.content();
  check('типы d/i/s/c не утекли в разметку', !/"type"\s*:\s*["'][disc]["']/.test(htmlNow));
  await sleep(500);
  await shot(page, 'result');

  // --- 5. ошибки консоли
  check('нет ошибок консоли браузера', consoleErrors.length === 0,
    consoleErrors.slice(0, 3).join(' | '));

} catch (e) {
  check('прохождение без исключений', false, String(e).slice(0, 200));
  await shot(page, 'error-state').catch(() => {});
}

await browser.close();
const pass = checks.every(c => c.ok);
const verdict = {
  url: baseUrl, viewport: mobile ? 'mobile-390' : 'desktop-1280',
  pass, checks,
  screenshots: fs.readdirSync(outDir).filter(f => f.endsWith('.png')),
  at: new Date().toISOString(),
};
fs.writeFileSync(jsonPath, JSON.stringify(verdict, null, 2));
console.log(`--- судья-браузер: ${checks.filter(c => c.ok).length}/${checks.length} ok, pass=${pass}`);
process.exit(pass ? 0 : 1);
