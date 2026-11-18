import puppeteer from '/home/dp/MyProjects/disc/test-assignment/node_modules/puppeteer-core/lib/esm/puppeteer/puppeteer-core.js';

const browser = await puppeteer.launch({ executablePath: '/usr/bin/google-chrome', headless: 'new', args: ['--no-sandbox'] });
const page = await browser.newPage();
const errors = [];
page.on('pageerror', e => errors.push('pageerror: ' + e.message));
page.on('console', m => { if (m.type() === 'error') errors.push('console: ' + m.text()); });

await page.goto('file://' + process.cwd() + '/index.html', { waitUntil: 'load' });
await page.click('#btnStart');
await page.waitForSelector('.pane .item', { visible: true });

// walk steps 0..6 with Далее, on step 7 press finish
for (let i = 0; i < 7; i++) {
  const active = await page.$eval('.pane:not([hidden])', el => +el.dataset.stepPane);
  if (active !== i) throw new Error('step mismatch: expected ' + i + ' got ' + active);
  await page.click('#btnNext');
}
const active7 = await page.$eval('.pane:not([hidden])', el => +el.dataset.stepPane);
if (active7 !== 7) throw new Error('finish step mismatch ' + active7);

// reorder first list of step 1: move item 1 (Экспресcивный, i) to the end via keyboard
await page.click('[data-step-btn="0"]');
await page.evaluate(() => {
  const li = document.querySelector('.pane:not([hidden]) .item');
  li.focus();
  for (let k = 0; k < 3; k++) li.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowDown', bubbles: true }));
});
const order1 = await page.$$eval('.pane:not([hidden]) ul.plist:first-child .item', els => els.map(e => e.getAttribute('data-type')));

await page.click('[data-step-btn="7"]');
await page.click('#btnFinish');
await page.waitForSelector('#result:not([hidden])', { visible: true });
const shown = await page.evaluate(() => ({
  d: +document.querySelectorAll('.score__value')[0].textContent,
  i: +document.querySelectorAll('.score__value')[1].textContent,
  s: +document.querySelectorAll('.score__value')[2].textContent,
  c: +document.querySelectorAll('.score__value')[3].textContent,
}));

// expected: compute from DATA with list1 = [c,d,s,i]
const DATAsrc = await page.evaluate(() => null); // can't access DATA (IIFE) -> recompute from DOM initial order? use saved expected below
console.log('order1 now:', order1);
console.log('shown scores:', shown);
console.log('errors:', errors);
await page.screenshot({ path: 'shot-result.png' });
await page.screenshot({ path: 'shot-start.png', fullPage: true });
await browser.close();
