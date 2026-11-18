import { chromium } from 'playwright-core';
const b = await chromium.launch({ executablePath: '/usr/bin/google-chrome', channel: undefined });
const p = await b.newPage();
const errs = [];
p.on('pageerror', e => errs.push(e.message));
await p.goto('file://' + process.cwd() + '/index.html');
await p.click('#startBtn');
// drag item in first list to bottom (HTML5 DnD)
const ul = p.locator('[data-list="0"]');
const first = ul.locator('.item').first();
const src = await first.boundingBox();
await p.mouse.move(src.x+10, src.y+10);
await p.mouse.down();
const last = await ul.locator('.item').nth(3).boundingBox();
await p.mouse.move(last.x+10, last.y+10, {steps: 8});
await p.mouse.up();
const ranks = await ul.locator('.rank').allTextContents();
// click through all steps
for (let s = 0; s < 7; s++) await p.click('#nextBtn');
await p.click('#finishBtn');
await p.waitForSelector('#result.is-open');
const scores = await p.locator('.bar-row .val').allTextContents();
const top = await p.textContent('#topNote');
console.log('ranks after drag:', ranks.join(','));
console.log('scores d/i/s/c:', scores.join(','), '| top:', top.trim());
console.log('errors:', errs.length ? errs : 'none');
await b.close();
