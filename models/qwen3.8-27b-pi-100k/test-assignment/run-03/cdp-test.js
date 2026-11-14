"use strict";
// headless-chrome CDP smoke test (no external deps, uses /json + websocket)
const { execFileSync, spawn } = require("node:child_process");
const path = require("node:path");
const os = require("node:os");
const fs = require("node:fs");
const http = require("node:http");

const FILE = "file://" + path.resolve("index.html");
const port = 9357;
const udd = fs.mkdtempSync(path.join(os.tmpdir(), "disc-chrome-"));

function get(url){
  return new Promise((res, rej) => http.get(url, r => {
    let d=""; r.on("data",c=>d+=c); r.on("end",()=>res(JSON.parse(d)));
  }).on("error", rej));
}

// minimal websocket client over net for CDP
const net = require("node:net");
const crypto = require("node:crypto");
function wsClient(wsUrl, onMsg){
  const u = new URL(wsUrl);
  const sock = net.connect(Number(u.port), "127.0.0.1");
  const key = crypto.randomBytes(16).toString("base64");
  sock.write(
    `GET ${u.pathname} HTTP/1.1\r\nHost: ${u.host}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: ${key}\r\nSec-WebSocket-Version: 13\r\n\r\n`);
  let buf = Buffer.alloc(0);
  let headerDone = false;
  let id = 0; const pending = new Map();
  function send(method, params){
    const n = ++id;
    const p = new Promise((res, rej) => pending.set(n, {res, rej}));
    sock.write(frame(JSON.stringify({ id: n, method, params: params || {} })));
    return p;
  }
  function frame(payload){
    const data = Buffer.from(payload);
    const len = data.length;
    let mask = Buffer.alloc(4), head;
    for(let i=0;i<4;i++) mask[i] = crypto.randomInt(256);
    if(len < 126){ head = Buffer.from([0x81, len | 0x80]); }
    else if(len < 65536){ head = Buffer.from([0x81, 126 | 0x80, (len>>8)&255, len&255]); }
    else { head = Buffer.concat([Buffer.from([0x81, 127|0x80]), Buffer.from([0,0,0,0,(len>>>24)&255,(len>>>16)&255,(len>>>8)&255,len&255])]); }
    const masked = Buffer.alloc(len);
    for(let i=0;i<len;i++) masked[i] = data[i] ^ mask[i&3];
    return Buffer.concat([head, mask, masked]);
  }
  sock.on("data", c => {
    buf = Buffer.concat([buf, c]);
    while(true){
      if(buf.length < 2) break;
      const b1 = buf[1];
      let off = 2, len = b1 & 0x7f;
      if(len === 126){ if(buf.length < 4) break; len = buf.readUInt16BE(2); off = 4; }
      else if(len === 127){ if(buf.length < 10) break; len = Number(buf.readBigUInt64BE(2)); off = 10; }
      if(buf.length < off + len) break;
      const pay = buf.slice(off, off+len); buf = buf.slice(off+len);
      try{
        const msg = JSON.parse(pay.toString("utf8"));
        if(msg.id && pending.has(msg.id)){
          const {res, rej} = pending.get(msg.id); pending.delete(msg.id);
          if(msg.error) rej(new Error(JSON.stringify(msg.error))); else res(msg.result);
        } else onMsg(msg);
      }catch(_){}
    }
  });
  const ready = new Promise(res => sock.once("data", () => setTimeout(() => res(send), 50)));
  return { sock, send, ready };
}

