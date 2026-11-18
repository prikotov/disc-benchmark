// Сверка подсчёта: одинаковые перестановки вариантов — на живой странице оригинала и на копии index.html.
// Оригинал доводим до результата штатным путём: finish -> токен в sessionStorage -> событие
// fd-form-success (как при успешной отправке формы) -> переход на /disc/result/?<token>,
// где страница сама расшифровывает токен и выводит баллы.
const puppeteer = require('/home/dp/.npm-global/lib/node_modules/puppeteer-core');
const path = require('path');
const fs = require('fs');

const DATA = JSON.parse(fs.readFileSync(path.resolve(__dirname, 'data.json'), 'utf8'));
const COPY = 'file://' + path.resolve(__dirname, '..', 'index.html');
const ORIG = 'https://stratoplan-school.com/disc/';
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// детерминированный генератор (mulberry32)
const rng = (seed) => () => {
  seed |= 0; seed = (seed + 0x6d2b79f5) | 0;
  let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
  t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
};
const shuffle4 = (r) => {
  const a = [0, 1, 2, 3];
  for (let i = 3; i > 0; i--) { const j = Math.floor(r() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; }
  return a;
};

const initialTypes = DATA.flat().map((cards) => cards.map(([t]) => t)); // 24 × 4

const expect = (perms) => {
  const s = { d: 0, i: 0, s: 0, c: 0 };
  perms.forEach((p, k) => {
    const order = p.map((i) => initialTypes[k][i]);
    s[order[0]] += 1;
    s[order[3]] -= 1;
  });
  return s;
};
const fmt = (s) => `D:${s.d}, I:${s.i}, S:${s.s}, C:${s.c}`;

// переставить варианты во всех 24 наборах; перестановка k применяется к k-му списку
const applyPerms = (perms) => {
  const lists = Array.from(document.querySelectorAll('#wizardmodal .disc-list, #panes .list'));
  lists.forEach((ul, k) => {
    const items = Array.from(ul.children).filter((li) => li.tagName === 'LI');
    perms[k].forEach((i) => ul.appendChild(items[i]));
  });
  return lists.length;
};

(async () => {
  const browser = await puppeteer.launch({
    executablePath: '/usr/bin/google-chrome',
    headless: true,
    args: ['--no-sandbox', '--disable-gpu', '--no-proxy-server', '--allow-file-access-from-files'],
    defaultViewport: { width: 1440, height: 900 },
  });

  const results = [];
  const seeds = [20240601, 7, 98765];
  for (const seed of seeds) {
    const r = rng(seed);
    const perms = Array.from({ length: 24 }, () => shuffle4(r));
    const expected = expect(perms);

    // --- копия ---
    const c = await browser.newPage();
    await c.goto(COPY, { waitUntil: 'load' });
    await c.evaluate(applyPerms, perms);
    await c.evaluate(() => document.querySelector('#finishBtn').click());
    await sleep(200);
    const copyShown = await c.$eval('#scoreText', (n) => n.textContent);
    await c.close();

    // --- оригинал ---
    const o = await browser.newPage();
    await o.goto(ORIG, { waitUntil: 'domcontentloaded', timeout: 60000 });
    await o.waitForSelector('#draggable-list24', { timeout: 60000 });
    const n = await o.evaluate(applyPerms, perms);
    await o.evaluate(() => document.querySelector('[data-disc-finish]').click());
    await sleep(1500); // шифрование токена (WebCrypto)
    const navP = o.waitForNavigation({ waitUntil: 'domcontentloaded', timeout: 60000 }).catch(() => null);
    await o.evaluate(() => window.postMessage({ type: 'fd-form-success' }, '*'));
    await navP;
    await o.waitForFunction(() => location.pathname.startsWith('/disc/result/'), { timeout: 60000 });
    await o.waitForFunction(() => {
      const s = document.querySelector('.result__score span');
      return s && s.textContent && !/^D:0, I:0, S:0, C:0$/.test(s.textContent);
    }, { timeout: 60000 }).catch(() => null);
    const origShown = await o.$eval('.result__score span', (x) => x.textContent).catch(() => '(нет)');
    const origUrl = o.url();
    await o.close();

    const ok = copyShown === fmt(expected) && origShown === fmt(expected);
    results.push({ seed, lists: n, expected: fmt(expected), copy: copyShown, original: origShown, ok });
    console.log(`seed ${seed}: списков=${n}  ожидалось ${fmt(expected)} | копия ${copyShown} | оригинал ${origShown} ${ok ? 'OK' : 'РАСХОЖДЕНИЕ'}`);
    console.log('   url результата оригинала:', origUrl.replace(/\?.*/, '?<token>'));
  }
  await browser.close();
  const allOk = results.every((x) => x.ok);
  console.log(allOk ? '\nВСЁ СОВПАЛО' : '\nЕСТЬ РАСХОЖДЕНИЯ');
  fs.writeFileSync(path.resolve(__dirname, 'cross.json'), JSON.stringify(results, null, 2));
  process.exit(allOk ? 0 : 1);
})().catch((e) => { console.error(e); process.exit(2); });
