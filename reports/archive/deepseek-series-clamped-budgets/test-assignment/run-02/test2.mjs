import puppeteer from '/home/dp/.npm-global/lib/node_modules/puppeteer-core/lib/puppeteer/puppeteer-core.js';

const browser = await puppeteer.launch({ executablePath: '/usr/bin/google-chrome', headless: 'new', args: ['--no-sandbox'] });
const page = await browser.newPage();
const errors = [];
page.on('pageerror', e => errors.push('pageerror: ' + e.message));
page.on('console', m => { if (m.type() === 'error') errors.push('console: ' + m.text()); });
page.on('request', r => { if (!r.url().startsWith('file:')) errors.push('ext: ' + r.url()); });

const url = 'file://' + process.cwd() + '/index.html';

for (const vp of [{w:1440,h:1000},{w:1024,h:900},{w:768,h:900},{w:390,h:844},{w:320,h:700}]) {
  await page.setViewport({ width: vp.w, height: vp.h, isMobile: vp.w < 500, hasTouch: vp.w < 500 });
  await page.goto(url, { waitUntil: 'load' });
  const r = await page.evaluate(() => {
    const overflowEls = [];
    document.querySelectorAll('.item, .card, .btn, .result__score').forEach(el => {
      if (el.scrollWidth > el.clientWidth + 1) overflowEls.push(el.className + '|' + el.textContent.trim().slice(0, 28) + '|' + el.scrollWidth + '>' + el.clientWidth);
    });
    const cols = getComputedStyle(document.querySelector('.grid3')).gridTemplateColumns;
    const card = document.querySelector('.card').getBoundingClientRect();
    return {
      docScrollW: document.documentElement.scrollWidth,
      winW: window.innerWidth,
      cols: cols.split(' ').length + ':' + cols,
      cardW: Math.round(card.width),
      cardH: Math.round(card.height),
      overflowEls: overflowEls.slice(0, 6),
      tabH: Math.round(document.getElementById('tabs').getBoundingClientRect().height),
      btnRowH: Math.round(document.querySelector('.actions').getBoundingClientRect().height),
    };
  });
  console.log('VP', JSON.stringify(vp), JSON.stringify(r));
}

// --- touch: drag by handle should reorder ---
await page.setViewport({ width: 390, height: 844, isMobile: true, hasTouch: true });
await page.goto(url, { waitUntil: 'load' });
const h = await page.evaluate(() => {
  const ul = document.querySelectorAll('.list')[0];
  const a = ul.children[0].querySelector('.handle').getBoundingClientRect();
  const b = ul.children[3].getBoundingClientRect();
  return { sx: a.x + a.width/2, sy: a.y + a.height/2, ex: b.x + b.width/2, ey: b.bottom - 3, before: [...ul.children].map(li=>li.dataset.type).join('') };
});
const cdp = await page.createCDPSession();
const touch = (type, x, y) => cdp.send('Input.dispatchTouchEvent', { type, touchPoints: type === 'touchEnd' ? [] : [{ x, y, radiusX: 4, radiusY: 4, force: 1 }] });
await touch('touchStart', h.sx, h.sy);
for (let i = 1; i <= 10; i++) {
  await touch('touchMove', h.sx + (h.ex - h.sx) * i / 10, h.sy + (h.ey - h.sy) * i / 10);
  await new Promise(r => setTimeout(r, 16));
}
await touch('touchEnd', h.ex, h.ey);
await new Promise(r => setTimeout(r, 200));
const after = await page.evaluate(() => [...document.querySelectorAll('.list')[0].children].map(li => li.dataset.type).join(''));
console.log('TOUCH handle drag', h.before, '->', after);

// --- touch on item body should NOT reorder (only handle) ---
const h2 = await page.evaluate(() => {
  const ul = document.querySelectorAll('.list')[1];
  const a = ul.children[0].getBoundingClientRect();
  const b = ul.children[3].getBoundingClientRect();
  return { sx: a.x + 12, sy: a.y + a.height/2, ex: b.x + 12, ey: b.bottom - 3, before: [...ul.children].map(li=>li.dataset.type).join('') };
});
await touch('touchStart', h2.sx, h2.sy);
for (let i = 1; i <= 8; i++) { await touch('touchMove', h2.sx, h2.sy + (h2.ey - h2.sy) * i / 8); await new Promise(r => setTimeout(r, 16)); }
await touch('touchEnd', h2.ex, h2.ey);
await new Promise(r => setTimeout(r, 200));
const after2 = await page.evaluate(() => [...document.querySelectorAll('.list')[1].children].map(li => li.dataset.type).join(''));
console.log('TOUCH body drag', h2.before, '->', after2, '(unchanged expected)');

// result page layout on mobile
await page.setViewport({ width: 390, height: 844, isMobile: true, hasTouch: true });
await page.goto(url, { waitUntil: 'load' });
await page.click('[data-step-btn="7"]');
await page.click('#btnFinish');
await new Promise(r => setTimeout(r, 600));
const res = await page.evaluate(() => ({
  docScrollW: document.documentElement.scrollWidth, winW: window.innerWidth,
  scoreBox: (() => { const r = document.getElementById('scoreLine').getBoundingClientRect(); return [Math.round(r.width), Math.round(r.height)]; })(),
  gauges: [...document.querySelectorAll('.gauge')].map(g => Math.round(g.getBoundingClientRect().width)),
  text: document.getElementById('scoreLine').textContent,
}));
console.log('RESULT mobile', JSON.stringify(res));
await page.screenshot({ path: 'shot-result-mobile.png' });

console.log('ERRORS', JSON.stringify(errors));
await browser.close();
