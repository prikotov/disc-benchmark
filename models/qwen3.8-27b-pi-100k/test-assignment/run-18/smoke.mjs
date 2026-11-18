// CDP smoke test against bundled Chrome. No external deps.
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import http from 'node:http';
import url from 'node:url';
import net from 'node:net';
import crypto from 'node:crypto';

const CHROME = process.env.CHROME_BIN || '/home/dp/.cache/puppeteer/chrome/linux-157.0.8103.50/chrome-linux64/chrome';
const PORT = 9345;

const getJSON = (u) => new Promise((res, rej) => {
  http.get(u, r => { let s = ''; r.on('data', c => s += c); r.on('end', () => res(JSON.parse(s))); }).on('error', rej);
});

const sleep = (ms) => new Promise(r => setTimeout(r, ms));

class WS {
  constructor() { this.sock = null; this.buf = Buffer.alloc(0); this.handlers = new Map(); }
  connect(host, port, path, cb) {
    const key = crypto.randomBytes(16).toString('base64');
    const req = 'GET ' + path + ' HTTP/1.1\r\nHost: ' + host + ':' + port + '\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: ' + key + '\r\nSec-WebSocket-Version: 13\r\n\r\n';
    this.sock = net.connect({ host, port });
    this.sock.write(req);
    let headerSeen = false;
    this._headerBuf = Buffer.alloc(0);
    this.sock.on('data', (chunk) => {
      if (!headerSeen) {
        this._headerBuf = Buffer.concat([this._headerBuf, chunk]);
        const idx = this._headerBuf.indexOf('\r\n\r\n');
        if (idx !== -1) {
          headerSeen = true;
          const rest = this._headerBuf.subarray(idx + 4);
          if (rest.length) this._process(rest);
          cb();
        }
      } else this._process(chunk);
    });
    this.sock.on('error', (e) => { console.error('ws sock error', e.message); });
  }
  _process(b) {
    this.buf = Buffer.concat([this.buf, b]);
    while (this.buf.length) {
      let off = 0;
      const fin = (this.buf[off] & 0x80) !== 0;
      const opcode = this.buf[off] & 0x0f;
      const masked = (this.buf[off + 1] & 0x80) !== 0;
      let len = this.buf[off + 1] & 0x7f;
      off += 2;
      if (len === 126) { len = this.buf.readUInt16BE(off); off += 2; }
      else if (len === 127) { len = Number(this.buf.readBigUInt64BE(off)); off += 8; }
      const mask = masked ? this.buf.slice(off, off + 4) : null; off += (masked ? 4 : 0);
      if (this.buf.length < off + len) break;
      const payload = this.buf.slice(off, off + len);
      if (masked) for (let i = 0; i < payload.length; i++) payload[i] ^= mask[i % 4];
      this.buf = this.buf.subarray(off + len);
      if (opcode === 0x1) {
        const text = payload.toString('utf8');
        const m = JSON.parse(text);
        if (m.id !== undefined) {
          const h = this.handlers.get(m.id);
          if (h) { this.handlers.delete(m.id); m.error ? h.rej(new Error(JSON.stringify(m.error))) : h.res(m.result); }
        }
      }
    }
  }
  send(obj) {
    const p = Buffer.from(JSON.stringify(obj), 'utf8');
    let header;
    if (p.length < 126) header = Buffer.from([0x81, 0x80 + p.length]);
    else if (p.length < 65536) { header = Buffer.alloc(4); header[0] = 0x81; header[1] = 0x80 + 126; header.writeUInt16BE(p.length, 2); }
    else { header = Buffer.alloc(10); header[0] = 0x81; header[1] = 0x80 + 127; header.writeBigUInt64BE(BigInt(p.length), 2); }
    this.sock.write(Buffer.concat([header, p]));
  }
  call(id, method, params) {
    return new Promise((res, rej) => {
      this.handlers.set(id, { res, rej });
      this.send({ id, method, params: params || {} });
    });
  }
}

const fileUrl = url.pathToFileURL(process.argv[2]).href;
const outFile = process.argv[3] || 'smoke-report.txt';
const refPath = process.argv[4];

const chrome = spawn(CHROME, [
  '--headless=new', '--no-sandbox', '--disable-gpu',
  `--remote-debugging-port=${PORT}`, '--no-first-run',
  '--no-default-browser-check', '--allow-file-access-from-files',
  'about:blank',
], { stdio: 'ignore' });

