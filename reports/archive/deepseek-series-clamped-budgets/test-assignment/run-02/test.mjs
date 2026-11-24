import puppeteer from '/home/dp/.npm-global/lib/node_modules/puppeteer-core/lib/puppeteer/puppeteer-core.js';

const browser = await puppeteer.launch({
  executablePath: '/usr/bin/google-chrome',
  headless: 'new',
  args: ['--no-sandbox', '--disable-dev-shm-usage', '--window-size=1440,1100'],
});
const page = await browser.newPage();
await page.setViewport({ width: 1440, height: 1000, deviceScaleFactor: 1 });

const errors = [];
page.on('pageerror', e => errors.push('pageerror: ' + e.message));
page.on('console', m => { if (m.type() === 'error') errors.push('console: ' + m.text()); });
page.on('request', r => { if (!r.url().startsWith('file:')) errors.push('external request: ' + r.url()); });

await page.goto('file://' + process.cwd() + '/index.html', { waitUntil: 'load' });

const info = await page.evaluate(() => {
  const lists = [...document.querySelectorAll('.list')];
  return {
    lists: lists.length,
    items: lists.map(l => l.children.length),
    itemsTotal: document.querySelectorAll('.item').length,
    handles: document.querySelectorAll('.handle').length,
    nums: document.querySelectorAll('.item__num').length,
    types: lists.map(l => [...l.children].map(li => li.dataset.type).join('')),
    firstOrder: [...lists[0].children].map(li => li.textContent.replace(/\s+/g,' ').trim()),
    progress: document.getElementById('progressBar').style.width,
    prevDisabled: document.getElementById('btnPrev').disabled,
    nextHidden: document.getElementById('btnNext').hidden,
    finishHidden: document.getElementById('btnFinish').hidden,
    stepLabel: document.getElementById('stepLabel').textContent,
  };
});
console.log('INFO', JSON.stringify(info, null, 1));

await page.screenshot({ path: 'shot-start.png', fullPage: false });

// ---- drag first item of list 0 to the bottom ----
const box = await page.evaluate(() => {
  const ul = document.querySelectorAll('.list')[0];
  const first = ul.children[0].getBoundingClientRect();
  const last = ul.children[3].getBoundingClientRect();
  return { sx: first.x + first.width/2, sy: first.y + first.height/2, ex: last.x + last.width/2, ey: last.y + last.height - 4 };
});
await page.mouse.move(box.sx, box.sy);
await page.mouse.down();
await page.mouse.move(box.sx, box.sy + 12, { steps: 4 });
await page.mouse.move(box.ex, box.ey, { steps: 12 });
await page.mouse.up();
const order0 = await page.evaluate(() => [...document.querySelectorAll('.list')[0].children].map(li => li.dataset.type).join(''));
console.log('ORDER after drag', order0);
await page.screenshot({ path: 'shot-drag.png' });

// ---- keyboard reorder: focus handle of list 1 item 2, ArrowUp ----
const kb = await page.evaluate(() => {
  const ul = document.querySelectorAll('.list')[1];
  const h = ul.children[1].querySelector('.handle');
  h.focus();
  return [...ul.children].map(li => li.dataset.type).join('');
});
await page.keyboard.press('ArrowUp');
const kb2 = await page.evaluate(() => [...document.querySelectorAll('.list')[1].children].map(li => li.dataset.type).join(''));
console.log('KEYBOARD', kb, '->', kb2);

// ---- walk through all steps ----
for (let i = 0; i < 7; i++) {
  await page.click('#btnNext');
  const st = await page.evaluate(() => ({
    step: document.querySelector('.tab.is-active').textContent,
    w: document.getElementById('progressBar').style.width,
    activePane: document.querySelector('.pane.is-active').dataset.stepPane,
    nextHidden: document.getElementById('btnNext').hidden,
    finishHidden: document.getElementById('btnFinish').hidden,
    label: document.getElementById('stepLabel').textContent,
  }));
  console.log('STEP', i + 1, JSON.stringify(st));
  if (i === 3) await page.screenshot({ path: 'shot-mid.png' });
}
await page.screenshot({ path: 'shot-last.png' });

// jump back via tab
await page.click('[data-step-btn="2"]');
console.log('JUMP', await page.evaluate(() => document.querySelector('.tab.is-active').textContent));

await page.click('[data-step-btn="7"]');
await page.click('#btnFinish');
await new Promise(r => setTimeout(r, 500));

const res = await page.evaluate(() => {
  const order = [...document.querySelectorAll('.list')].map(l => [...l.children].map(li => li.dataset.type));
  const maj = order.map(o => o[0]), min = order.map(o => o[3]);
  const c = (a, ch) => a.filter(v => v === ch).length;
  const exp = {};
  for (const t of 'disc') exp[t] = c(maj, t) - c(min, t);
  return {
    text: document.getElementById('scoreLine').textContent,
    expected: Object.entries(exp).map(([k, v]) => k.toUpperCase() + ':' + v).join(', '),
    resultVisible: !document.getElementById('result').hidden,
    wizardHidden: document.getElementById('wizard').hidden,
    gauges: [...document.querySelectorAll('.gauge')].map(g => g.dataset.gauge + '=' + g.querySelector('.gauge__value').textContent + ' w:' + g.querySelector('.gauge__fill').style.width + ' l:' + g.querySelector('.gauge__fill').style.left),
  };
});
console.log('RESULT', JSON.stringify(res, null, 1));
await page.screenshot({ path: 'shot-result.png' });

// restart
await page.click('#btnRestart');
const restarted = await page.evaluate(() => ({
  wizardVisible: !document.getElementById('wizard').hidden,
  resultHidden: document.getElementById('result').hidden,
  step: document.querySelector('.tab.is-active').textContent,
  firstOrder: [...document.querySelectorAll('.list')[0].children].map(li => li.dataset.type).join(''),
  progress: document.getElementById('progressBar').style.width,
}));
console.log('RESTART', JSON.stringify(restarted));

// mobile viewport
await page.setViewport({ width: 390, height: 844, deviceScaleFactor: 2, isMobile: true, hasTouch: true });
await new Promise(r => setTimeout(r, 300));
await page.screenshot({ path: 'shot-mobile.png' });
const mobile = await page.evaluate(() => {
  const tabsEl = document.getElementById('tabs');
  const cs = getComputedStyle(tabsEl);
  return { overflow: cs.overflowX, docScrollW: document.documentElement.scrollWidth, winW: window.innerWidth, cols: getComputedStyle(document.querySelector('.grid3')).gridTemplateColumns };
});
console.log('MOBILE', JSON.stringify(mobile));

console.log('ERRORS', JSON.stringify(errors, null, 1));
await browser.close();
