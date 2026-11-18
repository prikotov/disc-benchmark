#!/usr/bin/env python3
# CDP drag-to-rank smoke test: dispatch synthetic PointerEvents to exercise the drag handlers.
import asyncio, subprocess, sys, os, json
from websockets import connect as ws_connect
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cdp_test import Cdp, get_ws_url, BASE, PORT

DRAG_JS = """JSON.stringify((function(){
  var ul = document.querySelector('#rootwizard .disc-list');
  var top = ul.children[0];
  var bot = ul.children[ul.children.length-1];
  var tr = top.getBoundingClientRect(), br = bot.getBoundingClientRect();
  var cx = tr.left + tr.width/2;
  var cyTop = tr.top + tr.height/2;
  var cyBot = br.top + br.height + 15;
  var before = Array.from(ul.children).map(function(li){return li.getAttribute('data-type');});
  function fire(t,x,y,type){
    t.dispatchEvent(new PointerEvent(type,{clientX:x,clientY:y,button:0,pointerId:1,bubbles:true,cancelable:true,pressure:1}));
  }
  fire(top,cx,cyTop,'pointerdown');
  fire(document,cx,cyBot,'pointermove');
  fire(document,cx,cyBot,'pointerup');
  var after = Array.from(ul.children).map(function(li){return li.getAttribute('data-type');});
  return {before:before, after:after};
}()))"""

async def main():
    port = int(os.environ.get("CDP_PORT", PORT))
    proc = subprocess.Popen(["google-chrome","--headless=new","--no-sandbox",
        "--disable-gpu","--disable-dev-shm-usage","--start-maximized",
        "--no-first-run","--no-default-browser-check","--disable-extensions",
        f"--remote-debugging-port={port}",
        "file://" + BASE + "/index.html"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    ws = await ws_connect(await get_ws_url(port))
    cdp = Cdp(ws)
    cdp.reader_task = asyncio.create_task(cdp._reader())
    await cdp.send("Page.navigate", {"url":"file://" + BASE + "/index.html"})
    await asyncio.sleep(2.0)

    async def evaljs(expr):
        r = await cdp.send("Runtime.evaluate", {"expression": expr, "returnByValue": True})
        if "error" in r and r.get("error"):
            raise RuntimeError("JS error: " + str(r["error"]).replace("{'message': ", ""))
        res = r.get("result")
        while isinstance(res, dict) and "result" in res and "value" not in res:
            res = res["result"]
        if isinstance(res, dict) and "value" in res:
            return res["value"]
        return res

    await evaljs("document.querySelector('[data-modal-open]').click()")
    await asyncio.sleep(0.6)

    # sanity: modal open + 96 items
    open_state = await evaljs("document.getElementById('wizardmodal').classList.contains('is-open')")
    nitems = await evaljs("document.querySelectorAll('.disc-item').length")
    print("modal open:", open_state, " items:", nitems)

    out = await evaljs(DRAG_JS)
    d = json.loads(out)
    print("before:", d["before"])
    print("after :", d["after"])
    changed = d["before"] != d["after"]
    print("ORDER CHANGED (drag worked):", changed)
    print("DRAG TEST PASS" if changed else "DRAG TEST FAIL")

    cdp.close()
    try:
        await ws.recv()
    except Exception:
        pass
    await ws.close()
    proc.terminate()

asyncio.run(main())
