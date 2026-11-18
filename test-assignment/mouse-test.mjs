#!/usr/bin/env node
// Мышный драйвер с ВЕРИФИКАЦИЕЙ каждого драга: после перетаскивания
// перечитываем DOM-порядок списка; драг не применился — ретрай (до 3 раз,
// разный оффсет приземления). Все раскладки гарантированы → расхождение
// показанных баллов с планом честно указывает на решение.
import puppeteer from 'puppeteer-core';
import fs from 'node:fs';

const ref = JSON.parse(fs.readFileSync('reference/questions.json', 'utf-8'));
const bySet = new Map();
for (const q of ref.questions) {
  bySet.set(q.items.map(i => i.text).sort().join('|'), Object.fromEntries(q.items.map(i => [i.text, i.type])));
}
const keysJson = JSON.stringify([...bySet.keys()]);
const mapJson = JSON.stringify([...bySet.entries()]);

const MAJ = ['d','d','d','d','d','i','i','i','s','c','i','s','d','i','s','c','d','i','s','c','d','i','s','c'];
const MIN = ['c','s','c','i','c','s','c','s','c','i','d','s','c','d','i','s','i','d','s','c','c','d','i','s'];

const sleep = (ms) => new Promise(r => setTimeout(r, ms));

// страница: координаты и флаги для драга + текущий порядок текстов списка
const probe = (page, qi, pick) => page.evaluate((mj, mn, mjson, i, pick) => {
  const norm = (s) => (s || '').replace(/\s+/g, ' ').trim();
  const vis = (el) => !!(el.offsetParent || el.getClientRects().length);
  const refMap = new Map(JSON.parse(mjson));
  let seen = -1;
  for (const box of document.querySelectorAll('body *')) {
    if (!vis(box) || box.children.length !== 4) continue;
    const kids = [...box.children];
    const texts = kids.map(c => norm(c.textContent));
    if (texts.some(t => !t || t.length > 40)) continue;
    const tm = refMap.get([...texts].sort().join('|'));
    if (!tm) continue;
    seen++;
    if (seen !== i) continue;
    const byT = (t) => kids.find(c => tm[norm(c.textContent)] === t);
    const node = pick === 'topSrc' ? byT(mj) : pick === 'botSrc' ? byT(mn) : pick === 'topDst' ? kids[0] : kids[3];
    const isEdge = pick === 'topSrc' ? kids.indexOf(node) === 0
                 : pick === 'botSrc' ? kids.indexOf(node) === 3 : true;
    node.scrollIntoView({ block: 'center' });
    const r = node.getBoundingClientRect();
    return { x: r.x + r.width / 2, y: r.y + r.height / 2, edge: isEdge,
             order: kids.map(k => norm(k.textContent)).join('|') };
  }
  return null;
}, MAJ[qi], MIN[qi], mapJson, qi, pick);

const b = await puppeteer.launch({ executablePath: '/usr/bin/google-chrome', headless: true, args: ['--no-sandbox'] });
const p = await b.newPage();
await p.setViewport({ width: 1280, height: 900 });
await p.goto('file:///home/dp/MyProjects/disc/models/huihui-ai-pi-100k/test-assignment/run-01/index.html', { waitUntil: 'load' });
await sleep(400);

let retries = 0, failedDrags = 0;
const dragVerified = async (qi, kind) => {
  const before = await probe(p, qi, kind === 'top' ? 'topSrc' : 'botSrc');
  if (!before) return false;
  if (before.edge) return true; // уже на месте
  const orderBefore = before.order;
  const dst = await probe(p, qi, kind === 'top' ? 'topDst' : 'botDst');
  if (!dst) return false;

  for (let attempt = 0; attempt < 3; attempt++) {
    const jitter = [0, -10, 10][attempt];
    await p.mouse.move(before.x, before.y);
    await p.mouse.down();
    await p.mouse.move(before.x + 2, before.y + 2, { steps: 2 });
    await p.mouse.move(dst.x + jitter, dst.y + jitter, { steps: 18 });
    await sleep(120);
    await p.mouse.up();
    await sleep(400);
    const after = await probe(p, qi, kind === 'top' ? 'topSrc' : 'botSrc');
    if (after && after.edge && after.order !== orderBefore) return true;
    retries++;
  }
  failedDrags++;
  return false;
};

let qi = 0;
for (let step = 0; step < 60; step++) {
  const n = await p.evaluate((kj) => {
    const norm = (s) => (s || '').replace(/\s+/g, ' ').trim();
    const vis = (el) => !!(el.offsetParent || el.getClientRects().length);
    const keys = new Set(JSON.parse(kj));
    let n = 0;
    for (const box of document.querySelectorAll('body *')) {
      if (!vis(box) || box.children.length !== 4) continue;
      const texts = [...box.children].map(c => norm(c.textContent));
      if (texts.some(t => !t || t.length > 40)) continue;
      if (keys.has([...texts].sort().join('|'))) n++;
    }
    return n;
  }, keysJson);

  for (let k = 0; k < n && qi < 24; k++) {
    const t = await dragVerified(qi, 'top');
    const bo = await dragVerified(qi, 'bottom');
    if (t && bo) qi++; else { console.log('список не поддался, вопрос', qi); qi++; }
  }

  const fin = await p.evaluate(() => {
    const btn = [...document.querySelectorAll('button')].filter(x => x.offsetParent !== null)
      .find(x => /заверш/i.test(x.textContent));
    if (btn) { btn.click(); return true; }
    return false;
  });
  if (fin) break;
  await p.evaluate(() => {
    const btn = [...document.querySelectorAll('button')].filter(x => x.offsetParent !== null)
      .find(x => /далее/i.test(x.textContent));
    if (btn) btn.click();
  });
  await sleep(400);
}

await sleep(1200);
const txt = await p.evaluate(() => document.body.innerText);
const disp = [...txt.matchAll(/^[+−–-]?\d+$/gm)].map(x => x[0]);
console.log('обработано вопросов:', qi, '| ретраев:', retries, '| неудачных драгов:', failedDrags);
console.log('экранные числа:', disp, '(план: D:4, I:2, S:-2, C:-4)');
await b.close();
