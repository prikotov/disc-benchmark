const puppeteer = require('/home/dp/.npm-global/lib/node_modules/puppeteer-core');
const path = require('path');
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
(async () => {
  const browser = await puppeteer.launch({ browser: 'firefox', executablePath: '/usr/bin/firefox', headless: true, args: ['--headless'], protocol: 'webDriverBiDi', defaultViewport: { width: 1280, height: 860 } });
  const page = await browser.newPage();
  const errors = [];
  page.on('pageerror', (e) => errors.push(e.message));
  await page.goto('file://' + path.resolve(__dirname, '..', 'index.html'), { waitUntil: 'load' });
  console.log('title:', await page.title());
  await page.click('#openTest'); await sleep(200);
  console.log('dialog open:', await page.$eval('#testDialog', (n) => !n.hidden));
  console.log('items:', await page.$$eval('#pane-0 .item', (n) => n.length));
  const before = await page.$$eval('#pane-0 .list', (ls) => ls[0].querySelectorAll('.item')[0].firstChild.textContent);
  const box = await page.evaluate(() => { const li = document.querySelectorAll('#pane-0 .list')[0].children[0]; const r = li.getBoundingClientRect(); return { x: r.left + 60, y: r.top + r.height / 2 }; });
  const end = await page.evaluate(() => { const li = document.querySelectorAll('#pane-0 .list')[0].children[3]; const r = li.getBoundingClientRect(); return r.top + r.height / 2 + 8; });
  await page.mouse.move(box.x, box.y); await page.mouse.down();
  for (let k = 1; k <= 12; k++) { await page.mouse.move(box.x, box.y + (end - box.y) * k / 12); await sleep(20); }
  await page.mouse.up(); await sleep(250);
  const first = await page.$$eval('#pane-0 .list', (ls) => Array.from(ls[0].querySelectorAll('.item')).map((l) => l.firstChild.textContent));
  console.log('before:', before, 'after order:', JSON.stringify(first));
  await page.screenshot({ path: path.resolve(__dirname, 'shots', 'ff-step1.png') });
  await page.click('[data-step="7"]'); await sleep(100);
  await page.click('#finishBtn'); await sleep(200);
  console.log('score:', await page.$eval('#scoreText', (n) => n.textContent));
  await page.screenshot({ path: path.resolve(__dirname, 'shots', 'ff-result.png') });
  console.log('page errors:', JSON.stringify(errors));
  await browser.close();
})().catch((e) => { console.error('ERR', e.message.split('\n').slice(0, 3).join(' | ')); process.exit(1); });
