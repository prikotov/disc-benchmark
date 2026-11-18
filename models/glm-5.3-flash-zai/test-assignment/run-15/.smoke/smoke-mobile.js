const puppeteer = require('puppeteer-core');
const path = require('path');
const FILE = 'file://' + path.resolve(__dirname, '..', 'index.html');
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

(async () => {
  const browser = await puppeteer.launch({
    executablePath: '/usr/bin/google-chrome',
    headless: 'new',
    args: ['--no-sandbox', '--disable-dev-shm-usage'],
  });
  const page = await browser.newPage();
  await page.setViewport({ width: 390, height: 844, isMobile: true, hasTouch: true, deviceScaleFactor: 2 });
  const errors = [];
  page.on('pageerror', (e) => errors.push(e.message));
  await page.goto(FILE, { waitUntil: 'load' });
  await sleep(300);

  const coarse = await page.evaluate(() => window.matchMedia('(pointer: coarse)').matches);
  console.log('COARSE', coarse);

  await page.tap('[data-modal-open="wizardmodal"]');
  await sleep(300);
  await page.screenshot({ path: 'shot-m-step1.png' });

  // drag за handle: синтетические pointer events (handler не проверяет isTrusted)
  const res = await page.evaluate(() => {
    const li = document.querySelector('#draggable-list1 .disc-item');
    const handle = li.querySelector('.disc-handle');
    const hr = handle.getBoundingClientRect();
    const x = hr.left + hr.width / 2, y = hr.top + hr.height / 2;
    const mk = (type, cx, cy) => new PointerEvent(type, {
      bubbles: true, cancelable: true, pointerId: 7, pointerType: 'touch',
      isPrimary: true, clientX: cx, clientY: cy, button: 0, buttons: type === 'pointerup' ? 0 : 1,
    });
    handle.dispatchEvent(mk('pointerdown', x, y));
    const steps = [];
    const targetY = y + 170; // на 2 строки вниз
    for (let i = 1; i <= 10; i++) {
      const cy = y + ((targetY - y) * i) / 10;
      window.dispatchEvent(mk('pointermove', x, cy));
      steps.push([...li.parentElement.children].indexOf(li));
    }
    window.dispatchEvent(mk('pointerup', x, targetY));
    return {
      positions: steps,
      finalOrder: [...document.querySelectorAll('#draggable-list1 .disc-item')].map((el) => el.dataset.type).join(''),
      draggingClassLeft: li.classList.contains('is-dragging'),
    };
  });
  console.log('TOUCH_DRAG', JSON.stringify(res));
  await sleep(400);
  await page.screenshot({ path: 'shot-m-step1b.png' });

  // завершаем: без перетаскиваний жмём Далее до 8-го, Завершить
  for (let i = 0; i < 7; i++) {
    await page.tap('[data-disc-next]');
    await sleep(200);
  }
  await page.tap('[data-disc-finish]');
  await sleep(500);
  const fin = await page.evaluate(() => ({
    visible: !document.querySelector('#resultview').hidden,
    score: document.querySelector('#scoreline').textContent,
  }));
  console.log('MOBILE_FINISH', JSON.stringify(fin));
  await sleep(400);
  await page.screenshot({ path: 'shot-m-result.png' });

  console.log('ERRORS', JSON.stringify(errors));
  await browser.close();
})().catch((e) => { console.error('FATAL', e); process.exit(1); });