let ws = null;
async function main() {
  let ok = false;
  for (let i = 0; i < 60 && !ok; i++) {
    await sleep(250);
    try { await getJSON(`http://127.0.0.1:${PORT}/json`); ok = true; } catch (_) {}
  }
  if (!ok) throw new Error('chrome devtools not listening');
  const targets = await getJSON(`http://127.0.0.1:${PORT}/json`);
  const pageTarget = targets.find(t => t.type === 'page') || targets[0];
  const wsUrl = new URL(pageTarget.webSocketDebuggerUrl);
  ws = new WS();
  await new Promise((res, rej) => ws.connect(wsUrl.host, 80, wsUrl.pathname, res));
  await ws.call(1, 'Page.enable');
  await ws.call(2, 'Runtime.enable');
  await ws.call(3, 'Emulation.setDeviceMetricsOverride', { width: 1200, height: 900, deviceScaleFactor: 1, mobile: false })
    .catch(() => {});

  // navigate — await loadEventFired by polling readyState
  await ws.call(4, 'Page.navigate', { url: fileUrl });
  for (let i = 0; i < 40; i++) {
    await sleep(250);
    const rs = await ws.call(500 + i, 'Runtime.evaluate', { expression: 'document.readyState', returnByValue: true });
    if (rs.result && rs.result.value === 'complete') break;
  }
  await sleep(200);

  let nid = 1000;
  const runJS = async (expression) => {
    const r = await ws.call(++nid, 'Runtime.evaluate', { expression, returnByValue: true });
    if (r.exceptionDetails) throw new Error('js: ' + JSON.stringify(r.exceptionDetails));
    if (r.result && r.result.subtype === 'error') throw new Error('js val-err ' + r.result.description);
    return r.result && r.result.value;
  };

  const logs = [];
  // data check
  const dataJSON = await runJS(`(() => {
    const out = [];
    document.querySelectorAll('ul.trait-list').forEach(ul => {
      const l = [];
      ul.querySelectorAll('li.trait').forEach(li => l.push([li.querySelector('.label').textContent.trim(), li.dataset.type]));
      out.push(l);
    });
    return JSON.stringify(out);
  })()`);
  const mine = JSON.parse(dataJSON);
  const ref = JSON.parse(fs.readFileSync(refPath, 'utf8')).flat();
  const key = (p) => p[0] + '|' + p[1];
  const A = mine.flat(Infinity).map(key).sort().join('\n');
  const B = ref.map(key).sort().join('\n');
  logs.push('lists=' + mine.length + ' flat=' + mine.flat(Infinity).length + '/' + ref.length);
  if (A === B) logs.push('DATA MATCH OK');
  else {
    const sa = new Set(A.split('\n')), sb = new Set(B.split('\n'));
    logs.push('only-in-mine: ' + [...sa].filter(x => !sb.has(x)).slice(0, 6).join('; '));
    logs.push('only-in-ref:  ' + [...sb].filter(x => !sa.has(x)).slice(0, 6).join('; '));
    logs.push('DATA MISMATCH');
  }

  // drag via Input.dispatchMouseEvent
  const rect = await runJS(`(() => {
    const ul = document.querySelector('ul.trait-list');
    const r0 = ul.querySelector('li.trait').getBoundingClientRect();
    const r3 = ul.querySelectorAll('li.trait')[3].getBoundingClientRect();
    return JSON.stringify({ s: [Math.round(r0.x+80), Math.round(r0.y + r0.height/2)], e: [Math.round(r3.x+80), Math.round(r3.y + r3.height/2)] });
  })()`);
  const rr = JSON.parse(rect);
  const mouse = async (type, x, y) => ws.call(++nid, 'Input.dispatchMouseEvent', {
    type, x, y,
    button: 'left', clickCount: type === 'mousePressed' ? 1 : (type === 'mouseReleased' ? 0 : 0),
  });
  await mouse('mouseMoved', rr.s[0], rr.s[1]);
  await mouse('mousePressed', rr.s[0], rr.s[1]);
  for (let i = 1; i <= 16; i++) {
    await mouse('mouseMoved', rr.s[0] + (rr.e[0] - rr.s[0]) * i / 16, rr.s[1] + (rr.e[1] - rr.s[1]) * i / 16);
  }
  await mouse('mouseReleased', rr.e[0], rr.e[1]);
  await sleep(200);
  const afterDrag = await runJS(`(() => {
    const ul = document.querySelector('ul.trait-list');
    return JSON.stringify([...ul.querySelectorAll('li.trait')].map(li => [li.querySelector('.label').textContent.trim(), li.dataset.type, li.querySelector('.rank').textContent.trim()]));
  })()`);
  logs.push('after-drag list1: ' + afterDrag);

  // step through to 8
  for (let i = 0; i < 7; i++) {
    await runJS(`document.querySelector('#btnNext').click()`);
    await sleep(50);
  }
  const step8 = await runJS(`JSON.stringify({ finishHidden: document.querySelector('#btnFinish').hidden, bar: document.querySelector('#progressBar').style.width, active: Array.from(document.querySelectorAll('.pane')).findIndex(p => p.classList.contains('is-active')) })`);
  logs.push('step8: ' + step8);
  const shot1 = await ws.call(++nid, 'Page.captureScreenshot', { format: 'png' });
  fs.writeFileSync('smoke-step8.png', Buffer.from(shot1.data, 'base64'));

  await runJS(`document.querySelector('#btnFinish').click()`);
  await sleep(200);
  const resJSON = await runJS(`(() => {
    const out = {};
    document.querySelectorAll('#resultview .score').forEach(s => {
      out[s.querySelector('.letter').textContent.trim()] = s.querySelector('.val').textContent.trim();
    });
    return JSON.stringify({ visible: document.querySelector('#resultview').classList.contains('is-active'), testviewHidden: document.querySelector('#testview').style.display === 'none', scores: out, topType: (document.querySelector('#resultview .score.is-top')||{querySelector:()=>null}).querySelector('.letter')?.textContent.trim()||null });
  })()`);
  logs.push('result: ' + resJSON);
  const shot2 = await ws.call(++nid, 'Page.captureScreenshot', { format: 'png', captureBeyondViewport: true });
  fs.writeFileSync('smoke-result.png', Buffer.from(shot2.data, 'base64'));

  fs.writeFileSync(outFile, logs.join('\n') + '\n');
  console.log(logs.join('\n'));
}

main().then(() => { chrome.kill('SIGTERM'); process.exit(0); })
      .catch(e => { console.error('ERR', e && e.message || e); chrome.kill('SIGTERM'); process.exit(2); });
