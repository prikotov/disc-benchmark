const path = require('path');
const puppeteer = require('/home/dp/.npm-global/lib/node_modules/puppeteer-core');

(async () => {
  const file = 'file://' + path.resolve('index.html');
  const browser = await puppeteer.launch({
    executablePath: '/usr/bin/google-chrome',
    headless: 'new',
    args: ['--no-sandbox', '--disable-dev-shm-usage']
  });
  const page = await browser.newPage();
  await page.setViewport({ width: 1280, height: 900 });

  const errors = [];
  const requests = [];
  page.on('pageerror', e => errors.push('pageerror: ' + e.message));
  page.on('console', m => { if (m.type() === 'error' || m.type() === 'warning') errors.push('console.' + m.type() + ': ' + m.text()); });
  page.on('request', r => requests.push(r.url()));

  await page.goto(file, { waitUntil: 'load' });
  await new Promise(r => setTimeout(r, 200));

  const intro = await page.evaluate(() => ({
    title: document.querySelector('h1').textContent.trim(),
    startVisible: !document.getElementById('screenIntro').hidden,
    tabs: document.querySelectorAll('.tab').length,
    lists: document.querySelectorAll('.disc-list').length,
    items: document.querySelectorAll('.item').length
  }));
  console.log('intro:', JSON.stringify(intro));

  await page.click('#startBtn');
  await new Promise(r => setTimeout(r, 150));

  const started = await page.evaluate(() => ({
    testVisible: !document.getElementById('screenTest').hidden,
    activePane: document.querySelector('.pane.is-active').dataset.step,
    activeTab: document.querySelector('.tab.is-active').textContent,
    prevDisabled: document.getElementById('btnPrev').disabled,
    nextHidden: document.getElementById('btnNext').hidden,
    finishHidden: document.getElementById('btnFinish').hidden,
    progressWidth: document.getElementById('progressBar').style.width,
    perPane: [...document.querySelectorAll('.pane')].map(p => p.querySelectorAll('.disc-list').length)
  }));
  console.log('started:', JSON.stringify(started));

  // --- real mouse drag: move first item of list #1 to the last position ---
  const box = await page.evaluate(() => {
    const li = document.querySelectorAll('.disc-list')[0].children[0];
    const handle = li.querySelector('.item__handle');
    const list = li.parentNode;
    const last = list.children[3];
    const hr = handle.getBoundingClientRect();
    const lr = last.getBoundingClientRect();
    return { hx: hr.x + hr.width / 2, hy: hr.y + hr.height / 2, targetY: lr.y + lr.height - 2, word: li.textContent.trim() };
  });
  await page.mouse.move(box.hx, box.hy);
  await page.mouse.down();
  for (let i = 1; i <= 12; i++) {
    await page.mouse.move(box.hx, box.hy + (box.targetY - box.hy) * i / 12);
    await new Promise(r => setTimeout(r, 12));
  }
  await page.mouse.up();
  await new Promise(r => setTimeout(r, 150));

  const afterDrag = await page.evaluate(() => {
    const list = document.querySelectorAll('.disc-list')[0];
    return {
      order: [...list.children].map(li => li.querySelector('.item__word').textContent),
      nums: [...list.children].map(li => li.querySelector('.item__num').textContent),
      aria: list.children[0].getAttribute('aria-label')
    };
  });
  console.log('drag:', JSON.stringify(afterDrag));

  // --- keyboard reorder: every list, move 2nd item to the end via End, then check ---
  await page.evaluate(() => {
    const lists = [...document.querySelectorAll('.disc-list')].slice(1, 4);
    lists.forEach(l => l.children[1].focus());
  });
  const kbdBefore = await page.evaluate(() => [...document.querySelectorAll('.disc-list')[1].children].map(li => li.dataset.type));
  await page.keyboard.press('End');
  const kbdAfter = await page.evaluate(() => [...document.querySelectorAll('.disc-list')[1].children].map(li => li.dataset.type));
  console.log('keyboard:', JSON.stringify(kbdBefore), '->', JSON.stringify(kbdAfter));
  await page.keyboard.press('Home');
  const kbdHome = await page.evaluate(() => [...document.querySelectorAll('.disc-list')[1].children].map(li => li.dataset.type));
  console.log('keyboard Home:', JSON.stringify(kbdHome));

  // --- walk through all steps, reorder a few lists deterministically ---
  const steps = [];
  for (let s = 0; s < 8; s++) {
    const state = await page.evaluate(() => ({
      step: document.querySelector('.pane.is-active').dataset.step,
      tab: document.querySelector('.tab.is-active').textContent,
      meta: document.getElementById('stepMeta').textContent,
      prevDisabled: document.getElementById('btnPrev').disabled,
      nextHidden: document.getElementById('btnNext').hidden,
      finishHidden: document.getElementById('btnFinish').hidden,
      progress: document.getElementById('progressBar').style.width
    }));
    steps.push(state);
    // on each step, move first item of the 2nd list to the bottom (keyboard End)
    await page.evaluate(() => {
      const pane = document.querySelector('.pane.is-active');
      const li = pane.querySelectorAll('.disc-list')[1].children[0];
      li.focus();
    });
    await page.keyboard.press('End');
    if (s < 7) { await page.click('#btnNext'); await new Promise(r => setTimeout(r, 60)); }
  }
  console.log('steps:', JSON.stringify(steps, null, 0));

  const preFinish = await page.evaluate(() => {
    const score = { d: 0, i: 0, s: 0, c: 0 };
    document.querySelectorAll('.disc-list').forEach(l => {
      const items = [...l.children];
      score[items[0].dataset.type] += 1;
      score[items[3].dataset.type] -= 1;
    });
    return score;
  });

  // click finish (last step)
  await page.click('#btnFinish');
  await new Promise(r => setTimeout(r, 600));

  const result = await page.evaluate(() => ({
    visible: !document.getElementById('screenResult').hidden,
    testHidden: document.getElementById('screenTest').hidden,
    line: document.getElementById('scoreLine').textContent,
    values: [...document.querySelectorAll('.scale')].map(s => s.dataset.type + '=' + s.querySelector('.scale__val').textContent),
    fills: [...document.querySelectorAll('.scale__fill')].map(f => f.style.width + '/' + f.style.left + '/' + f.style.right)
  }));
  console.log('expected:', JSON.stringify(preFinish));
  console.log('result:', JSON.stringify(result));

  // restart
  await page.click('#btnRestart');
  await new Promise(r => setTimeout(r, 150));
  const restart = await page.evaluate(() => ({
    testVisible: !document.getElementById('screenTest').hidden,
    step: document.querySelector('.pane.is-active').dataset.step,
    order: [...document.querySelectorAll('.disc-list')[0].children].map(li => li.querySelector('.item__word').textContent)
  }));
  console.log('restart:', JSON.stringify(restart));

  // mobile pass: drag by handle + tap flow
  await page.setViewport({ width: 390, height: 844, deviceScaleFactor: 2, isMobile: true, hasTouch: true });
  await new Promise(r => setTimeout(r, 150));
  const mobile = await page.evaluate(() => ({
    overflowX: document.documentElement.scrollWidth > window.innerWidth + 1,
    gridCols: getComputedStyle(document.querySelector('.grid')).gridTemplateColumns,
    tabsScrollable: document.querySelector('.tabs').scrollWidth > document.querySelector('.tabs').clientWidth
  }));
  console.log('mobile:', JSON.stringify(mobile));
  await page.click('#btnNext');
  await new Promise(r => setTimeout(r, 150));
  const mobileStep2 = await page.evaluate(() => ({
    step: document.querySelector('.pane.is-active').dataset.step,
    overflowX: document.documentElement.scrollWidth > window.innerWidth + 1,
    tabLeft: document.querySelector('.tabs').scrollLeft
  }));
  console.log('mobile step2:', JSON.stringify(mobileStep2));

  // screenshots
  await page.setViewport({ width: 1280, height: 900 });
  await page.evaluate(() => document.getElementById('btnRestart').click());
  await new Promise(r => setTimeout(r, 200));
  await page.screenshot({ path: 'shot-intro.png' });
  await page.click('#startBtn');
  await new Promise(r => setTimeout(r, 200));
  await page.screenshot({ path: 'shot-step1.png' });
  await page.evaluate(() => document.getElementById('btnFinish').hidden || document.getElementById('btnNext').click());
  await new Promise(r => setTimeout(r, 400));
  await page.screenshot({ path: 'shot-step2.png' });
  await page.evaluate(() => {
    for (let i = 0; i < 8; i++) document.getElementById('btnNext').click();
  });
  await new Promise(r => setTimeout(r, 100));
  await page.evaluate(() => {
    if (!document.getElementById('btnFinish').hidden) document.getElementById('btnFinish').click();
  });
  await new Promise(r => setTimeout(r, 700));
  await page.screenshot({ path: 'shot-result.png' });

  console.log('errors:', JSON.stringify(errors));
  console.log('requests:', JSON.stringify(requests));

  await browser.close();
})().catch(e => { console.error('FAIL', e); process.exit(1); });