(async () => {
  const chrome = spawn("google-chrome", [
    "--headless=new","--no-sandbox","--disable-gpu","--disable-dev-shm-usage",
    `--remote-debugging-port=${port}`,"--user-data-dir="+udd,
    "file://" + path.resolve("index.html"),
  ], { stdio: "ignore" });
  let wsUrl = null;
  for(let i=0;i<60 && !wsUrl;i++){
    await new Promise(r=>setTimeout(r,500));
    try{
      const tabs = await get(`http://127.0.0.1:${port}/json`);
      const target = tabs.find(t => t.type === "page" && t.url.startsWith("file://"));
      if(target) wsUrl = target.webSocketDebuggerUrl;
    }catch(_){}
  }
  if(!wsUrl){ console.log("FAIL: no CDP target"); chrome.kill("KILL"); process.exit(1); }
  const ws = wsClient(wsUrl, () => {});
  await ws.ready;
  const ok = []; const bad = [];
  const check = (name, cond) => (cond ? ok : bad).push(name);

  await ws.send("Runtime.enable");
  const ev = (expr) => ws.send("Runtime.evaluate", { expression: expr, returnByValue: true, awaitPromise: true })
    .then(r => { if(r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails).slice(0,300)); return r.result.value; });

  // errors collector
  const pageErrors = [];
  wsClient(wsUrl, m => {
    if(m.method === "Runtime.exceptionThrown") pageErrors.push(m.params.exceptionDetails?.exception?.description || "unknown");
  });

  await ev(`document.title`);
  check("title", /Бесплатный тест DISC/.test(await ev("document.title")));
  check("open-btn", !!(await ev(`!!document.querySelector('#btnOpen')`)));

  // open modal
  await ev(`document.querySelector('#btnOpen').click(); true`);
  check("modal-open", await ev(`document.querySelector('#disc').classList.contains('is-open')`));
  check("tabs-8", await ev("document.querySelectorAll('.tab').length") === 8);
  check("lists-on-step-3", await ev("document.querySelectorAll('.list').length") === 3);
  check("items-12", await ev("Array.from(document.querySelectorAll('.list')).every(l=>l.children.length===4)"));

  // verify q1 first word has latin c
  check("latin-c", await ev(`document.querySelector('.txt').textContent`) === "Экспресcивный");

  // test reordering via keyboard: first .item, press ArrowDown
  const before = await ev(`document.querySelector('.list .item').textContent`);
  await ev(`
    (function(){
      const it = document.querySelector('.list .item');
      it.focus();
      it.dispatchEvent(new KeyboardEvent('keydown',{key:'ArrowDown',bubbles:true}));
      return true;
    })()
  `);
  const after = await ev(`document.querySelector('.list .item').textContent`);
  check("arrowmove", before !== after);

  // test pointer drag: move first item of list 2 to bottom
  await ev(`
    (function(){
      const list = document.querySelectorAll('.list')[1];
      const it = list.children[0];
      const r = it.getBoundingClientRect();
      const x = r.left + r.width/2;
      const yTop = r.top + r.height/2;
      const last = list.children[3];
      const rl = last.getBoundingClientRect();
      const yBot = rl.bottom + 30;
      const opts = {bubbles:true, clientX:x, clientY:yTop, isPrimary:true, pointerId:1, pointerType:'mouse', button:0, buttons:1};
      it.dispatchEvent(new PointerEvent('pointerdown', opts));
      // moves
      for(let i=1;i<=8;i++){
        const y = yTop + (yBot - yTop) * i / 8;
        document.dispatchEvent(new PointerEvent('pointermove', {bubbles:true, clientX:x, clientY:y, pointerId:1, pointerType:'mouse', buttons:1}));
      }
      document.dispatchEvent(new PointerEvent('pointerup', {bubbles:true, clientX:x, clientY:yBot, pointerId:1, pointerType:'mouse', buttons:0}));
      return true;
    })()
  `);
  const firstT = await ev(`document.querySelectorAll('.list')[1].children[0].dataset.type`);
  const orig4th = null; await ev(`void 0`);
  check("drag-reordered", firstT === "i"); // first was d(Пылкий), moved to bottom → next first is i

  // go through all steps
  for(let s=0;s<8;s++){
    const lastStep = s === 7;
    if(lastStep){
      await ev(`document.querySelector('#btnFinish').click(); true`);
    } else {
      await ev(`document.querySelector('#btnNext').click(); true`);
    }
  }
  check("result-visible", await ev(`!document.querySelector('#resultView').hidden`));
  const line = await ev(`document.querySelector('#scoreLine').textContent`);
  check("scoreline-format", /^D:-?\d+, I:-?\d+, S:-?\d+, C:-?\d+$/.test(line));
  const sum = await ev(`
    (function(){
      const m = document.querySelector('#scoreLine').textContent.match(/(-?\\d+)/g).map(Number);
      return m.reduce((a,b)=>a+b,0);
    })()
  `);
  check("sum-zero", sum === 0);
  console.log("scoreline:", line);

  // restart
  await ev(`document.querySelector('#btnRestart').click(); true`);
  check("restart", await ev(`document.querySelector('#resultView').hidden && document.querySelector('.list .item').textContent === 'Экспресcивный'`));

  // escape closes
  await ev(`document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true})); true`);
  check("esc-close", await ev(`!document.querySelector('#disc').classList.contains('is-open')`));

  // external requests check: network log would need CDP Network; we opened file:// with no network anyway.
  check("page-errors", pageErrors.length === 0);
  if(pageErrors.length) console.log("page errors:", pageErrors);

  console.log(`\nPASS ${ok.length}: ${ok.length && ok.join("; ")}`);
  if(bad.length) { console.log(`FAIL ${bad.length}: ${bad.join("; ")}`); }
  chrome.kill("KILL");
  process.exit(bad.length ? 1 : 0);
})().catch(e => { console.error("ERROR", e.message); process.exit(2); });
