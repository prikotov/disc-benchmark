// Headless-Chrome playthrough of index.html via CDP (no external deps, Node >= 22).
// Checks: no exceptions, 96 items, modal flow 8 steps, drag reorder works, score matches DOM order.
import { spawn } from 'node:child_process';
import { setTimeout as sleep } from 'node:timers/promises';

const PORT = 9333;
const FILE = new URL('./index.html', import.meta.url).pathname;

const chrome = spawn('google-chrome', [
  '--headless=new', '--disable-gpu', '--no-sandbox',
  `--remote-debugging-port=${PORT}`, '--window-size=1400,1000', 'about:blank',
], { stdio: 'ignore' });

const die = (msg) => { console.error('FAIL:', msg); chrome.kill(); process.exit(1); };

// wait for devtools endpoint
let version;
for (let i = 0; i < 50; i++) {
  try { version = await (await fetch(`http://127.0.0.1:${PORT}/json/version`)).json(); break; }
  catch { await sleep(200); }
}
if (!version) die('devtools endpoint not reachable');

const ws = new WebSocket(version.webSocketDebuggerUrl);
await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });

let msgId = 0;
const pending = new Map();
const sessions = new Map();
const exceptions = [];
const consoleErrors = [];

ws.onmessage = (ev) => {
  const m = JSON.parse(ev.data);
  if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); return; }
  const s = m.sessionId ? sessions.get(m.sessionId) : null;
  if (!s) return;
  if (m.method === 'Runtime.exceptionThrown') exceptions.push(m.params);
  if (m.method === 'Runtime.consoleAPICalled' && m.params.type === 'error') consoleErrors.push(m.params);
};

const send = (method, params = {}, sessionId) => new Promise((resolve) => {
  const id = ++msgId;
  pending.set(id, resolve);
  ws.send(JSON.stringify({ id, method, params, ...(sessionId ? { sessionId } : {}) }));
});

const { result: tgt } = await send('Target.createTarget', { url: 'about:blank' });
const { result: att } = await send('Target.attachToTarget', { targetId: tgt.targetId, flatten: true });
const sid = att.sessionId;
sessions.set(sid, sid);

await send('Runtime.enable', {}, sid);
await send('Page.enable', {}, sid);
await send('Page.navigate', { url: 'file://' + FILE }, sid);
await sleep(1200);

const evl = async (expr) => {
  const r = await send('Runtime.evaluate', {
    expression: expr, awaitPromise: true, returnByValue: true,
  }, sid);
  if (r.result?.exceptionDetails) die('evaluate threw: ' + JSON.stringify(r.result.exceptionDetails));
  return r.result?.result?.value;
};

// 1) render smoke
const itemCount = await evl(`document.querySelectorAll('.disc-item').length`);
if (itemCount !== 96) die(`expected 96 items, got ${itemCount}`);
const handles = await evl(`document.querySelectorAll('.disc-handle').length`);
if (handles !== 96) die(`expected 96 handles, got ${handles}`);

// 2) open wizard
await evl(`document.querySelector('[data-disc-open]').click()`);
const opened = await evl(`document.getElementById('wizardmodal').classList.contains('is-open')`);
if (!opened) die('wizard did not open');
const activePane = await evl(`document.querySelector('.disc-pane.is-active').dataset.stepPane`);
if (activePane !== '0') die('step 0 not active on open');

// 3) drag test on list1: drag first item below the third (crossing its midpoint)
const dragResult = await evl(`(() => {
  const ul = document.getElementById('draggable-list1');
  const before = [...ul.children].map(li => li.dataset.type).join('');
  const items = [...ul.querySelectorAll('li')];
  const src = items[0], dst = items[2];
  const sr = src.getBoundingClientRect(), dr = dst.getBoundingClientRect();
  const sx = sr.left + sr.width/2, sy = sr.top + sr.height/2;
  const dx = dr.left + dr.width/2, dy = dr.top + dr.height/2; // ниже середины -> вставка после dst
  const opts = (x,y) => ({bubbles:true, cancelable:true, pointerId:7, pointerType:'mouse', clientX:x, clientY:y, isPrimary:true});
  src.dispatchEvent(new PointerEvent('pointerdown', opts(sx,sy)));
  const steps = 12;
  for (let i=1;i<=steps;i++){
    const x = sx+(dx-sx)*i/steps, y = sy+(dy-sy)*i/steps;
    window.dispatchEvent(new PointerEvent('pointermove', opts(x,y)));
  }
  window.dispatchEvent(new PointerEvent('pointerup', opts(dx,dy)));
  const after = [...ul.children].map(li => li.dataset.type).join('');
  return {before, after};
})()`);
if (dragResult.before === dragResult.after) die('drag did not reorder list1: ' + JSON.stringify(dragResult));
console.log('drag OK:', dragResult.before, '->', dragResult.after);

