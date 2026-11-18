#!/usr/bin/env python3
# CDP driver for headless Chrome: load index.html, drive the UI, assert result.
import asyncio, json, subprocess, sys, time
from http.client import HTTPConnection
import websockets
import os

BASE = os.environ.get("BASE", "/home/dp/MyProjects/disc/.tmpwork/disc-pi-142bw98t/run")
URL = "file://" + os.path.join(BASE, "index.html")
PORT = 9233

class Cdp:
    def __init__(self, ws):
        self.ws = ws
        self.msg_id = 1
        self.pending = {}   # id -> {future}
        self.errors = []
        self.infos = []
        self.events = asyncio.Queue()
        self.reader_task = None
    async def _reader(self):
        try:
            while True:
                raw = await self.ws.recv()
                msg = json.loads(raw)
                if "id" in msg and msg.get("id") in self.pending:
                    fid = msg["id"]
                    fut = self.pending.pop(fid)
                    if not fut.done():
                        if "error" in msg and msg.get("error"):
                            fut.set_exception(Exception(msg["error"].get("message","?")))
                        else:
                            fut.set_result(msg)
                elif msg.get("type") == "event":
                    m = msg.get("params", {})
                    kind = m.get("method")
                    if kind == "Runtime.consoleAPICalled":
                        p = m.get("result")
                        sev = p.get("level", "info")
                        text = p.get("message", "")
                        (self.errors if sev == "error" else self.infos).append(text)
                        print("[CONSOLE %s] %s" % (sev, text))
                    elif kind == "Runtime.exceptionThrown":
                        p = m.get("exceptionDetail")
                        self.errors.append(str(p.get("exceptionMessage","")) + str(p.get("location")))
                        print("[EXCEPTION] %s" % p.get("exceptionMessage"))
                    else:
                        self.events.put_nowait(msg)
        except Exception as e:
            pass
    async def send(self, method, params=None):
        req = {"id": self.msg_id, "method": method, "params": params or {}}
        fid = self.msg_id
        self.msg_id += 1
        self.pending[fid] = asyncio.Future()
        await self.ws.send(json.dumps(req))
        return await asyncio.wait_for(self.pending[fid], 30)
    def close(self):
        if self.reader_task:
            self.reader_task.cancel()

async def get_ws_url(port):
    for _ in range(80):
        try:
            c = HTTPConnection("127.0.0.1", port)
            c.request("GET", "/json")
            res = c.getresponse().read().decode()
            data = json.loads(res)
            for d in data:
                if d.get("type") == "page":
                    return d.get("webSocketDebuggerUrl" or "wsUrl")
            # fallback: first with webSocketDebuggerUrl
            for d in data:
                if d.get("webSocketDebuggerUrl"):
                    return d["webSocketDebuggerUrl"]
        except Exception:
            pass
        time.sleep(0.2)
    raise RuntimeError("no page on /json")

