const puppeteer = require('puppeteer-core');
const path = require('path');

const CHROME = '/usr/bin/google-chrome';
const FILE = 'file://' + path.resolve(__dirname, '..', 'index.html');

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

(async () => {
  const browser = await puppeteer.launch({
    executablePath: CHROME,
    headless: 'new',
    args: ['--no-sandbox', '--disable-dev-shm-usage', '--window-size=1440,1000'],
    defaultViewport: { width: 1440, height: 1000 },
  });
  const page = await browser.newPage();

  const errors = [];
  const externalRequests = [];
  page.on('console', (m) => { if (m.type() === 'error') errors.push('console: ' + m.text()); });
  page.on('pageerror', (e) => errors.push('pageerror: ' + e.message));
  page.on('request', (r) => { if (!r.url().startsWith('file://') && !r.url().startsWith('data:')) externalRequests.push(r.url()); });

  await page.goto(FILE, { waitUntil: 'load' });
  await sleep(300);
  await page.screenshot({ path: 'shot-start.png' });

  // --- структура
  const checks = await page.evaluate(() => {
    const q = (s) => document.querySelector(s);
    const qa = (s) => [...document.querySelectorAll(s)];
    return {
      tabs: qa('.disc-tab').length,
      panes: qa('.disc-pane').length,
      lists: qa('.disc-list').length,
      items: qa('.disc-item').length,
      handles: qa('.disc-handle').length,
      modalHidden: getComputedStyle(q('#wizardmodal')).display === 'none',
      progressWidth: q('#discProgress').style.width,
      resultHidden: q('#resultview').hidden,
    };
  });
  console.log('STRUCTURE', JSON.stringify(checks));

  // --- открыть модалку
  await page.click('[data-modal-open="wizardmodal"]');
  await sleep(200);
  const opened = await page.evaluate(() => document.querySelector('#wizardmodal').classList.contains('is-open'));
  console.log('OPENED', opened);
  await page.screenshot({ path: 'shot-step1.png' });

  // --- drag&drop: перетащить 1-й пункт 1-го списка на позицию 3 (вниз)
  const beforeOrder = await page.evaluate(() =>
    [...document.querySelectorAll('#draggable-list1 .disc-item')].map((li) => li.dataset.type + ':' + li.textContent.trim().slice(0, 8))
  );
  const box = await page.evaluate(() => {
    const li = document.querySelector('#draggable-list1 .disc-item');
    const r = li.getBoundingClientRect();
    return { x: r.left + r.width / 2, y: r.top + r.height / 2, h: r.height };
  });
  await page.mouse.move(box.x, box.y);
  await page.mouse.down();
  // двигаем вниз с шагами (события pointermove должны стрелять)
  for (let i = 1; i <= 8; i++) {
    await page.mouse.move(box.x, box.y + (box.h * 3.4 * i) / 8, { steps: 3 });
    await sleep(30);
  }
  await page.mouse.up();
  await sleep(300);
  const afterOrder = await page.evaluate(() =>
    [...document.querySelectorAll('#draggable-list1 .disc-item')].map((li) => li.dataset.type + ':' + li.textContent.trim().slice(0, 8))
  );
  console.log('DRAG', JSON.stringify({ before: beforeOrder, after: afterOrder, changed: JSON.stringify(beforeOrder) !== JSON.stringify(afterOrder) }));

  // --- пройти тест: на каждом шаге немного перетасуем 1-й список (кроме шага 1 — там уже перетасовали), далее
  for (let step = 1; step < 8; step++) {
    // двигаем первый пункт первого списка вниз на 1 позицию — проверяемый паттерн
    const b = await page.evaluate(() => {
      const lis = [...document.querySelectorAll('.disc-pane.is-active .disc-list')];
      const li = lis[0].querySelector('.disc-item');
      const r = li.getBoundingClientRect();
      return { x: r.left + r.width / 2, y: r.top + r.height / 2, h: r.height, n: lis[0].children.length };
    });
    await page.mouse.move(b.x, b.y);
    await page.mouse.down();
    for (let i = 1; i <= 6; i++) {
      await page.mouse.move(b.x, b.y + (b.h * 1.5 * i) / 6, { steps: 3 });
      await sleep(25);
    }
    await page.mouse.up();
    await sleep(200);
    await page.click('[data-disc-next]');
    await sleep(250);
  }

  // на 8-м шаге: перетащим 1-й пункт 1-го списка на самое дно
  const b8 = await page.evaluate(() => {
    const lis = [...document.querySelectorAll('.disc-pane.is-active .disc-list')];
    const li = lis[0].querySelector('.disc-item');
    const r = li.getBoundingClientRect();
    return { x: r.left + r.width / 2, y: r.top + r.height / 2, h: r.height };
  });
  await page.mouse.move(b8.x, b8.y);
  await page.mouse.down();
  for (let i = 1; i <= 8; i++) {
    await page.mouse.move(b8.x, b8.y + (b8.h * 3.4 * i) / 8, { steps: 3 });
    await sleep(30);
  }
  await page.mouse.up();
  await sleep(300);
  await page.screenshot({ path: 'shot-step8.png' });

  // --- финальный порядок DOM -> ожидаемый счёт (считаем по DOM до клика)
  const expected = await page.evaluate(() => {
    const maj = [], min = [];
    document.querySelectorAll('.disc-list').forEach((ul) => {
      const lis = [...ul.querySelectorAll('.disc-item')];
      maj.push(lis[0].dataset.type);
      min.push(lis[lis.length - 1].dataset.type);
    });
    const c = (a, t) => a.filter((x) => x === t).length;
    const s = (t) => c(maj, t) - c(min, t);
    return { d: s('d'), i: s('i'), s: s('s'), c: s('c') };
  });
  const expStr = `D:${expected.d}, I:${expected.i}, S:${expected.s}, C:${expected.c}`;
  console.log('EXPECTED_SCORE', expStr);

  // --- завершить
  await page.click('[data-disc-finish]');
  await sleep(600);
  const result = await page.evaluate(() => {
    const rv = document.querySelector('#resultview');
    return {
      visible: !rv.hidden,
      scoreline: document.querySelector('#scoreline').textContent,
      chips: {
        d: document.querySelector('#chipd').textContent,
        i: document.querySelector('#chipi').textContent,
        s: document.querySelector('#chips').textContent,
        c: document.querySelector('#chipc').textContent,
      },
      modalClosed: !document.querySelector('#wizardmodal').classList.contains('is-open'),
      scrollUnlocked: !document.documentElement.classList.contains('no-scroll'),
    };
  });
  console.log('RESULT', JSON.stringify(result));
  console.log('SCORE_MATCH', result.scoreline === expStr);
  await sleep(500);
  await page.screenshot({ path: 'shot-result.png' });

  // --- ещё раз: сброс
  await page.click('#restartBtn');
  await sleep(400);
  const restart = await page.evaluate(() => {
    const first = [...document.querySelectorAll('#draggable-list1 .disc-item')].map((li) => li.dataset.type);
    return {
      modalOpen: document.querySelector('#wizardmodal').classList.contains('is-open'),
      step: document.querySelector('#rootwizard').dataset.step,
      list1: first.join(''),
      progress: document.querySelector('#discProgress').style.width,
      resultHidden: document.querySelector('#resultview').hidden,
    };
  });
  console.log('RESTART', JSON.stringify(restart));

  // --- Esc закрывает
  await page.keyboard.press('Escape');
  await sleep(200);
  const escClosed = await page.evaluate(() => !document.querySelector('#wizardmodal').classList.contains('is-open'));
  console.log('ESC_CLOSED', escClosed);

  console.log('ERRORS', JSON.stringify(errors));
  console.log('EXTERNAL_REQUESTS', JSON.stringify(externalRequests));

  await browser.close();
})().catch((e) => { console.error('FATAL', e); process.exit(1); });
