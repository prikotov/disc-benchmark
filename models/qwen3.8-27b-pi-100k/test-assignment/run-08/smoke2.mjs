import puppeteer from '/home/dp/MyProjects/disc/test-assignment/node_modules/puppeteer-core/lib/esm/puppeteer/puppeteer-core.js';
const browser = await puppeteer.launch({ executablePath: '/usr/bin/google-chrome', headless: 'new', args: ['--no-sandbox'] });
const page = await browser.newPage();
const problems = [];
const net = [];
page.on('request', r => { if (!r.url().startsWith('file://')) net.push(r.url()); });
page.on('pageerror', e => problems.push('pageerror: ' + e.message));

await page.goto('file://' + process.cwd() + '/index.html', { waitUntil: 'load' });

// static structure
const st = await page.evaluate(() => {
  const panes = document.querySelectorAll('.pane'), lists = document.querySelectorAll('ul.plist'), items = document.querySelectorAll('.item');
  const okLists = [...lists].every(ul => ul.children.length === 4);
  const okTypes = [...lists].every(ul => ['d','i','s','c'].every(t => ul.querySelector(`li[data-type="${t}"]`)));
  const okRanks = [...lists].every(ul => [...ul.children].map((li,i) => li.querySelector('.item__rank').textContent === String(i+1)).every(Boolean));
  return { panes: panes.length, lists: lists.length, items: items.length, okLists, okTypes, okRanks, tabs: document.querySelectorAll('.tab').length };
});
console.log('structure:', st);
if (!(st.panes === 8 && st.lists === 24 && st.items === 96 && st.okLists && st.okTypes && st.okRanks && st.tabs === 8)) problems.push('structure bad');

await page.click('#btnStart');
// step 0: prev disabled, next visible
const a1 = await page.evaluate(() => ({ prev: document.getElementById('btnPrev').disabled, next: document.getElementById('btnNext').hidden, finish: document.getElementById('btnFinish').hidden, bar: document.getElementById('progressBar').style.width }));
console.log('step0 actions:', a1);
if (!a1.prev || a1.next || !a1.finish) problems.push('step0 buttons');

// reorder list1 via keyboard (same DOM path as DnD)
await page.evaluate(() => {
  const li = document.querySelector('.pane[data-step-pane="0"] .item');
  for (let k = 0; k < 3; k++) li.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowDown', bubbles: true }));
});
const o1 = await page.$eval('.pane[data-step-pane="0"] .plist', ul => [...ul.children].map(li => li.dataset.type));
if (o1.join() !== 'c,d,s,i') problems.push('reorder: ' + o1);

// navigate prev/next back and forth
await page.click('#btnNext'); await page.click('#btnPrev');
const mid = await page.$eval('.pane:not([hidden])', el => +el.dataset.stepPane);
if (mid !== 1) problems.push('prev/next: ' + mid);

// to last step
for (let i = 0; i < 7; i++) await page.click('#btnNext');
const a7 = await page.evaluate(() => ({ next: document.getElementById('btnNext').hidden, finish: !document.getElementById('btnFinish').hidden, bar: document.getElementById('progressBar').style.width }));
console.log('step7 actions:', a7);
if (!a7.next || !a7.finish || a7.bar !== '100%') problems.push('step7 buttons');

await page.click('#btnFinish');
await page.waitForSelector('#result:not([hidden])', { visible: true });
const shown = await page.evaluate(() => [...document.querySelectorAll('.score__value')].map(e => +e.textContent));
console.log('scores:', shown);
if (shown.join() !== '-1,-2,-2,5') problems.push('scores ' + shown);

// reset restores original order
await page.click('#btnReset');
const o1b = await page.$eval('.pane[data-step-pane="0"] .plist', ul => [...ul.children].map(li => li.dataset.type));
const resultHidden = await page.$eval('#result', el => el.hidden);
const pane0 = await page.$eval('.pane:not([hidden])', el => +el.dataset.stepPane);
console.log('after reset:', o1b, 'resultHidden:', resultHidden, 'pane:', pane0);
if (o1b.join() !== 'i,c,d,s' || !resultHidden || pane0 !== 0) problems.push('reset');

console.log('external requests:', net.length ? net : 'none');
console.log('PROBLEMS:', problems.length ? problems : 'none');
await browser.close();
