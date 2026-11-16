// Смоук-тест index.html в headless Chrome (puppeteer-core + системный Chrome)
const puppeteer = require('/home/dp/.npm-global/lib/node_modules/puppeteer-core');
const path = require('path');

const FILE = 'file://' + path.resolve(__dirname, 'index.html');

(async () => {
  const browser = await puppeteer.launch({
    executablePath: '/usr/bin/google-chrome',
    headless: 'new',
    args: ['--no-sandbox', '--disable-dev-shm-usage', '--allow-file-access-from-files']
  });
  const page = await browser.newPage();
  await page.setViewport({ width: 1440, height: 900 });

  const errors = [];
  const requests = [];
  page.on('pageerror', e => errors.push('pageerror: ' + e.message));
  page.on('console', m => { if (m.type() === 'error') errors.push('console: ' + m.text()); });
  page.on('request', r => { if (!r.url().startsWith('file://')) requests.push(r.url()); });

  await page.goto(FILE, { waitUntil: 'networkidle0' });

  const stat = await page.evaluate(() => ({
    lists: document.querySelectorAll('.disc-list').length,
    items: document.querySelectorAll('.disc-item').length,
    handles: document.querySelectorAll('.disc-handle').length,
    panes: document.querySelectorAll('[data-step-pane]').length,
    tabs: document.querySelectorAll('[data-step-btn]').length
  }));
  console.log('stat', JSON.stringify(stat));

  // открыть тест
  await page.click('#openTest');
  await new Promise(r => setTimeout(r, 300));
  console.log('open:', await page.evaluate(() => document.getElementById('wizardmodal').classList.contains('is-open')));

  // перебрать все шаги кнопкой «Далее»
  for (let i = 0; i < 7; i++) {
    await page.click('[data-disc-next]');
    await new Promise(r => setTimeout(r, 60));
  }
  const nav = await page.evaluate(() => ({
    step: document.getElementById('rootwizard').dataset.step,
    prevDisabled: document.querySelector('[data-disc-prev]').disabled,
    nextHidden: document.querySelector('[data-disc-next]').hidden,
    finishHidden: document.querySelector('[data-disc-finish]').hidden,
    progress: document.getElementById('discProgress').style.width
  }));
  console.log('after 7 next:', JSON.stringify(nav));

  // назад на первый шаг через таб
  await page.click('[data-step-btn="0"]');
  await new Promise(r => setTimeout(r, 60));
  console.log('tab click step:', await page.evaluate(() => document.getElementById('rootwizard').dataset.step));

  // --- drag&drop мышью: в первом списке перетащить 4-й элемент на 1-е место ---
  const box = await page.evaluate(() => {
    const ul = document.getElementById('draggable-list1');
    const li = ul.children[3];
    const r = li.getBoundingClientRect();
    return { x: r.x + 30, y: r.y + r.height / 2, ulTop: ul.getBoundingClientRect().top };
  });
  await page.mouse.move(box.x, box.y);
  await page.mouse.down();
  await page.mouse.move(box.x, box.y - 10, { steps: 3 });
  await page.mouse.move(box.x, box.ulTop + 6, { steps: 12 });
  await page.mouse.up();
  await new Promise(r => setTimeout(r, 150));
  const order1 = await page.evaluate(() =>
    Array.from(document.getElementById('draggable-list1').children).map(li => li.textContent.trim())
  );
  console.log('list1 after drag:', JSON.stringify(order1));

  // --- клавиатурное перемещение: вернуть слово вниз ---
  await page.evaluate(() => {
    const li = document.getElementById('draggable-list1').children[0];
    li.focus();
    li.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowDown', bubbles: true, cancelable: true }));
    li.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowDown', bubbles: true, cancelable: true }));
    li.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowDown', bubbles: true, cancelable: true }));
  });
  const order1b = await page.evaluate(() =>
    Array.from(document.getElementById('draggable-list1').children).map(li => li.textContent.trim())
  );
  console.log('list1 after keyboard down x3:', JSON.stringify(order1b));

  // --- нативный HTML5 DnD (синтетические события) ---
  const nativeOk = await page.evaluate(() => {
    const ul = document.getElementById('draggable-list2');
    const li = ul.children[0];
    const other = ul.children[3];
    const dt = new DataTransfer();
    li.dispatchEvent(new DragEvent('dragstart', { bubbles: true, cancelable: true, dataTransfer: dt }));
    const r = other.getBoundingClientRect();
    other.dispatchEvent(new DragEvent('dragover', { bubbles: true, cancelable: true, dataTransfer: dt, clientX: r.x + 5, clientY: r.y + r.height - 1 }));
    other.dispatchEvent(new DragEvent('drop', { bubbles: true, cancelable: true, dataTransfer: dt }));
    li.dispatchEvent(new DragEvent('dragend', { bubbles: true, cancelable: true, dataTransfer: dt }));
    return Array.from(ul.children).map(x => x.textContent.trim());
  });
  console.log('list2 after native dnd:', JSON.stringify(nativeOk));

  // --- завершить тест на последнем шаге ---
  await page.click('[data-step-btn="7"]');
  await new Promise(r => setTimeout(r, 60));
  await page.click('[data-disc-finish]');
  await new Promise(r => setTimeout(r, 200));
  const res = await page.evaluate(() => ({
    score: document.getElementById('scoreLine').textContent,
    wizardHidden: document.getElementById('wizardBody').hidden,
    resultShown: !document.getElementById('resultView').hidden,
    bars: document.querySelectorAll('.scorebar').length,
    legend: document.querySelectorAll('.legend-card').length
  }));
  console.log('result:', JSON.stringify(res));

  // сумма баллов должна быть нулём
  const sum = await page.evaluate(() => {
    const m = document.getElementById('scoreLine').textContent.match(/D:(-?\d+), I:(-?\d+), S:(-?\d+), C:(-?\d+)/);
    return m ? (+m[1] + +m[2] + +m[3] + +m[4]) : null;
  });
  console.log('score sum:', sum);

  await page.screenshot({ path: path.resolve(__dirname, 'shot-result.png') });

  // закрыть и открыть снова — должен открыться результат
  await page.click('#resultView [data-disc-close]');
  await new Promise(r => setTimeout(r, 150));
  await page.click('#openTest');
  await new Promise(r => setTimeout(r, 150));
  console.log('reopen shows result:', await page.evaluate(() => !document.getElementById('resultView').hidden));

  // перезапуск
  await page.click('[data-disc-restart]');
  await new Promise(r => setTimeout(r, 150));
  const restarted = await page.evaluate(() => ({
    wizard: !document.getElementById('wizardBody').hidden,
    step: document.getElementById('rootwizard').dataset.step,
    list1: Array.from(document.getElementById('draggable-list1').children).map(li => li.textContent.trim())
  }));
  console.log('restarted:', JSON.stringify(restarted));

  await page.screenshot({ path: path.resolve(__dirname, 'shot-wizard.png') });

  // мобильный вьюпорт
  await page.setViewport({ width: 390, height: 844, isMobile: true, hasTouch: true, deviceScaleFactor: 2 });
  await new Promise(r => setTimeout(r, 250));
  await page.screenshot({ path: path.resolve(__dirname, 'shot-mobile.png') });

  console.log('external requests:', JSON.stringify(requests));
  console.log('errors:', JSON.stringify(errors));
  await browser.close();
})().catch(e => { console.error('FATAL', e); process.exit(1); });