async def main():
    proc = subprocess.Popen([
        "google-chrome-stable","--headless=new","--no-sandbox","--disable-gpu",
        "--remote-debugging-port=%d"%PORT,"--window-size=1200,900",
        "--disable-dev-shm-usage", URL],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    ws_url = await get_ws_url(PORT)
    ws = await websockets.connect(ws_url)
    cdp = Cdp(ws)
    cdp.reader_task = asyncio.create_task(cdp._reader())
    await cdp.send("Page.enable")
    await cdp.send("Runtime.enable")

    async def evaljs(expr):
        r = await cdp.send("Runtime.evaluate", {"expression": expr, "returnByValue": True})
        if "error" in r and r.get("error"):
            raise RuntimeError("JS error: " + str(r["error"]).replace("{\'message\': ", "") )
        res = r.get("result")
        while isinstance(res, dict) and "result" in res and "value" not in res:
            res = res["result"]
        if isinstance(res, dict) and "value" in res:
            return res["value"]
        return res

    await asyncio.sleep(1.5)

    # 1) Click open
    await evaljs("document.querySelector('.btn-open').click()")
    await asyncio.sleep(0.2)

    open_state = await evaljs("document.getElementById('wizardmodal').classList.contains('is-open')")
    item_count = await evaljs("document.querySelectorAll('.disc-item').length")
    print("modal open:", open_state)
    print("disc-items:", item_count)
    assert open_state, "modal should open"
    assert item_count == 96, "expected 96 items, got %s" % item_count

    # 3) Drive to step 8 (index 7)
    await evaljs("document.querySelectorAll('.disc-tab')[7].click()")
    await asyncio.sleep(0.2)
    print("finish visible (true):", await evaljs("!document.getElementById('btnFinish').hidden"))
    print("next hidden (true):", await evaljs("document.getElementById('btnNext').hidden"))

    # 4) REORDER: 'd'->top, 's'->bottom in each list. Expected: D+24, S-24.
    await evaljs("""
    (function(){
      Array.from(document.querySelectorAll('.disc-list')).forEach(function(ul){
        var lis = Array.from(ul.children);
        var top = lis.filter(function(x){return x.dataset.type==='d';})[0];
        var bot = lis.filter(function(x){return x.dataset.type==='s';})[0];
        if(top){ ul.insertBefore(top, ul.firstChild); }
        if(bot){ ul.appendChild(bot); }
      });
    })()
    """)
    result = await evaljs("""
    (function(){
      var d={D:0,I:0,S:0,C:0};
      Array.from(document.querySelectorAll('.disc-list')).forEach(function(ul){
        Array.from(ul.children).forEach(function(li,pos){
          var t = (li.dataset.type||'').toUpperCase();
          if(pos===0) d[t]=(d[t]||0)+1;
          else if(pos===3) d[t]=(d[t]||0)-1;
        });
      });
      return d;
    })()
    """)
    print("simulated scores (expect D24,S-24,I0,C0):", result)
    orders = await evaljs("Array.from(document.querySelectorAll('.disc-list')).map(function(ul){ return Array.from(ul.children).map(function(li){ return li.dataset.type; }); })")
    print("ORDERS:", orders)
    good = sum(1 for o in orders if o and o[0] == 'd' and o[3] == 's')
    print("lists with d@top,s@bottom:", good, "of", len(orders))
    # 5) Finish -> showResult
    await evaljs("document.getElementById('btnFinish').click()")
    await asyncio.sleep(0.3)
    diag = await evaljs("""
      (function(){
        try{
          var el = function(id){ return document.getElementById(id); };
          var cs = function(e){ return e ? getComputedStyle(e).display : '?'; };
          return {lists: document.querySelectorAll('.disc-list').length,
                  resultHidden: el('discResult').hidden,
                  resultDisplay: cs(el('discResult')),
                  resultScore: (el('discResultScore')? el('discResultScore').textContent : '(no)'),
                  rootDisplay: cs(el('discRoot')),
                  tabsDisplay: cs(el('discTabs')) || 'n/a',
                  actionsDisplay: cs(el('discActions'))}
        }catch(e){ return {err: e.name+': '+e.message}; }
      })()
    """)
    print("DIAG:", repr(diag))
    flags = await evaljs("JSON.stringify({fh:window.__fh||null,sr:window.__sr||null,srOk:window.__srOk,srDone:window.__srDone,gerr:window.__gerr||[]})")
    print("DEBUG FLAGS:", flags)
    await asyncio.sleep(0.3)
    cdp.reader_task.cancel()
    print("=== CONSOLE ERRORS right after finish: %d ===" % len(cdp.errors))
    for e in cdp.errors: print("  [ERR]", e)
    if cdp.errors:
        print("(errors found; stopping)")
        await ws.close()
        proc.terminate()
        try: proc.wait(timeout=5)
        except: pass
        return
    cdp.errors.clear()
    # re-attach reader (it was cancelled)
    cdp.reader_task = asyncio.create_task(cdp._reader())
    await asyncio.sleep(0.2)

    score = await evaljs("document.getElementById('discResultScore').textContent")
    dom = await evaljs("document.getElementById('discResultDominant').textContent")
    types = await evaljs("""
      Array.from(document.querySelectorAll('.disc-type')).map(function(el){
        return {code: el.querySelector('.disc-type__code').textContent,
                value: el.querySelector('.disc-type__value').textContent,
                name: el.querySelector('.disc-type__name').textContent,
                dominant: el.classList.contains('is-dominant')};
      })
    """)
    hidden_result = await evaljs("document.getElementById('discResult').hidden")
    print("RESULT hidden:", hidden_result)
    print("SCORE:", repr(score))
    print("DOMINANT:", repr(dom))
    for tt in types:
        print("  ", tt)

    # console errors
    await asyncio.sleep(0.2)
    cdp.reader_task.cancel()
    print("=== CONSOLE ERRORS (final): %d ===" % len(cdp.errors))
    for e in cdp.errors:
        print("  [ERR] %s" % e)
    print("=== CONSOLE INFO: %d ===" % len(cdp.infos))
    for i in cdp.infos:
        print("  [INFO] %s" % i)

    # Assert
    assert not hidden_result, "result should be visible"
    assert "D: 24" in score, "score: %r" % score
    assert "S: -24" in score, "score: %r" % score
    assert "D" in dom, "dominant: %r" % dom
    tdict = {t['code']: t for t in types}
    assert tdict['D']['value'] == '24', tdict
    assert tdict['S']['value'] == '-24', tdict
    assert tdict['D']['dominant'], "D not dominant"
    assert not any(t['dominant'] for t in types if t['code'] != 'D'), "only D dominant"
    assert set(tdict) == {'D','I','S','C'}, set(tdict)

    print("ALL DOM ASSERTIONS PASSED")
    await ws.close()
    proc.terminate()
    try: proc.wait(timeout=5)

    except Exception: proc.kill()

if __name__ == "__main__":
    asyncio.run(main())
