const fs = require('fs');
const path = require('path');

const PORT = 9222;
const FILE = 'file://' + path.resolve(__dirname, 'index.html');

async function httpJson(p) {
  const r = await fetch(`http://127.0.0.1:${PORT}${p}`);
  return r.json();
}

class CDP {
  constructor(ws) { this.ws = ws; this.id = 0; this.waiters = new Map(); this.events = []; }
  static async connect(url) {
    const ws = new WebSocket(url);
    await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });
    const c = new CDP(ws);
    ws.onmessage = (m) => {
      const d = JSON.parse(m.data);
      if (d.id && c.waiters.has(d.id)) { const w = c.waiters.get(d.id); c.waiters.delete(d.id); d.error ? w.rej(new Error(JSON.stringify(d.error))) : w.res(d.result); }
      if (d.method) { c.events.push(d); if (c.onEvent) c.onEvent(d); }
    };
    return c;
  }
  send(method, params = {}) {
    const id = ++this.id;
    this.ws.send(JSON.stringify({ id, method, params }));
    return new Promise((res, rej) => { this.waiters.set(id, { res, rej }); setTimeout(() => { if (this.waiters.has(id)) { this.waiters.delete(id); rej(new Error('timeout ' + method)); } }, 10000); });
  }
  async eval(expr) {
    const r = await this.send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true });
    if (r.exceptionDetails) throw new Error('page exception: ' + JSON.stringify(r.exceptionDetails));
    return r.result.value;
  }
  close() { this.ws.close(); }
}

