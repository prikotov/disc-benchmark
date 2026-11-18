import puppeteer from "puppeteer-core";

const file = "file:///home/dp/MyProjects/disc/.tmpwork/disc-pi-dkhbddwt/run/index.html";

const browser = await puppeteer.launch({
  executablePath: "/usr/bin/google-chrome",
  headless: "new",
  args: ["--no-sandbox", "--disable-gpu"],
});
const page = await browser.newPage();
const errors = [];
page.on("pageerror", (e) => errors.push("PAGEERROR: " + e.message));
page.on("console", (m) => { if (m.type() === "error") errors.push("CONSOLE: " + m.text()); });

await page.goto(file, { waitUntil: "networkidle0" });

const info = await page.evaluate(() => ({
  tabs: document.querySelectorAll("#tabs .tab").length,
  panes: document.querySelectorAll("#panes .pane").length,
  lists: document.querySelectorAll(".list").length,
  items: document.querySelectorAll(".item").length,
  activePane: document.querySelector(".pane.is-active")?.dataset.stepPane,
  prevDisabled: document.getElementById("btnPrev").disabled,
  finishHidden: document.getElementById("btnFinish").hidden,
}));
console.log("INIT", JSON.stringify(info));

// --- step 8: next buttons ---
for (let i = 1; i < 7; i++) await page.click("#btnNext");
const step7 = await page.evaluate(() => ({
  activePane: document.querySelector(".pane.is-active")?.dataset.stepPane,
  nextHidden: document.getElementById("btnNext").hidden,
  finishVisible: !document.getElementById("btnFinish").hidden,
  activeTab: [...document.querySelectorAll(".tab")].findIndex(t => t.classList.contains("is-active")),
}));
console.log("STEP7", JSON.stringify(step7));

// --- simulate a drag: reorder first list of pane 1 (currently back on step 8) ---
await page.evaluate(() => {
  document.querySelectorAll("#tabs .tab")[0].click();
});
const drag = await page.evaluate(() => {
  const ul = document.querySelector(".list");
  const items = [...ul.querySelectorAll(":scope > li")];
  const types = items.map(li => li.dataset.type);
  const target = items[0];
  const r = target.getBoundingClientRect();

  function pe(el, type, x, y) {
    el.dispatchEvent(new PointerEvent(type, {
      bubbles: true, cancelable: true, pointerId: 1, pointerType: "mouse",
      clientX: x, clientY: y, button: 0, buttons: type === "pointermove" ? 1 : 0,
    }));
  }
  const startX = r.left + 20, startY = r.top + r.height / 2;
  // destination: middle of 4th item
  const dest = items[3].getBoundingClientRect();
  pe(target, "pointerdown", startX, startY);
  const steps = 8;
  for (let i = 1; i <= steps; i++) {
    const x = startX + (dest.left - startX) * i / steps;
    const y = startY + (dest.top + dest.height / 2 - startY) * i / steps;
    pe(target, "pointermove", x, y);
  }
  pe(target, "pointerup", dest.left + 10, dest.top + dest.height / 2);
  return { before: types, after: [...ul.querySelectorAll(":scope > li")].map(li => li.dataset.type) };
});
console.log("DRAG", JSON.stringify(drag));

// --- finish & check scores ---
// after drag: list0 type order changed: item that was pos0 now pos3
await page.evaluate(() => {
  for (let i = 0; i < 7; i++) document.getElementById("btnNext").click();
  document.getElementById("btnFinish").click();
});
const res = await page.evaluate(() => ({
  resultsVisible: document.getElementById("results").classList.contains("is-active"),
  d: document.querySelectorAll("#scores .score")[0]?.querySelector(".score__value").textContent,
  i: document.querySelectorAll("#scores .score")[1]?.querySelector(".score__value").textContent,
  s: document.querySelectorAll("#scores .score")[2]?.querySelector(".score__value").textContent,
  c: document.querySelectorAll("#scores .score")[3]?.querySelector(".score__value").textContent,
  dBefore: document.querySelector(".list li").dataset.type,
}));

// expected d score = (maj d) - (min d). Only list0 changed: originally d at index 2 (pos2, no score),
// now list0 order: [original[1], 1, 2, 0]? compute from drag.after
const orig0 = ["i","c","d","s"];
const after0 = drag.after;
const dExp = (after0[0] === "d" ? 1 : 0) - (after0[3] === "d" ? 1 : 0);
console.log("RESULT", JSON.stringify(res), "expected d =", dExp);

// --- restart ---
await page.click("#btnRestart");
const afterRestart = await page.evaluate(() => ({
  resultsVisible: document.getElementById("results").classList.contains("is-active"),
  firstList: [...document.querySelectorAll(".list")[0].querySelectorAll(":scope > li")].map(li => li.dataset.type),
  activeTab: [...document.querySelectorAll("#tabs .tab")].findIndex(t => t.classList.contains("is-active")),
}));
console.log("RESTART", JSON.stringify(afterRestart));

console.log("ERRORS", JSON.stringify(errors));
await browser.close();
