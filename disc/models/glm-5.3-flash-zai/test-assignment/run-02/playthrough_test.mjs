import { createRequire } from 'module';
const require = createRequire('/home/dp/MyProjects/disc/test-assignment/package.json');
const puppeteer = require('puppeteer-core');
const fs = require('fs');

const EXEC = '/usr/bin/google-chrome';
const FILE = 'file://' + process.cwd() + '/index.html';

(async () => {
  const browser = await puppeteer.launch({
    executablePath: EXEC,
    headless: 'new',
    args: ['--no-sandbox', '--disable-dev-shm-usage', '--window-size=1400,950'],
  });
  const page = await browser.newPage();
  await page.setViewport({ width: 1400, height: 950 });

  const consoleErrors = [];
  const pageErrors = [];
  const requests = [];
  page.on('console', (m) => { if (m.type() === 'error') consoleErrors.push(m.text()); });
  page.on('pageerror', (e) => pageErrors.push(String(e)));
  page.on('request', (r) => requests.push(r.url()));

  await page.goto(FILE, { waitUntil: 'load' });
  await page.screenshot({ path: 'shot-start.png' });

  // 1. render smoke
  const stats = await page.evaluate(() => ({
    lists: document.querySelectorAll('.disc-list').length,
    items: document.querySelectorAll('.disc-item').length,
    tabs: document.querySelectorAll('.disc-tab').length,
    panes: document.querySelectorAll('.disc-pane').length,
    title: document.getElementById('discTitle')?.textContent,
  }));
  console.log('RENDER:', JSON.stringify(stats));

  // 2. data check vs page.html
  const src = fs.readFileSync('page.html', 'utf8');
  const re = /<ul class="disc-list"[^>]*>([\s\S]*?)<\/ul>/g;
  let m, refLists = [];
  while ((m = re.exec(src))) {
    const items = [...m[1].matchAll(/<li class="disc-item" data-type="([disc])">(.*?)<\/li>/g)]
      .map(x => [x[1], x[2]]);
    refLists.push(items);
  }
  const gotLists = await page.evaluate(() =>
    [...document.querySelectorAll('.disc-list')].map(ul =>
      [...ul.querySelectorAll('li')].map(li => [li.dataset.type, li.querySelector('.disc-item__word').textContent])
    )
  );
  const dataOk = JSON.stringify(refLists) === JSON.stringify(gotLists);
  console.log('DATA exact match (order+content):', dataOk);
  if (!dataOk) {
    for (let i = 0; i < Math.max(refLists.length, gotLists.length); i++) {
      if (JSON.stringify(refLists[i]) !== JSON.stringify(gotLists[i])) {
        console.log('first diff at list', i + 1);
        console.log('ref :', JSON.stringify(refLists[i]));
        console.log('got :', JSON.stringify(gotLists[i]));
        break;
      }
    }
  }

  // 3. open modal
  await page.click('[data-disc-open]');
  await new Promise(r => setTimeout(r, 300));
  const openOk = await page.evaluate(() => document.getElementById('wizardmodal').classList.contains('is-open'));
  console.log('MODAL opens:', openOk);
  await page.screenshot({ path: 'shot-step1.png' });

  // 4. drag test: in the very first list, drag item 4 (idx 3) to the top, and item (new) last -> stays
  async function dragItem(ulIndex, fromIdx, toYOffset) {
    const info = await page.evaluate(({ ulIndex, fromIdx }) => {
      const ul = document.querySelectorAll('.disc-list')[ulIndex];
      const li = ul.children[fromIdx];
      const r = li.getBoundingClientRect();
      return { x: r.left + r.width / 2, y: r.top + r.height / 2 };
    }, { ulIndex, fromIdx });

    await page.mouse.move(info.x, info.y);
    await page.mouse.down();
    // move gradually
    const steps = 12;
    for (let i = 1; i <= steps; i++) {
      await page.mouse.move(info.x, info.y + (toYOffset * i) / steps);
      await new Promise(r => setTimeout(r, 10));
    }
    await page.mouse.up();
    await new Promise(r => setTimeout(r, 100));
  }

  // drag item `fromIdx` by `slots` item positions (center-to-center), overshooting 12px into the target
  async function dragItemCentered(ulIndex, fromIdx, slots = -3) {
    const info = await page.evaluate(({ ulIndex, fromIdx, slots }) => {
      const ul = document.querySelectorAll('.disc-list')[ulIndex];
      const a = ul.children[fromIdx].getBoundingClientRect();
      const target = ul.children[fromIdx + slots];
      const b = target.getBoundingClientRect();
      return { x: a.left + a.width / 2, y: a.top + a.height / 2, dy: (b.top + b.height / 2) - (a.top + a.height / 2) + Math.sign(slots) * 12 };
    }, { ulIndex, fromIdx, slots });
    await dragItem(ulIndex, fromIdx, info.dy);
  }

  // get order of first list before
  const before = await page.evaluate(() => [...document.querySelectorAll('.disc-list')[0].children].map(li => li.dataset.type));
  console.log('list1 types before:', before.join(','));

  // drag item idx3 to top: distance between centers of item3 and item0, minus overshoot
  await dragItemCentered(0, 3);
  const after = await page.evaluate(() => [...document.querySelectorAll('.disc-list')[0].children].map(li => li.dataset.type));
  console.log('list1 types after drag 3->0:', after.join(','));

  const expected = [before[3], before[0], before[1], before[2]];
  console.log('DRAG reorder ok:', JSON.stringify(after) === JSON.stringify(expected));

  // also test swap of adjacent: drag idx1 down one slot (center-to-center + overshoot)
  await dragItemCentered(0, 1, +1);
  const after2 = await page.evaluate(() => [...document.querySelectorAll('.disc-list')[0].children].map(li => li.dataset.type));
  const expected2 = [after[0], after[2], after[1], after[3]];
  console.log('DRAG adjacent swap ok:', JSON.stringify(after2) === JSON.stringify(expected2), '|', after2.join(','));

  // 5. full pass: for every list (except list1 already manipulated), drag idx3 -> idx0.
  // Track a deterministic permutation per list: [3,0,1,2]
  const finals = await page.evaluate(() => {
    // apply permutation via direct DOM for the remaining lists (drag for list1 done above);
    // but better: do it via UI for ALL lists including #1 in canonical form.
    return null;
  });

  // Reset page to redo a fully scripted canonical pass with real drags:
  await page.reload({ waitUntil: 'load' });
  await page.click('[data-disc-open]');
  await new Promise(r => setTimeout(r, 250));

  const permPlan = []; // for scoring expectation
  for (let s = 0; s < 8; s++) {
    // navigate to step s
    await page.evaluate((s) => {
      document.querySelectorAll('.disc-tab')[s].click();
    }, s);
    await new Promise(r => setTimeout(r, 120));
    for (let k = 0; k < 3; k++) {
      const ulIndex = s * 3 + k;
      const typesBefore = await page.evaluate((i) => [...document.querySelectorAll('.disc-list')[i].children].map(li => li.dataset.type), ulIndex);
      const h = await page.evaluate((i) => {
        const ul = document.querySelectorAll('.disc-list')[i];
        const a = ul.children[3].getBoundingClientRect();
        const b = ul.children[0].getBoundingClientRect();
        return { x: a.left + a.width / 2, y: a.top + a.height / 2, dy: (b.top + b.height / 2) - (a.top + a.height / 2) - 12 };
      }, ulIndex);
      const dy = h.dy;
      await page.mouse.move(h.x, h.y);
      await page.mouse.down();
      for (let i = 1; i <= 14; i++) {
        await page.mouse.move(h.x, h.y + (dy * i) / 14);
        await new Promise(r => setTimeout(r, 8));
      }
      await page.mouse.up();
      await new Promise(r => setTimeout(r, 80));
      const typesAfter = await page.evaluate((i) => [...document.querySelectorAll('.disc-list')[i].children].map(li => li.dataset.type), ulIndex);
      const exp = [typesBefore[3], typesBefore[0], typesBefore[1], typesBefore[2]];
      if (JSON.stringify(typesAfter) !== JSON.stringify(exp)) {
        console.log('DRAG FAIL list', ulIndex + 1, typesBefore.join(','), '->', typesAfter.join(','));
      }
      permPlan.push(exp);
    }
  }

  // 6. finish and read scores
  await page.click('#btnFinish');
  await new Promise(r => setTimeout(r, 250));
  const shown = await page.evaluate(() => ({
    visible: !document.getElementById('discResult').hidden,
    text: document.getElementById('resultScore').textContent,
    bars: document.querySelectorAll('#resultBars .result-bar__row').length,
  }));
  console.log('RESULT view visible:', shown.visible, '| score shown:', shown.text, '| bars:', shown.bars);

  // expected score from permPlan
  const exp = { d: 0, i: 0, s: 0, c: 0 };
  permPlan.forEach(list => {
    exp[list[0]]++;
    exp[list[3]]--;
  });
  const expStr = `D:${exp.d}, I:${exp.i}, S:${exp.s}, C:${exp.c}`;
  console.log('EXPECTED score:', expStr, '| MATCH:', expStr === shown.text);
  await page.screenshot({ path: 'shot-result.png' });

  // 7. restart
  await page.click('#btnRestart');
  await new Promise(r => setTimeout(r, 200));
  const restartOk = await page.evaluate(() => {
    const first = [...document.querySelectorAll('.disc-list')[0].children].map(li => li.dataset.type);
    return !document.getElementById('discResult').hidden === false &&
      document.querySelector('.disc-pane.is-active').dataset.stepPane === '0' &&
      first.join(',') === 'i,c,d,s';
  });
  console.log('RESTART ok:', restartOk);

  // 8. Esc close
  await page.keyboard.press('Escape');
  await new Promise(r => setTimeout(r, 150));
  const closedOk = await page.evaluate(() => !document.getElementById('wizardmodal').classList.contains('is-open'));
  console.log('ESC close ok:', closedOk);

  console.log('CONSOLE ERRORS:', consoleErrors.length, consoleErrors.slice(0, 3));
  console.log('PAGE ERRORS:', pageErrors.length, pageErrors.slice(0, 3));
  const external = requests.filter(u => !u.startsWith('file://') && !u.startsWith('data:'));
  console.log('EXTERNAL REQUESTS:', external.length, external.slice(0, 5));

  await browser.close();
})().catch(e => { console.error('FATAL', e); process.exit(1); });
