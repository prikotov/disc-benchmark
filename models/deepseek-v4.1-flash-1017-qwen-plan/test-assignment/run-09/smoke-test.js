const puppeteer = require('puppeteer-core');
const path = require('path');

(async () => {
  const browser = await puppeteer.launch({
    executablePath: '/usr/bin/google-chrome',
    headless: 'new',
    args: ['--no-sandbox', '--disable-gpu', '--allow-file-access-from-files']
  });
  const page = await browser.newPage();
  const errors = [];
  const requests = [];
  page.on('console', m => { if (m.type() === 'error') errors.push('console: ' + m.text()); });
  page.on('pageerror', e => errors.push('pageerror: ' + e.message));
  page.on('request', r => requests.push(r.url()));

  await page.goto('file://' + path.resolve('index.html'), {waitUntil: 'load'});
  await page.setViewport({width: 1440, height: 1000, deviceScaleFactor: 1});
  await page.screenshot({path: 'shot-start.png', fullPage: true});

  await page.click('[data-disc-open]');
  await new Promise(r => setTimeout(r, 300));
  const modalOpen = await page.$eval('#wizardmodal', el => el.classList.contains('is-open'));
  const activeStep = await page.$eval('#wizardmodal', el => el.querySelector('#rootwizard').dataset.step);
  console.log('modalOpen', modalOpen, 'step', activeStep);

  // drag first item of first list to bottom using pointer/mouse
  const first = await page.$('#draggable-list1 .disc-item');
  const items = await page.$$('#draggable-list1 .disc-item');
  const boxFirst = await first.boundingBox();
  const boxLast = await items[3].boundingBox();
  const before = await page.$$eval('#draggable-list1 .disc-item', els => els.map(e => e.textContent.trim()));
  await page.mouse.move(boxFirst.x + boxFirst.width/2, boxFirst.y + boxFirst.height/2);
  await page.mouse.down();
  await page.mouse.move(boxFirst.x + boxFirst.width/2, boxLast.y + boxLast.height/2, {steps: 12});
  await page.mouse.up();
  await new Promise(r => setTimeout(r, 150));
  const after = await page.$$eval('#draggable-list1 .disc-item', els => els.map(e => e.textContent.trim()));
  console.log('before', JSON.stringify(before));
  console.log('after ', JSON.stringify(after));

  await page.screenshot({path: 'shot-step1.png', fullPage: false});

  // click next through steps
  for (let i = 0; i < 7; i++) {
    await page.click('[data-disc-next]');
    await new Promise(r => setTimeout(r, 80));
  }
  const step7 = await page.$eval('#rootwizard', el => el.dataset.step);
  const finishVisible = await page.$eval('[data-disc-finish]', el => !el.hidden);
  console.log('step7', step7, 'finishVisible', finishVisible);
  await page.screenshot({path: 'shot-step8.png', fullPage: false});

  await page.click('[data-disc-finish]');
  await new Promise(r => setTimeout(r, 300));
  const resultVisible = await page.$eval('#resultView', el => !el.hidden);
  const score = await page.$eval('#scoreText', el => el.textContent);
  console.log('resultVisible', resultVisible, 'score', score);
  await page.screenshot({path: 'shot-result.png', fullPage: false});

  // expected score from current DOM
  const expected = await page.evaluate(() => {
    const ranks = Array.from(document.querySelectorAll('.disc-list')).map(ul =>
      Array.from(ul.children).map(li => li.dataset.type));
    const maj = ranks.map(r => r[0]);
    const min = ranks.map(r => r[3]);
    const count = (a, ch) => a.filter(x => x === ch).length;
    const s = {d: count(maj,'d') - count(min,'d'), i: count(maj,'i') - count(min,'i'), s: count(maj,'s') - count(min,'s'), c: count(maj,'c') - count(min,'c')};
    return `D:${s.d}, I:${s.i}, S:${s.s}, C:${s.c}`;
  });
  console.log('expected', expected, 'match', expected === score);

  await page.click('[data-disc-restart]');
  await new Promise(r => setTimeout(r, 250));
  const restarted = await page.evaluate(() => {
    const first = Array.from(document.querySelectorAll('#draggable-list1 .disc-item')).map(e=>e.textContent.trim());
    return {resultHidden: document.querySelector('#resultView').hidden, step: document.querySelector('#rootwizard').dataset.step, first};
  });
  console.log('restarted', JSON.stringify(restarted));

  console.log('errors', JSON.stringify(errors));
  console.log('requests', JSON.stringify(requests));
  await browser.close();
})();
