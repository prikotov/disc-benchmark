// Мобильный/сенсорный режим копии: pointer: coarse, перетаскивание только за «точечки», раскладка.
const puppeteer = require('/home/dp/.npm-global/lib/node_modules/puppeteer-core');
const path = require('path');
const fs = require('fs');

const FILE = 'file://' + path.resolve(__dirname, '..', 'index.html');
const OUT = path.resolve(__dirname, 'shots');
fs.mkdirSync(OUT, { recursive: true });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let failures = 0;
const check = (cond, msg) => { console.log(cond ? '  ok  ' : '  FAIL', msg); if (!cond) failures += 1; };

async function itemBox(page, s, c, i) {
  return page.evaluate((s, c, i) => {
    const li = document.querySelectorAll(`#pane-${s} .list`)[c].querySelectorAll(':scope > .item')[i];
    const r = li.getBoundingClientRect();
    const h = li.querySelector('.handle').getBoundingClientRect();
    return { x: r.left + 20, y: r.top + r.height / 2, hx: h.left + h.width / 2, hy: h.top + h.height / 2, h: r.height };
  }, s, c, i);
}
const texts = (page, s, c) => page.evaluate((s, c) => Array.from(document.querySelectorAll(`#pane-${s} .list`)[c]
  .querySelectorAll(':scope > .item')).map((li) => li.firstChild.textContent), s, c);

(async () => {
  const browser = await puppeteer.launch({
    executablePath: '/usr/bin/google-chrome', headless: true,
    args: ['--no-sandbox', '--disable-gpu', '--no-proxy-server'],
  });
  const page = await browser.newPage();
  await page.setViewport({ width: 390, height: 844, deviceScaleFactor: 2, isMobile: true, hasTouch: true });
  const errors = [];
  page.on('pageerror', (e) => errors.push(e.message));
  await page.goto(FILE, { waitUntil: 'load' });

  console.log('[m1] старт на телефоне');
  const coarse = await page.evaluate(() => matchMedia('(pointer: coarse)').matches);
  check(coarse, 'эмуляция сенсорного указателя (pointer: coarse) активна');
  await page.screenshot({ path: path.join(OUT, 'm01-start.png') });

  console.log('[m2] тест на телефоне');
  await page.tap('#openTest');
  await sleep(200);
  const tabsOverflow = await page.$eval('#tabs', (t) => t.scrollWidth > t.clientWidth);
  check(tabsOverflow, 'вкладки шагов прокручиваются по горизонтали');
  const bodyScroll = await page.$eval('#dialogBody', (b) => b.scrollHeight > b.clientHeight);
  check(bodyScroll, 'содержимое шага прокручивается внутри окна');
  const footVisible = await page.$eval('.modal__foot', (f) => {
    const r = f.getBoundingClientRect();
    return r.bottom <= window.innerHeight + 1 && r.top >= 0;
  });
  check(footVisible, 'нижняя панель с кнопками видна на экране');
  const dialogFits = await page.$eval('.modal__dialog', (d) => {
    const r = d.getBoundingClientRect();
    return r.top >= -1 && r.bottom <= window.innerHeight + 1;
  });
  check(dialogFits, 'окно теста помещается в высоту экрана');
  await page.screenshot({ path: path.join(OUT, 'm02-step1.png') });

  console.log('[m3] перетаскивание за текст не работает на сенсорном устройстве');
  const before = await texts(page, 0, 0);
  const b0 = await itemBox(page, 0, 0, 0);
  const b3 = await itemBox(page, 0, 0, 3);
  await page.mouse.move(b0.x, b0.y);
  await page.mouse.down();
  for (let k = 1; k <= 10; k++) { await page.mouse.move(b0.x, b0.y + ((b3.y + 20 - b0.y) * k) / 10); await sleep(16); }
  await page.mouse.up();
  await sleep(200);
  check(JSON.stringify(await texts(page, 0, 0)) === JSON.stringify(before), 'перетаскивание за текст варианта не начинается');

  console.log('[m4] касание за «точечки» переставляет вариант');
  const h0 = await itemBox(page, 0, 0, 0);
  const h3 = await itemBox(page, 0, 0, 3);
  await page.touchscreen.touchStart(h0.hx, h0.hy);
  for (let k = 1; k <= 14; k++) {
    await page.touchscreen.touchMove(h0.hx, h0.hy + ((h3.y + 25 - h0.hy) * k) / 14);
    await sleep(20);
  }
  await page.touchscreen.touchEnd();
  await sleep(250);
  const after = await texts(page, 0, 0);
  check(JSON.stringify(after) === JSON.stringify(['Покладистый', 'Волевой', 'Осторожный', 'Экспресcивный']),
    `касание за точечки перенесло вариант вниз: ${JSON.stringify(after)}`);
  check(await page.$$eval('.item.is-ghost', (n) => n.length) === 0, 'призрак удалён после касания');
  await page.screenshot({ path: path.join(OUT, 'm03-after-touch-drag.png') });

  console.log('[m5] шаги и итог на телефоне');
  await page.tap('[data-step="7"]');
  await sleep(300);
  check(await page.$eval('#finishBtn', (b) => !b.hidden), 'на последнем шаге видна «Завершить тест»');
  await page.screenshot({ path: path.join(OUT, 'm04-step8.png') });
  await page.tap('#finishBtn');
  await sleep(200);
  check(await page.$eval('#result', (n) => !n.hidden), 'итог показан на телефоне');
  await page.screenshot({ path: path.join(OUT, 'm05-result.png'), fullPage: true });

  check(errors.length === 0, `ошибок JS: ${errors.length} ${errors.join(' | ')}`);
  await browser.close();
  console.log(failures ? `\nИТОГ: ${failures} не прошли` : '\nИТОГ: все проверки прошли');
  process.exit(failures ? 1 : 0);
})().catch((e) => { console.error(e); process.exit(2); });