(async () => {
  const out = [];
  const ok = (name, cond, extra = '') => { out.push((cond ? 'PASS ' : 'FAIL ') + name + (extra ? ' — ' + extra : '')); };

  // 1) static scan of index.html for external references
  const src = fs.readFileSync(path.resolve(__dirname, 'index.html'), 'utf8');
  const extRe = /https?:\/\/[^\s"'<>]+/g;
  const ext = [...new Set((src.match(extRe) || []).map(u => u.split(':')[0] + '://' + u.split('/')[2]))];
  ok('no external http(s) URLs in index.html', ext.length === 0, ext.join(','));
  ok('no <script src>/', !/<script[^>]+src=/.test(src));
  ok('no <link ... href="http', !/<link[^>]+href="http/.test(src));
  ok('no <img', !/<img/i.test(src));
  ok('inline svg icons present', (src.match(/<svg/g) || []).length >= 5);

  // 2) browser run
  const targets = await httpJson('/json');
  const page = targets.find(t => t.type === 'page');
  const cdp = await CDP.connect(page.webSocketDebuggerUrl);
  await cdp.send('Runtime.enable');
  await cdp.send('Page.enable');
  await cdp.send('Network.enable');
  const netUrls = [];
  cdp.onEvent = (d) => { if (d.method === 'Network.requestWillBeSent') netUrls.push(d.params.request.url); };

  const errors = [];
  await cdp.send('Runtime.enable');
  // capture console errors
  await cdp.eval(`window.__errs = []; const _e = window.onerror; window.onerror = (m) => { window.__errs.push(String(m)); }; true`);

  // start screen
  ok('start view visible', await cdp.eval(`!document.getElementById('viewStart').hidden`));
  ok('test view hidden initially', await cdp.eval(`document.getElementById('viewTest').hidden`));
  ok('24 lists after build (DOM present)', await cdp.eval(`document.querySelectorAll('.list').length === 24`));
  ok('8 tabs', await cdp.eval(`document.querySelectorAll('.tab').length === 8`));
  ok('96 items', await cdp.eval(`document.querySelectorAll('.list .item').length === 96`));

  // click start
  await cdp.eval(`document.getElementById('btnStart').click(); true`);
  ok('entering test shows it, hides start', await cdp.eval(`!document.getElementById('viewTest').hidden && document.getElementById('viewStart').hidden`));
  ok('step 0: prev disabled, next visible, finish hidden', await cdp.eval(`
    (() => { return document.getElementById('btnPrev').disabled && !document.getElementById('btnNext').hidden && document.getElementById('btnFinish').hidden })()
  `));
  ok('only first pane visible', await cdp.eval(`
    (() => { const p=[...document.querySelectorAll('#panes > div')]; return p[0].hidden===false && p.slice(1).every(x=>x.hidden) })()
  `));
  ok('progress bar = 12.5%', await cdp.eval(`document.getElementById('progressBar').style.width==='12.5%'`));

  // tab jump to step 4 and back
  await cdp.eval(`document.querySelectorAll('.tab')[4].click(); true`);
  ok('tab 5 navigates (step 4 of 8, bar 62.5%)', await cdp.eval(`
    (() => { const p=[...document.querySelectorAll('#panes > div')]; return p[4].hidden===false && document.getElementById('progressBar').style.width==='62.5%' })()
  `));
  await cdp.eval(`document.getElementById('btnPrev').click(); true`);

  // baseline: untouched order must score exactly like the original site computes
  const lists0 = await cdp.eval(`[...document.querySelectorAll('.list')].map(ul => [...ul.children].map(li => li.getAttribute('data-type')))`);
  const base = { d: 0, i: 0, s: 0, c: 0 };
  for (const l of lists0) { base[l[0]]++; base[l[l.length - 1]]--; }
  ok('untouched baseline score = D:-1, I:0, S:-3, C:4 (original site rule/example)',
     base.d === -1 && base.i === 0 && base.s === -3 && base.c === 4,
     `D:${base.d}, I:${base.i}, S:${base.s}, C:${base.c}`);

  // pointer drag: move item[0] of first list to the end
  const dragRes = await cdp.eval(`
    (() => {
      const ul = document.querySelector('#panes > div .list');
      const lis = [...ul.children];
      const moved = lis[0];
      const last = lis[lis.length-1];
      const r = last.getBoundingClientRect();
      const x = r.left + r.width/2, y = r.top + r.height/2;
      const opts = (clientX, clientY) => ({ bubbles: true, pointerId: 1, pointerType: 'mouse', isPrimary: true, clientX, clientY, button: 0, buttons: 1 });
      const r0 = moved.getBoundingClientRect();
      moved.dispatchEvent(new PointerEvent('pointerdown', opts(r0.left + 20, r0.top + 10)));
      moved.dispatchEvent(new PointerEvent('pointermove', opts(x, y)));
      ul.dispatchEvent(new PointerEvent('pointermove', opts(x, y)));
      moved.dispatchEvent(new PointerEvent('pointerup', opts(x, y)));
      ul.dispatchEvent(new PointerEvent('pointerup', opts(x, y)));
      return [...ul.querySelectorAll('.item .txt')].map(e => e.textContent);
    })()
  `);
  ok('drag moved item0 to end of first list', dragRes[dragRes.length-1] === 'Экспресcивный', dragRes.join(' | '));
  ok('position badges refreshed after drag', await cdp.eval(`
    (() => { const u=document.querySelector('#panes > div .list'); return [...u.querySelectorAll('.pos')].map(e=>e.textContent).join('') === '1234' })()
  `));

  // go to last step & finish — but first make a second change to have a known score:
  // compute expected score in the page using the ORIGINAL rule (maj pos0 +1, min last -1)
  const scoresNow = await cdp.eval(`
    (() => {
      const counts = {d:0,i:0,s:0,c:0};
      document.querySelectorAll('.list').forEach(ul => {
        const lis=[...ul.children];
        lis.forEach((li, ix) => { const t=li.getAttribute('data-type'); if (!(t in counts)) return; if (ix===0) counts[t]++; else if (ix===lis.length-1) counts[t]--; });
      });
      return counts;
    })()
  `);

  // also compute independently in node from page DOM order (via eval dump)
  const lists = await cdp.eval(`[...document.querySelectorAll('.list')].map(ul => [...ul.children].map(li => li.getAttribute('data-type')))`);
  const node = {d:0,i:0,s:0,c:0};
  for (const l of lists) { node[l[0]]++; node[l[l.length-1]]--; }
  ok('score rule: page-computed equals node-computed', JSON.stringify(scoresNow) === JSON.stringify(node), JSON.stringify(node));

  await cdp.eval(`
    (async () => {
      const next = () => document.getElementById('btnNext');
      for (let i=0;i<7;i++) next().click();
    })(); true
  `);
  ok('on step 8: next hidden, finish visible', await cdp.eval(`
    (() => { return document.getElementById('btnNext').hidden && !document.getElementById('btnFinish').hidden })()
  `));

  await cdp.eval(`document.getElementById('btnFinish').click(); true`);
  ok('result view shown, test hidden', await cdp.eval(`
    (() => { const g=(id)=>document.getElementById(id); return !g('viewResult').hidden && g('viewTest').hidden })()
  `));
  const scoreLine = await cdp.eval(`document.getElementById('scoreLine').textContent`);
  const expectedLine = `D:${node.d}, I:${node.i}, S:${node.s}, C:${node.c}`;
  ok('score line matches expected', scoreLine === expectedLine, scoreLine + ' vs ' + expectedLine);

  // restart resets order
  await cdp.eval(`document.getElementById('btnRestart').click(); true`);
  ok('restart returns to step 0', await cdp.eval(`
    (() => { const p=[...document.querySelectorAll('#panes > div')]; return !document.getElementById('viewTest').hidden && p[0].hidden===false && document.getElementById('progressBar').style.width==='12.5%' })()
  `));
  const firstOrder = await cdp.eval(`[...document.querySelectorAll('#panes > div .list .item .txt')].slice(0,4).map(e=>e.textContent)`);
  ok('first list order restored after restart', firstOrder[0] === 'Экспресcивный' && firstOrder[3] === 'Осторожный', firstOrder.join(' | '));

  // network: no external requests during the whole session
  const uniq = [...new Set(netUrls)].filter(u => !u.startsWith('file://'));
  ok('no network requests (offline, file:// only)', uniq.length === 0, uniq.join(', '));

  const errs = await cdp.eval(`window.__errs`);
  ok('no page errors', Array.isArray(errs) && errs.length === 0, JSON.stringify(errs));

  cdp.close();
  console.log(out.join('\n'));
  process.exit(out.some(l => l.startsWith('FAIL')) ? 1 : 0);
})().catch(e => { console.error('HARNESS ERROR', e); process.exit(2); });
