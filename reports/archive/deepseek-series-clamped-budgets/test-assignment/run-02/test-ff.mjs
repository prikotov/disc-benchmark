import puppeteer from '/home/dp/.npm-global/lib/node_modules/puppeteer-core/lib/puppeteer/puppeteer-core.js';
let browser;
try {
  browser = await puppeteer.launch({ browser: 'firefox', executablePath: '/usr/bin/firefox', headless: true });
} catch (e) { console.log('LAUNCH FAIL', e.message); process.exit(0); }
const page = await browser.newPage();
const errors = [];
page.on('pageerror', e => errors.push('pageerror: ' + e.message));
page.on('console', m => { if (m.type() === 'error') errors.push('console: ' + m.text()); });
await page.setViewport({ width: 1280, height: 900 });
await page.goto('file://' + process.cwd() + '/index.html', { waitUntil: 'load' });
const info = await page.evaluate(() => ({
  lists: document.querySelectorAll('.list').length,
  items: document.querySelectorAll('.item').length,
  handles: document.querySelectorAll('.handle').length,
  progress: document.getElementById('progressBar').style.width,
  supportsPointer: typeof window.PointerEvent === 'function',
}));
console.log('INFO', JSON.stringify(info));
const box = await page.evaluate(() => {
  const ul = document.querySelectorAll('.list')[0];
  const a = ul.children[0].getBoundingClientRect();
  const b = ul.children[3].getBoundingClientRect();
  return { sx: a.x + a.width/2, sy: a.y + a.height/2, ex: b.x + b.width/2, ey: b.bottom - 3 };
});
await page.mouse.move(box.sx, box.sy);
await page.mouse.down();
await page.mouse.move(box.sx, box.sy + 14, { steps: 3 });
await page.mouse.move(box.ex, box.ey, { steps: 10 });
await page.mouse.up();
console.log('ORDER', await page.evaluate(() => [...document.querySelectorAll('.list')[0].children].map(li => li.dataset.type).join('')));
await page.click('[data-step-btn="7"]');
await page.click('#btnFinish');
await new Promise(r => setTimeout(r, 400));
console.log('RESULT', await page.evaluate(() => document.getElementById('scoreLine').textContent));
await page.screenshot({ path: 'shot-ff.png' });
console.log('ERRORS', JSON.stringify(errors));
await browser.close();