// ghost cleaned up?
const ghosts = await evl(`document.querySelectorAll('.disc-ghost').length`);
if (ghosts !== 0) die('ghost not removed after drop');

// 4) walk through all steps with "Далее"
for (let s = 1; s <= 7; s++) {
  await evl(`document.querySelector('[data-disc-next]').click()`);
  const p = await evl(`document.querySelector('.disc-pane.is-active').dataset.stepPane`);
  if (Number(p) !== s) die(`step mismatch: expected ${s}, got ${p}`);
}
const nextHidden = await evl(`document.querySelector('[data-disc-next]').hidden`);
const finishShown = await evl(`!document.querySelector('[data-disc-finish]').hidden`);
if (!nextHidden || !finishShown) die('next/finish visibility wrong at step 7');

// 5) finish -> result in same app
await evl(`document.querySelector('[data-disc-finish]').click()`);
const resultVisible = await evl(`!document.getElementById('discResultView').hidden`);
if (!resultVisible) die('result view not shown after finish');
const scoreText = await evl(`document.getElementById('discScore').textContent`);

// expected score from final DOM order (maj=pos0 +1, min=pos3 -1)
const expected = await evl(`(() => {
  const maj=[],min=[];
  document.querySelectorAll('.disc-list').forEach(ul=>{
    const lis=[...ul.querySelectorAll('li')];
    maj.push(lis[0].getAttribute('data-type'));
    min.push(lis[3].getAttribute('data-type'));
  });
  const c=(a,ch)=>a.reduce((s,v)=>s+(v===ch?1:0),0);
  const r={d:c(maj,'d')-c(min,'d'), i:c(maj,'i')-c(min,'i'), s:c(maj,'s')-c(min,'s'), c:c(maj,'c')-c(min,'c')};
  return 'D:'+r.d+', I:'+r.i+', S:'+r.s+', C:'+r.c;
})()`);
console.log('score shown :', scoreText);
console.log('score by DOM:', expected);
if (scoreText !== expected) die('score mismatch');

// tabs jump back to step 0 still works after result? (tabs hidden in result — check)
const tabsHidden = await evl(`getComputedStyle(document.querySelector('.disc-modal__tabs')).display === 'none'`);
if (!tabsHidden) die('tabs should be hidden in result mode');

// 6) restart resets lists and returns to test
await evl(`document.querySelector('[data-disc-restart]').click()`);
const afterRestart = await evl(`(() => {
  const ul = document.getElementById('draggable-list1');
  return {
    order: [...ul.children].map(li => li.dataset.type).join(''),
    testVisible: !document.getElementById('discTestBody').hidden,
    resultHidden: document.getElementById('discResultView').hidden,
    step: document.querySelector('.disc-pane.is-active').dataset.stepPane,
  };
})()`);
if (afterRestart.order !== 'icds') die('restart did not restore initial order');
if (!afterRestart.testVisible || !afterRestart.resultHidden || afterRestart.step !== '0') die('restart state wrong');
console.log('restart OK');

// 7) Esc closes modal
await evl(`document.dispatchEvent(new KeyboardEvent('keydown', {key:'Escape', bubbles:true}))`);
const closed = await evl(`!document.getElementById('wizardmodal').classList.contains('is-open')`);
if (!closed) die('Esc did not close wizard');

if (exceptions.length) die('page exceptions: ' + JSON.stringify(exceptions));
if (consoleErrors.length) die('console errors: ' + JSON.stringify(consoleErrors));

console.log('ALL CHECKS PASSED');
chrome.kill();
process.exit(0);
