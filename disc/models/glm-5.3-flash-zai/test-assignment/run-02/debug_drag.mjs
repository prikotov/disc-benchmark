import { createRequire } from 'module';
const require = createRequire('/home/dp/MyProjects/disc/test-assignment/package.json');
const puppeteer = require('puppeteer-core');

const EXEC = '/usr/bin/google-chrome';
const FILE = 'file://' + process.cwd() + '/index.html';

(async () => {
  const browser = await puppeteer.launch({
    executablePath: EXEC,
    headless: 'new',
    args: ['--no-sandbox', '--disable-dev-shm-usage'],
  });
  const page = await browser.newPage();
  await page.setViewport({ width: 1400, height: 950 });
  page.on('console', (m) => console.log('[page]', m.type(), m.text()));
  await page.goto(FILE, { waitUntil: 'load' });

  await page.evaluate(() => {
    ['pointerdown', 'pointermove', 'pointerup', 'mousedown', 'mousemove'].forEach((t) =>
      document.addEventListener(t, (e) => {
        if (t === 'pointermove' || t === 'mousemove') {
          if (!window.__mv) window.__mv = 0;
          window.__mv++;
          if (window.__mv < 6 || window.__mv % 5 === 0)
            console.log(t, e.pointerId ?? '-', e.clientX|0, e.clientY|0, 'target=', e.target.className?.baseVal ?? e.target.className);
        } else {
          console.log(t, e.pointerId ?? '-', e.button, 'target=', (e.target.closest && e.target.closest('.disc-item')?.textContent?.trim()) || e.target.tagName);
        }
      }, true)
    );
  });

  await page.click('[data-disc-open]');
  await new Promise(r => setTimeout(r, 300));

  const info = await page.evaluate(() => {
    const ul = document.querySelectorAll('.disc-list')[0];
    const li = ul.children[3];
    const r = li.getBoundingClientRect();
    return { x: r.left + r.width / 2, y: r.top + r.height / 2 };
  });
  console.log('drag from', info);

  await page.mouse.move(info.x, info.y);
  await page.mouse.down();
  for (let i = 1; i <= 10; i++) {
    await page.mouse.move(info.x, info.y - i * 12);
    await new Promise(r => setTimeout(r, 30));
  }
  await page.mouse.up();
  await new Promise(r => setTimeout(r, 200));

  const order = await page.evaluate(() => {
    const ul = document.querySelectorAll('.disc-list')[0];
    return [...ul.children].map(li => li.dataset.type).join(',');
  });
  console.log('ORDER AFTER:', order);
  console.log('is-dragging remains:', await page.evaluate(() => !!document.querySelector('.is-dragging')));

  await browser.close();
})().catch(e => { console.error('FATAL', e); process.exit(1); });
