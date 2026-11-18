import puppeteer from 'puppeteer-core';
import fs from 'fs';
import path from 'path';

const FIRSTLIST = '.pane.is-active .card:first-of-type .list .item';
const file = 'file://' + path.resolve('index.html');
const expected = JSON.parse(fs.readFileSync('questions.json', 'utf8'));

const browser = await puppeteer.launch({
  executablePath: '/usr/bin/google-chrome',
  headless: 'new',
  args: ['--no-sandbox', '--disable-dev-shm-usage', '--allow-file-access-from-files'],
  defaultViewport: { width: 1280, height: 900 },
});
const page = await browser.newPage();
const errors = [];
page.on('console', (m) => { if (m.type() === 'error' || m.type() === 'warning') errors.push(m.type() + ': ' + m.text()); });
page.on('pageerror', (e) => errors.push('pageerror: ' + e.message));
page.on('request', (r) => { if (!r.url().startsWith('file://') && !r.url().startsWith('data:')) errors.push('EXTERNAL REQUEST: ' + r.url()); });

await page.goto(file, { waitUntil: 'load' });
await page.screenshot({ path: 'shot-landing.png', fullPage: false });

// данные из DOM
const dom = await page.$$eval('#wizardmodal .list', (uls) => uls.map((ul) =>
  [...ul.children].map((li) => [li.getAttribute('data-type'), li.textContent.trim()])));
const flat = (arr) => JSON.stringify(arr.map((l) => l.map(([t, x]) => [t, x])));
const exp = expected.map((l) => l.items.map((i) => [i.type, i.text]));
console.log('lists:', dom.length, 'items per list:', dom.map((l) => l.length).join(','));
console.log('data exact match:', flat(dom) === flat(exp));
if (flat(dom) !== flat(exp)) {
  dom.forEach((l, i) => { if (JSON.stringify(l) !== JSON.stringify(exp[i])) console.log('DIFF list', i + 1, JSON.stringify(l), JSON.stringify(exp[i])); });
}

// открыть модалку
await page.click('.hero .btn--primary');
await new Promise((r) => setTimeout(r, 400));
console.log('modal open:', await page.$eval('#wizardmodal', (m) => m.classList.contains('is-open') && m.getAttribute('aria-hidden')));
console.log('visible panes:', await page.$$eval('.pane.is-active', (p) => p.length));
await page.screenshot({ path: 'shot-step1.png' });

// drag & drop: первый item первого списка вниз на позицию 4
const before = await page.$$eval(FIRSTLIST, (els) => els.map((e) => e.textContent.trim()));
const rects = await page.$$eval(FIRSTLIST, (els) => els.map((e) => { const r = e.getBoundingClientRect(); return { x: r.x + r.width / 2, y: r.y + r.height / 2, h: r.height }; }));
const src = rects[0];
const dst = rects[3];
await page.mouse.move(src.x, src.y);
await page.mouse.down();
for (let i = 1; i <= 12; i++) {
  await page.mouse.move(src.x, src.y + (dst.y + dst.h / 2 - src.y) * i / 12);
  await new Promise((r) => setTimeout(r, 20));
}
await page.mouse.up();
await new Promise((r) => setTimeout(r, 200));
const after = await page.$$eval(FIRSTLIST, (els) => els.map((e) => e.textContent.trim()));
console.log('drag before:', before);
console.log('drag after :', after);
console.log('drag moved white -> last:', before[0] === after[3] && new Set(after).size === 4);

// пройти все шаги
for (let i = 0; i < 7; i++) {
  await page.click('[data-next]');
  await new Promise((r) => setTimeout(r, 120));
}
console.log('step 8 active:', await page.$eval('.tab.is-active', (t) => t.textContent));
console.log('prev disabled:', await page.$eval('[data-prev]', (b) => b.disabled), 'next hidden:', await page.$eval('[data-next]', (b) => b.hidden), 'finish hidden:', await page.$eval('[data-finish]', (b) => b.hidden));
console.log('progress width:', await page.$eval('#discProgress', (p) => p.style.width));
await page.screenshot({ path: 'shot-step8.png' });

// ожидаемый счёт из DOM на момент завершения
const domScore = await page.$$eval('#wizardmodal .list', (uls) => {
  const maj = [], min = [];
  uls.forEach((ul) => { const it = [...ul.children]; maj.push(it[0].dataset.type); min.push(it[3].dataset.type); });
  const count = (a, t) => a.filter((x) => x === t).length;
  return { d: count(maj, 'd') - count(min, 'd'), i: count(maj, 'i') - count(min, 'i'), s: count(maj, 's') - count(min, 's'), c: count(maj, 'c') - count(min, 'c') };
});
await page.click('[data-finish]');
await new Promise((r) => setTimeout(r, 500));
const shown = await page.$eval('#resultScore', (e) => e.textContent);
const want = `D:${domScore.d}, I:${domScore.i}, S:${domScore.s}, C:${domScore.c}`;
console.log('score shown:', shown, '| expected:', want, '|', shown === want);
console.log('bars:', await page.$$eval('.bar', (b) => b.map((x) => x.querySelector('.bar__name').textContent + '=' + x.querySelector('.bar__value').textContent)));
console.log('wizard hidden:', await page.$eval('#wizard', (w) => w.hidden));
await page.screenshot({ path: 'shot-result.png', fullPage: false });

// перезапуск
await page.click('[data-restart]');
await new Promise((r) => setTimeout(r, 300));
const reset = await page.$$eval(FIRSTLIST, (els) => els.map((e) => e.textContent.trim()));
console.log('restart order restored:', JSON.stringify(reset) === JSON.stringify(before));

// клавиатура
await page.focus(FIRSTLIST);
await page.keyboard.press('ArrowDown');
console.log('keyboard reorder:', await page.$$eval(FIRSTLIST, (els) => els.map((e) => e.textContent.trim())));

// проверка вкладок
await page.click('[data-step="4"]');
console.log('tab jump pane:', await page.$$eval('.pane.is-active', (p) => p.map((x) => x.dataset.pane)));

// мобильный вьюпорт: drag за ручку
const m = await browser.newPage();
await m.setViewport({ width: 390, height: 844, isMobile: true, hasTouch: true });
const merr = [];
m.on('pageerror', (e) => merr.push(e.message));
await m.goto(file, { waitUntil: 'load' });
await m.click('.hero .btn--primary');
await new Promise((r) => setTimeout(r, 400));
await m.screenshot({ path: 'shot-mobile.png' });
const mrects = await m.$$eval(FIRSTLIST, (els) => els.map((e) => { const r = e.getBoundingClientRect(); return { x: r.x + 22, y: r.y + r.height / 2, h: r.height }; }));
const cdp = await m.createCDPSession();
await cdp.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [{ x: mrects[0].x, y: mrects[0].y }] });
for (let i = 1; i <= 12; i++) {
  await cdp.send('Input.dispatchTouchEvent', { type: 'touchMove', touchPoints: [{ x: mrects[0].x, y: mrects[0].y + (mrects[3].y + mrects[3].h / 2 - mrects[0].y) * i / 12 }] });
  await new Promise((r) => setTimeout(r, 20));
}
await cdp.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
await new Promise((r) => setTimeout(r, 200));
const mafter = await m.$$eval(FIRSTLIST, (els) => els.map((e) => e.textContent.trim()));
console.log('mobile touch drag:', JSON.stringify(mafter));
console.log('mobile errors:', merr);

console.log('console errors:', errors);
await browser.close();