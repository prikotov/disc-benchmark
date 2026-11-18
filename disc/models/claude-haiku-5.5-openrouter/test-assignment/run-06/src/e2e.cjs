// Сквозная проверка копии index.html в headless Chrome (file://).
const puppeteer = require('/home/dp/.npm-global/lib/node_modules/puppeteer-core');
const path = require('path');
const fs = require('fs');

const FILE = 'file://' + path.resolve(__dirname, '..', 'index.html');
const DATA = JSON.parse(fs.readFileSync(path.resolve(__dirname, 'data.json'), 'utf8'));
const OUT = path.resolve(__dirname, 'shots');
fs.mkdirSync(OUT, { recursive: true });

let failures = 0;
const check = (cond, msg) => {
  if (cond) console.log('  ok  ', msg);
  else { failures += 1; console.log('  FAIL', msg); }
};
const fmt = (s) => `D:${s.d}, I:${s.i}, S:${s.s}, C:${s.c}`;
const expectScore = (orders) => {
  const s = { d: 0, i: 0, s: 0, c: 0 };
  orders.forEach((o) => { s[o[0]] += 1; s[o[o.length - 1]] -= 1; });
  return s;
};

async function domOrders(page) {
  return page.evaluate(() => Array.from(document.querySelectorAll('#panes .list'))
    .map((ul) => Array.from(ul.querySelectorAll(':scope > .item')).map((li) => li.dataset.type)));
}
async function domTexts(page, stepIdx, cardIdx) {
  return page.evaluate((s, c) => Array.from(document.querySelectorAll(`#pane-${s} .list`)[c]
    .querySelectorAll(':scope > .item')).map((li) => li.firstChild.textContent), stepIdx, cardIdx);
}
async function itemBox(page, stepIdx, cardIdx, itemIdx) {
  return page.evaluate((s, c, i) => {
    const li = document.querySelectorAll(`#pane-${s} .list`)[c].querySelectorAll(':scope > .item')[i];
    const r = li.getBoundingClientRect();
    const h = li.querySelector('.handle').getBoundingClientRect();
    return { x: r.left + r.width / 2, y: r.top + r.height / 2, hx: h.left + h.width / 2, hy: h.top + h.height / 2, w: r.width, h: r.height };
  }, stepIdx, cardIdx, itemIdx);
}
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function dragMouse(page, from, toY, { viaHandle = false } = {}) {
  const sx = viaHandle ? from.hx : from.x;
  const sy = viaHandle ? from.hy : from.y;
  await page.mouse.move(sx, sy);
  await page.mouse.down();
  const steps = 12;
  for (let k = 1; k <= steps; k++) {
    await page.mouse.move(sx, sy + ((toY - sy) * k) / steps);
    await sleep(16);
  }
  await sleep(200);
  await page.mouse.up();
  await sleep(250);
}

