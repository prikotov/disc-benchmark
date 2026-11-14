#!/usr/bin/env python3
import asyncio, json, subprocess, sys, time
import websockets
from http.client import HTTPConnection

URL = "file:///home/dp/MyProjects/disc/.tmpwork/disc-pi-142bw98t/run/index.html"
PORT = 9400

async def main():
    proc = subprocess.Popen([
        "google-chrome-stable","--headless=new","--no-sandbox","--disable-gpu",
        "--remote-debugging-port=%d"%PORT,"--window-size=1200,900","--disable-dev-shm-usage",URL],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    ws_url = None
    for _ in range(120):
        try:
            c = HTTPConnection("127.0.0.1", PORT)
            c.request("GET", "/json")
            data = json.loads(c.getresponse().read())
            pages = [d for d in data if d.get("type") == "page"]
            if pages:
                ws_url = pages[0]["webSocketDebuggerUrl"]
                break
        except Exception:
            pass
        time.sleep(0.2)
    if not ws_url:
        print("NO PAGE FOUND"); proc.terminate(); return 1
    print("page ws url:", ws_url)
    ws = await websockets.connect(ws_url)
    next_id = 0
    async def send(method, params=None):
        nonlocal next_id
        next_id += 1
        rid = next_id
        await ws.send(json.dumps({"id": rid, "method": method, "params": params or {}}))
        while True:
            raw = await asyncio.wait_for(ws.recv(), 15)
            msg = json.loads(raw)
            if msg.get("id") == rid:
                return msg
            # otherwise it's an unsolicited event; skip
    r = await send("Page.enable");  print("Page.enable:", r)
    r = await send("Runtime.enable"); print("Runtime.enable:", r)
    r = await send("Runtime.evaluate", {"expression": "1+1", "returnByValue": True}); print("1+1:", r)
    r = await send("Runtime.evaluate", {"expression": "document.querySelectorAll('.disc-item').length", "returnByValue": True}); print("disc-items:", r)
    await ws.close()
    proc.terminate()
    return 0

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
