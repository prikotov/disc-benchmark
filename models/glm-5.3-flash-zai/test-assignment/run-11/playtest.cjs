// CDP smoke-test + автопрохождение копии DISC
const fs = require('fs');
const http = require('http');
const path = require('path');

const FILE = 'file://' + path.resolve('/home/dp/MyProjects/disc/.tmpwork/disc-pi-lak86kfu/run/index.html');
const PORT = 9222;

function getJson(url) {
  return new Promise((res, rej) => {
    http.get(url, (r) => {
      let b = '';
      r.on('data', (c) => (b += c));
      r.on('end', () => res(JSON.parse(b)));
    }).on('error', rej);
  });
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function main() {
  const targets = await getJson(`http://127.0.0.1:${PORT}/json`);
  const page = targets.find((t) => t.type === 'page');
  if (!page) throw new Error('no page target');
  const ws = new WebSocket(page.webSocketDebuggerUrl);
  await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });

  let msgId = 0;
  const pending = new Map();
  const events = [];
  ws.onmessage = (m) => {
    const d = JSON.parse(m.data);
    if (d.id && pending.has(d.id)) { pending.get(d.id)(d); pending.delete(d.id); }
    else if (d.method) events.push(d);
  };
  const send = (method, params = {}) =>
    new Promise((res) => { const id = ++msgId; pending.set(id, res); ws.send(JSON.stringify({ id, method, params })); });

  await send('Runtime.enable');
  await send('Page.enable');
  const errors = [];

  const evalJs = async (expr) => {
    const r = await send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true });
    if (r.result.exceptionDetails) throw new Error('eval failed: ' + JSON.stringify(r.result.exceptionDetails.exception?.description || r.result.exceptionDetails.text));
    return r.result.result.value;
  };

  await send('Page.navigate', { url: FILE });
  for (let i = 0; i < 60; i++) {
    const rs = await evalJs(`document.readyState`).catch(() => 'loading');
    if (rs === 'complete') break;
    await sleep(250);
  }
  const loc = await evalJs(`location.href`);
  if (!loc.includes('index.html')) throw new Error('navigation failed: ' + loc);
  await sleep(300);

  // ---- 1. рендер-смоук ----
  const smoke = await evalJs(`(() => {
    const lists = document.querySelectorAll('.disc-list');
    const items = document.querySelectorAll('.disc-item');
    const tabs = document.querySelectorAll('.disc-tab');
    const panes = document.querySelectorAll('.disc-pane');
    return {
      title: document.title,
      lists: lists.length, items: items.length, tabs: tabs.length, panes: panes.length,
      firstWords: [...items].slice(0,4).map(i => i.textContent),
      activePane: document.querySelector('.disc-pane.is-active')?.dataset.stepPane,
      prevDisabled: document.getElementById('discPrev').disabled,
      nextHidden: document.getElementById('discNext').hidden,
      finishHidden: document.getElementById('discFinish').hidden,
      progress: document.getElementById('discProgress').style.width,
    };
  })()`);
  console.log('SMOKE:', JSON.stringify(smoke, null, 1));
  if (smoke.lists !== 24 || smoke.items !== 96 || smoke.tabs !== 8 || smoke.panes !== 8) throw new Error('render mismatch');

  // ---- 1b. данные посимвольно (до любых взаимодействий) ----
  {
    const ref = JSON.parse(fs.readFileSync('/tmp/questions.json', 'utf8'));
    const got = await evalJs(`(() => {
      const out = [];
      for (let i = 1; i <= 24; i++) {
        const ul = document.getElementById('draggable-list' + i);
        if (!ul) return null;
        out.push({ id: i, items: [...ul.querySelectorAll('.disc-item')].map(li => ({ type: li.getAttribute('data-type'), text: li.querySelector('.disc-item__text').textContent })) });
      }
      return out;
    })()`);
    let mm = 0;
    if (got) for (let i = 0; i < ref.length; i++) for (let j = 0; j < ref[i].items.length; j++) {
      const a = ref[i].items[j], b = got[i].items[j];
      if (a.type !== b.type || a.text !== b.text) { mm++; console.log(`MISMATCH block ${i+1} pos ${j}: ref=${JSON.stringify(a)} got=${JSON.stringify(b)}`); }
    } else mm++;
    console.log('DATA MISMATCHES:', mm);
    if (mm) throw new Error('data mismatch');
  }

  // ---- 2. поток: открыть, пройти шаги без перестановок, завершить ----
  await evalJs(`document.querySelector('[data-open-wizard]').click()`);
  await sleep(150);
  const openState = await evalJs(`({
    modalOpen: document.getElementById('wizardmodal').classList.contains('is-open'),
    ariaHidden: document.getElementById('wizardmodal').getAttribute('aria-hidden'),
    bodyLocked: document.documentElement.classList.contains('no-scroll'),
  })`);
  console.log('OPEN:', JSON.stringify(openState));

  for (let s = 0; s < 8; s++) {
    const st = await evalJs(`({
      step: document.querySelector('.disc-pane.is-active')?.dataset.stepPane,
      prev: !document.getElementById('discPrev').disabled,
      next: !document.getElementById('discNext').hidden,
      finish: !document.getElementById('discFinish').hidden,
      progress: document.getElementById('discProgress').style.width,
    })`);
    process.stdout.write(`STEP ${s}: ${JSON.stringify(st)}\n`);
    if (s < 7) await evalJs(`document.getElementById('discNext').click()`);
    await sleep(60);
  }
  await evalJs(`document.getElementById('discFinish').click()`);
  await sleep(300);
  const result1 = await evalJs(`({
    modalClosed: !document.getElementById('wizardmodal').classList.contains('is-open'),
    resultShown: !document.getElementById('result').hidden,
    score: document.getElementById('discScoreText').textContent,
    vals: ['d','i','s','c'].map(k => document.querySelector('#res-'+k+' .result__type-val').textContent),
  })`);
  console.log('RESULT(no reorder):', JSON.stringify(result1));
  // порядок списков = исходный, счёт = maj(pos0)-min(pos3) по данным оригинала
  if (result1.score !== 'D:-1, I:0, S:-3, C:4') throw new Error('score mismatch (no reorder): ' + result1.score);

  // ---- 3. перестановка: на шаге 1 первого элемента вниз в первом списке, счёт должен измениться ----
  await evalJs(`document.getElementById('discRestart').click()`);
  await sleep(150);
  // переставляем в списке 1: item0 (i) вниз на последнюю позицию (после item3)
  await evalJs(`(() => {
    const ul = document.getElementById('draggable-list1');
    const items = [...ul.querySelectorAll('.disc-item')];
    const first = items[0], third = items[3];
    const fr = third.getBoundingClientRect();
    const y = fr.top + fr.height * 0.75;
    const x = first.getBoundingClientRect().left + 10;
    const opts = (cx, cy) => ({ bubbles: true, pointerId: 7, pointerType: 'mouse', button: 0, buttons: 1, clientX: cx, clientY: cy, isPrimary: true });
    first.dispatchEvent(new PointerEvent('pointerdown', opts(x, first.getBoundingClientRect().top + 10)));
    first.dispatchEvent(new PointerEvent('pointermove', opts(x + 4, first.getBoundingClientRect().top + 16)));
    for (let i = 0; i <= 20; i++) {
      first.dispatchEvent(new PointerEvent('pointermove', opts(x + 4, first.getBoundingClientRect().top + 16 + (y - first.getBoundingClientRect().top - 16) * i / 20)));
    }
    first.dispatchEvent(new PointerEvent('pointermove', opts(x + 4, y)));
    first.dispatchEvent(new PointerEvent('pointerup', opts(x + 4, y)));
    return [...ul.querySelectorAll('.disc-item')].map(li => li.dataset.type + ':' + li.textContent.trim());
  })()`);
  const order1 = await evalJs(`[...document.getElementById('draggable-list1').querySelectorAll('.disc-item')].map(li => li.dataset.type)`);
  console.log('ORDER after drag (list1):', order1.join(','));
  if (order1.join(',') !== 'c,d,s,i') throw new Error('drag reorder failed: ' + order1.join(','));

  // дотащить до конца (без остальных перестановок) и проверить счёт:
  // один блок: most=c, least=i → c:+1, i:-1 по сравнению с нулевым
  for (let s = 0; s < 7; s++) await evalJs(`document.getElementById('discNext').click()`);
  await sleep(100);
  await evalJs(`document.getElementById('discFinish').click()`);
  await sleep(250);
  const result2 = await evalJs(`({
    score: document.getElementById('discScoreText').textContent,
  })`);
  console.log('RESULT(after 1 swap):', JSON.stringify(result2));
  if (result2.score !== 'D:-1, I:-2, S:-2, C:5') throw new Error('score mismatch after swap: ' + result2.score);

  // ---- 4. Esc закрывает модалку; табы кликабельны ----
  await evalJs(`document.querySelector('[data-open-wizard]').click()`);
  await sleep(100);
  await evalJs(`document.querySelectorAll('.disc-tab')[5].click()`);
  await sleep(80);
  const tabState = await evalJs(`({
    pane: document.querySelector('.disc-pane.is-active')?.dataset.stepPane,
    progress: document.getElementById('discProgress').style.width,
    listsStart: document.getElementById('draggable-list1').firstElementChild.dataset.type,
  })`);
  console.log('TAB JUMP:', JSON.stringify(tabState));
  await evalJs(`document.dispatchEvent(new KeyboardEvent('keydown', {key:'Escape', bubbles:true}))`);
  await sleep(100);
  const closed = await evalJs(`!document.getElementById('wizardmodal').classList.contains('is-open')`);
  console.log('ESC CLOSED:', closed);
  if (!closed) throw new Error('esc close failed');

  // ---- 5. данные посимвольно после рестарта ----
  await evalJs(`document.getElementById('discRestart').click()`);
  await sleep(150);
  const ref = JSON.parse(fs.readFileSync('/tmp/questions.json', 'utf8'));
  const got = await evalJs(`(() => {
    const out = [];
    for (let i = 1; i <= 24; i++) {
      const ul = document.getElementById('draggable-list' + i);
      if (!ul) return null;
      out.push({ id: i, items: [...ul.querySelectorAll('.disc-item')].map(li => ({ type: li.getAttribute('data-type'), text: li.querySelector('.disc-item__text').textContent })) });
    }
    return out;
  })()`);
  const exact = got && ref.every((b, i) => JSON.stringify(b) === JSON.stringify(got[i]));
  console.log('DATA EXACT MATCH AFTER RESTART:', exact);
  if (!exact) throw new Error('restart data mismatch');

  const consoleErrors = events.filter(e =>
    (e.method === 'Runtime.exceptionThrown') ||
    (e.method === 'Runtime.consoleAPICalled' && e.params.type === 'error')
  );
  console.log('CONSOLE ERRORS:', consoleErrors.length);
  if (consoleErrors.length) console.log(JSON.stringify(consoleErrors, null, 1).slice(0, 2000));

  console.log('ALL OK');
  ws.close();
  process.exit(0);
}

main().catch((e) => { console.error('FAIL:', e.message); process.exit(1); });