(async () => {
  const browser = await puppeteer.launch({
    executablePath: '/usr/bin/google-chrome',
    headless: true,
    args: ['--no-sandbox', '--disable-gpu', '--allow-file-access-from-files'],
    defaultViewport: { width: 1440, height: 900 },
  });
  const page = await browser.newPage();
  const requests = [];
  const errors = [];
  page.on('request', (r) => requests.push(r.url()));
  page.on('console', (m) => { if (m.type() === 'error' || m.type() === 'warning') errors.push(m.text()); });
  page.on('pageerror', (e) => errors.push('pageerror: ' + e.message));

  await page.goto(FILE, { waitUntil: 'load' });

  console.log('\n[1] стартовый экран');
  check(await page.$eval('#start', (n) => !n.hidden), 'старт виден');
  check(await page.$eval('#result', (n) => n.hidden), 'результат скрыт');
  check(await page.$eval('#testDialog', (n) => n.hidden), 'диалог скрыт');
  await page.screenshot({ path: path.join(OUT, '01-start.png') });

  console.log('\n[2] открытие теста и структура');
  await page.click('#openTest');
  await sleep(150);
  check(await page.$eval('#testDialog', (n) => !n.hidden), 'диалог открыт');
  const paneCount = await page.$$eval('#panes .pane', (n) => n.length);
  check(paneCount === 8, `панелей шагов: ${paneCount}`);
  const cardsPerPane = await page.$$eval('#panes .pane', (ps) => ps.map((p) => p.querySelectorAll('.card').length));
  check(cardsPerPane.every((n) => n === 3), 'в каждом шаге 3 набора');
  const itemsPerCard = await page.$$eval('#panes .list', (ls) => ls.map((l) => l.children.length));
  check(itemsPerCard.length === 24 && itemsPerCard.every((n) => n === 4), '24 набора по 4 варианта');
  const initial = await domOrders(page);
  const expectInit = DATA.map((cards) => cards.map((items) => items.map(([t]) => t))).flat();
  check(JSON.stringify(initial) === JSON.stringify(expectInit), 'исходный порядок типов совпадает с оригиналом');
  const texts0 = await domTexts(page, 0, 0);
  check(JSON.stringify(texts0) === JSON.stringify(DATA[0][0].map(([, t]) => t)), 'тексты первого набора совпадают');
  check(await page.$eval('#pane-0', (p) => !p.hidden), 'активен первый шаг');
  check(await page.$eval('#prevBtn', (b) => b.disabled), 'кнопка «Назад» отключена на первом шаге');
  check(await page.$eval('#finishBtn', (b) => b.hidden), 'кнопка «Завершить» скрыта на первом шаге');
  check((await page.$eval('#progressBar', (b) => b.style.width)) === '12.5%', 'прогресс 12.5% на первом шаге');
  await page.screenshot({ path: path.join(OUT, '02-step1.png') });

  console.log('\n[3] перетаскивание мышью (за весь вариант)');
  let box = await itemBox(page, 0, 0, 0);
  // вниз, за нижний вариант набора
  const lastBox = await itemBox(page, 0, 0, 3);
  await dragMouse(page, box, lastBox.y + 10);
  let t = await domTexts(page, 0, 0);
  check(JSON.stringify(t) === JSON.stringify(['Покладистый', 'Волевой', 'Осторожный', 'Экспресcивный']),
    `перенос первого варианта вниз: ${JSON.stringify(t)}`);
  check(await page.$$eval('.item.is-ghost', (n) => n.length) === 0, 'призрак удалён после отпускания');
  check(await page.$$eval('.item.is-over', (n) => n.length) === 0, 'подсветка места сброшена');
  // обычный клик без движения не меняет порядок
  box = await itemBox(page, 0, 0, 1);
  await page.mouse.click(box.x, box.y);
  await sleep(100);
  t = await domTexts(page, 0, 0);
  check(JSON.stringify(t) === JSON.stringify(['Покладистый', 'Волевой', 'Осторожный', 'Экспресcивный']), 'клик без движения не переставляет');
  // вверх, за верхний вариант (последний вариант -> верх)
  box = await itemBox(page, 0, 0, 3);
  const firstBox = await itemBox(page, 0, 0, 0);
  await dragMouse(page, box, firstBox.y - 6);
  t = await domTexts(page, 0, 0);
  check(JSON.stringify(t) === JSON.stringify(['Экспресcивный', 'Покладистый', 'Волевой', 'Осторожный']),
    `перенос последнего варианта вверх: ${JSON.stringify(t)}`);
  // перетаскивание не затрагивает соседние наборы
  const other = await domTexts(page, 0, 1);
  check(JSON.stringify(other) === JSON.stringify(DATA[0][1].map(([, x]) => x)), 'соседний набор не изменился');

  console.log('\n[4] клавиатура: стрелки переставляют вариант');
  // состояние перед блоком: ['Экспресcивный','Покладистый','Волевой','Осторожный']
  await page.evaluate(() => document.querySelectorAll('#pane-0 .list')[0].children[2].focus());
  await page.keyboard.press('ArrowUp');
  await sleep(200);
  t = await domTexts(page, 0, 0);
  check(JSON.stringify(t) === JSON.stringify(['Экспресcивный', 'Волевой', 'Покладистый', 'Осторожный']),
    `ArrowUp переставил вариант вверх: ${JSON.stringify(t)}`);
  let focusedText = await page.evaluate(() => document.activeElement && document.activeElement.firstChild.textContent);
  check(focusedText === 'Волевой', 'фокус остался на переставленном варианте');
  await page.keyboard.press('ArrowDown');
  await sleep(200);
  t = await domTexts(page, 0, 0);
  check(JSON.stringify(t) === JSON.stringify(['Экспресcивный', 'Покладистый', 'Волевой', 'Осторожный']),
    `ArrowDown вернул: ${JSON.stringify(t)}`);
  await page.evaluate(() => document.querySelectorAll('#pane-0 .list')[0].children[0].focus());
  await page.keyboard.press('ArrowUp');
  await sleep(100);
  t = await domTexts(page, 0, 0);
  check(JSON.stringify(t) === JSON.stringify(['Экспресcивный', 'Покладистый', 'Волевой', 'Осторожный']),
    'ArrowUp у первого варианта ничего не меняет');

  console.log('\n[5] навигация по шагам');
  await page.click('#nextBtn');
  await sleep(50);
  check(await page.$eval('#pane-1', (p) => !p.hidden), 'Далее -> второй шаг');
  check(await page.$eval('#prevBtn', (b) => !b.disabled), '«Назад» доступна со второго шага');
  await page.click('[data-step="4"]');
  await sleep(50);
  check(await page.$eval('#pane-4', (p) => !p.hidden), 'клик по вкладке «Пятый» переходит на шаг 5');
  check(await page.$eval('#pane-1', (p) => p.hidden), 'предыдущий шаг скрыт');
  await page.click('#prevBtn');
  await sleep(50);
  check(await page.$eval('#pane-3', (p) => !p.hidden), 'Назад -> четвёртый шаг');
  await page.click('[data-step="7"]');
  await sleep(50);
  check(await page.$eval('#nextBtn', (b) => b.hidden), 'на последнем шаге «Далее» скрыта');
  check(await page.$eval('#finishBtn', (b) => !b.hidden), 'на последнем шаге видна «Завершить тест»');
  check((await page.$eval('#progressBar', (b) => b.style.width)) === '100%', 'прогресс 100% на последнем шаге');
  await page.screenshot({ path: path.join(OUT, '03-step8.png') });

  console.log('\n[6] закрытие, Esc и повторное открытие сохраняет порядок');
  await page.keyboard.press('Escape');
  await sleep(50);
  check(await page.$eval('#testDialog', (n) => n.hidden), 'Esc закрывает диалог');
  check(await page.$eval('#start', (n) => !n.hidden), 'стартовый экран после закрытия');
  await page.click('#openTest');
  await sleep(50);
  t = await domTexts(page, 0, 0);
  check(JSON.stringify(t) === JSON.stringify(['Экспресcивный', 'Покладистый', 'Волевой', 'Осторожный']), `порядок после повторного открытия: ${JSON.stringify(t)}`);
  await page.click('#closeBtn');
  await sleep(50);
  check(await page.$eval('#testDialog', (n) => n.hidden), 'крестик закрывает диалог');
  await page.click('#openTest');
  await sleep(50);
  await page.click('#overlay', { offset: { x: 10, y: 10 } }).catch(() => {});
  await sleep(50);
  check(await page.$eval('#testDialog', (n) => n.hidden), 'клик по подложке закрывает диалог');

  console.log('\n[7] полный проход, подсчёт и результат в приложении');
  // Детерминированный порядок: в каждом наборе переставим варианты по схеме, отличной от исходной
  const plan = [];
  await page.click('#openTest');
  await sleep(50);
  for (let s = 0; s < 8; s++) {
    await page.click(`[data-step="${s}"]`);
    await sleep(20);
    for (let c = 0; c < 3; c++) {
      const r = (s * 3 + c) % 4; // сдвиг
      await page.evaluate((stepIdx, cardIdx, rot) => {
        const ul = document.querySelectorAll(`#pane-${stepIdx} .list`)[cardIdx];
        const items = Array.from(ul.children);
        const rotated = items.slice(rot).concat(items.slice(0, rot));
        rotated.forEach((li) => ul.appendChild(li));
      }, s, c, r);
    }
  }
  const orders = await domOrders(page);
  const expected = expectScore(orders);
  await page.click('[data-step="7"]');
  await sleep(30);
  await page.click('#finishBtn');
  await sleep(200);
  check(await page.$eval('#testDialog', (n) => n.hidden), 'после «Завершить» диалог закрыт');
  check(await page.$eval('#result', (n) => !n.hidden), 'результат показан в приложении');
  check(await page.$eval('#start', (n) => n.hidden), 'стартовый экран скрыт');
  const shown = await page.$eval('#scoreText', (n) => n.textContent);
  check(shown === fmt(expected), `баллы: ${shown} (ожидалось ${fmt(expected)})`);
  check((await page.$$eval('#bars .bar', (n) => n.length)) === 4, 'четыре строки с баллами');
  await page.screenshot({ path: path.join(OUT, '04-result.png') });

  console.log('\n[8] перезапуск');
  await page.click('#restartBtn');
  await sleep(100);
  check(await page.$eval('#testDialog', (n) => !n.hidden), 'перезапуск открывает тест');
  check(await page.$eval('#pane-0', (p) => !p.hidden), 'перезапуск: первый шаг');
  check(JSON.stringify(await domOrders(page)) === JSON.stringify(expectInit), 'перезапуск: исходный порядок восстановлен');
  check(await page.$eval('#result', (n) => n.hidden), 'результат скрыт после перезапуска');
  await page.keyboard.press('Escape');

  console.log('\n[9] сеть и ошибки');
  const external = requests.filter((u) => !u.startsWith('file:'));
  check(external.length === 0, `внешних запросов: ${external.length} ${external.slice(0, 3).join(' ')}`);
  check(errors.length === 0, `ошибок в консоли: ${errors.length} ${errors.slice(0, 3).join(' | ')}`);

  await browser.close();
  console.log(`\nИТОГ: ${failures === 0 ? 'все проверки прошли' : failures + ' проверок не прошли'}`);
  process.exit(failures ? 1 : 0);
})().catch((e) => { console.error(e); process.exit(2); });
