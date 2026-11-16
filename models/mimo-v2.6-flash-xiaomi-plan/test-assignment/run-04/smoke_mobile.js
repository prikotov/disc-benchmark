// Мобильный прогон: coarse-указатель, тач-перетаскивание за «точечки», скриншоты
const puppeteer = require('/home/dp/.npm-global/lib/node_modules/puppeteer-core');
const path = require('path');
const FILE = 'file://' + path.resolve(__dirname, 'index.html');

(async () => {
  const browser = await puppeteer.launch({
    executablePath: '/usr/bin/google-chrome',
    headless: 'new',
    args: ['--no-sandbox', '--disable-dev-shm-usage']
  });
  const page = await browser.newPage();
  await page.setViewport({ width: 390, height: 844, isMobile: true, hasTouch: true, deviceScaleFactor: 2 });

  const errors = [];
  const requests = [];
  page.on('pageerror', e => errors.push('pageerror: ' + e.message));
  page.on('console', m => { if (m.type() === 'error') errors.push('console: ' + m.text()); });
  page.on('request', r => { if (!r.url().startsWith('file://')) requests.push(r.url()); });

  await page.goto(FILE, { waitUntil: 'networkidle0' });

  console.log('pointer coarse:', await page.evaluate(() =>
    window.matchMedia('(pointer: coarse)').matches));
  console.log('draggable flags (li/handle):', await page.evaluate(() => {
    const li = document.querySelector('.disc-item');
    return li.getAttribute('draggable') + '/' + li.querySelector('.disc-handle').getAttribute('draggable');
  }));

  await page.tap('#openTest');
  await new Promise(r => setTimeout(r, 400));
  console.log('open:', await page.evaluate(() => document.getElementById('wizardmodal').classList.contains('is-open')));
  await page.screenshot({ path: path.resolve(__dirname, 'shot-mobile-wizard.png') });

  // тач-перетаскивание за handle: 4-й элемент первого списка -> наверх
  const geo = await page.evaluate(() => {
    const ul = document.getElementById('draggable-list1');
    const li = ul.children[3];
    const h = li.querySelector('.disc-handle');
    const r = h.getBoundingClientRect();
    const top = ul.getBoundingClientRect().top;
    return { x: r.x + r.width / 2, y: r.y + r.height / 2, top };
  });

  const client = await page.createCDPSession();
  await client.send('Input.dispatchTouchEvent', {
    type: 'touchStart',
    touchPoints: [{ x: geo.x, y: geo.y }]
  });
  for (let i = 1; i <= 12; i++) {
    const y = geo.y + (geo.top + 8 - geo.y) * (i / 12);
    await client.send('Input.dispatchTouchEvent', {
      type: 'touchMove',
      touchPoints: [{ x: geo.x, y: y }]
    });
    await new Promise(r => setTimeout(r, 20));
  }
  await client.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
  await new Promise(r => setTimeout(r, 250));

  const order = await page.evaluate(() =>
    Array.from(document.getElementById('draggable-list1').children).map(li => li.textContent.trim()));
  console.log('list1 after touch drag:', JSON.stringify(order));

  // «Далее» на мобильном
  await page.tap('[data-disc-next]');
  await new Promise(r => setTimeout(r, 200));
  console.log('step after next:', await page.evaluate(() => document.getElementById('rootwizard').dataset.step));
  console.log('active tab in view:', await page.evaluate(() => {
    const t = document.querySelector('.disc-tab.is-active');
    const w = document.getElementById('wizardTabs');
    const tr = t.getBoundingClientRect(), wr = w.getBoundingClientRect();
    return tr.left >= wr.left - 1 && tr.right <= wr.right + 1;
  }));

  await page.screenshot({ path: path.resolve(__dirname, 'shot-mobile-wizard2.png') });

  // финал на мобилке
  await page.tap('[data-step-btn="7"]');
  await new Promise(r => setTimeout(r, 250));
  await page.tap('[data-disc-finish]');
  await new Promise(r => setTimeout(r, 250));
  console.log('score:', await page.evaluate(() => document.getElementById('scoreLine').textContent));
  await page.screenshot({ path: path.resolve(__dirname, 'shot-mobile-result.png'), fullPage: false });

  console.log('external requests:', JSON.stringify(requests));
  console.log('errors:', JSON.stringify(errors));
  await browser.close();
})().catch(e => { console.error('FATAL', e); process.exit(1); });
