import { createRequire } from 'module';
const require = createRequire('/home/dp/MyProjects/disc/test-assignment/package.json');
const puppeteer = require('puppeteer-core');
(async () => {
  const browser = await puppeteer.launch({ executablePath: '/usr/bin/google-chrome', headless: 'new', args: ['--no-sandbox'] });
  const page = await browser.newPage();
  await page.setViewport({ width: 390, height: 844, isMobile: true, hasTouch: true });
  await page.goto('file://' + process.cwd() + '/index.html', { waitUntil: 'load' });
  await page.click('[data-disc-open]');
  await new Promise(r => setTimeout(r, 400));
  const state = await page.evaluate(() => {
    const finishBtn = document.getElementById('btnFinish');
    const tab = document.querySelectorAll('.disc-tab')[7];
    tab.click();
    return new Promise(res => setTimeout(() => {
      res({
        finishVisibleAfterJump: !finishBtn.hidden && finishBtn.offsetParent !== null,
        nextHiddenOnLast: document.getElementById('btnNext').offsetParent === null,
        activePane: document.querySelector('.disc-pane.is-active').dataset.stepPane,
        itemTouchAction: getComputedStyle(document.querySelector('.disc-item')).touchAction,
        handleTouchAction: getComputedStyle(document.querySelector('.disc-handle')).touchAction,
      });
    }, 300));
  });
  console.log(JSON.stringify(state, null, 1));
  await page.screenshot({ path: 'shot-mobile.png' });
  await browser.close();
})().catch(e => { console.error('FATAL', e); process.exit(1); });
