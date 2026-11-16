const path = require('path');
const puppeteer = require('/home/dp/.npm-global/lib/node_modules/puppeteer-core');

(async () => {
  const browser = await puppeteer.launch({
    executablePath: '/usr/bin/google-chrome',
    headless: 'new',
    args: ['--no-sandbox', '--disable-dev-shm-usage']
  });
  const page = await browser.newPage();
  page.on('pageerror', e => console.log('pageerror:', e.message));
  await page.setViewport({ width: 390, height: 844, isMobile: true, hasTouch: true, deviceScaleFactor: 2 });
  await page.goto('file://' + path.resolve('index.html'), { waitUntil: 'load' });
  await page.click('#startBtn');
  await new Promise(r => setTimeout(r, 200));

  const info = await page.evaluate(() => {
    const tabs = document.getElementById('tabs');
    const btn = document.getElementById('btnNext');
    const r = btn.getBoundingClientRect();
    return {
      tabsClient: tabs.clientWidth, tabsScroll: tabs.scrollWidth, scrollLeft: tabs.scrollLeft,
      tabW: [...tabs.children].map(t => Math.round(t.getBoundingClientRect().width)),
      pageH: document.documentElement.scrollHeight,
      btnRect: { x: r.x, y: r.y, w: r.width, h: r.height },
      innerH: window.innerHeight, scrollY: window.scrollY,
      docScrollW: document.documentElement.scrollWidth, innerW: window.innerWidth
    };
  });
  console.log('info:', JSON.stringify(info));

  // keyboard on a known list
  await page.evaluate(() => document.querySelectorAll('.disc-list')[1].children[1].focus());
  const before = await page.evaluate(() => [...document.querySelectorAll('.disc-list')[1].children].map(li => li.dataset.type));
  await page.keyboard.press('ArrowUp');
  const up = await page.evaluate(() => [...document.querySelectorAll('.disc-list')[1].children].map(li => li.dataset.type));
  await page.keyboard.press('End');
  const end = await page.evaluate(() => [...document.querySelectorAll('.disc-list')[1].children].map(li => li.dataset.type));
  await page.keyboard.press('Home');
  const home = await page.evaluate(() => [...document.querySelectorAll('.disc-list')[1].children].map(li => li.dataset.type));
  console.log('kbd:', JSON.stringify({ before, up, end, home }));

  // is the "next" button clickable at mobile size?
  try {
    await page.click('#btnNext');
    console.log('click next ok, step =', await page.evaluate(() => document.querySelector('.pane.is-active').dataset.step));
  } catch (e) {
    console.log('click next FAILED:', e.message);
    const rect = await page.evaluate(() => { const b = document.getElementById('btnNext'); const r = b.getBoundingClientRect(); return { x: r.x, y: r.y, w: r.width, h: r.height, scrollY: window.scrollY, hidden: b.hidden }; });
    console.log('after fail rect:', JSON.stringify(rect));
  }

  // touch drag by handle on step 2
  const box = await page.evaluate(() => {
    const pane = document.querySelector('.pane.is-active');
    const li = pane.querySelector('.disc-list').children[0];
    const h = li.querySelector('.item__handle').getBoundingClientRect();
    const last = pane.querySelector('.disc-list').children[3].getBoundingClientRect();
    return { x: h.x + h.width / 2, y: h.y + h.height / 2, ty: last.y + last.height - 4 };
  });
  await page.touchscreen.touchStart(box.x, box.y);
  for (let i = 1; i <= 10; i++) {
    await page.touchscreen.touchMove(box.x, box.y + (box.ty - box.y) * i / 10);
    await new Promise(r => setTimeout(r, 20));
  }
  await page.touchscreen.touchEnd();
  await new Promise(r => setTimeout(r, 200));
  const afterTouch = await page.evaluate(() => ({
    order: [...document.querySelector('.pane.is-active .disc-list').children].map(li => li.querySelector('.item__word').textContent),
    scrollY: window.scrollY
  }));
  console.log('touch drag:', JSON.stringify(afterTouch));

  await page.screenshot({ path: 'shot-mobile-step2.png' });
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({ path: 'shot-mobile-top.png' });
  await browser.close();
})().catch(e => { console.error('FAIL', e); process.exit(1); });