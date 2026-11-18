#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Сборка index.html (одностраничная копия DISC-теста) из study/questions.json.

Вопросы (24 списка x 4 прилагательных с типами d/i/s/c) извлекаются из исходной
страницы источника (study/disc_modal.html -> study/questions.json).
"""
import json
import os
import html

HERE = os.path.dirname(os.path.abspath(__file__))
QUESTIONS = os.path.join(HERE, "study", "questions.json")
OUT = os.path.join(HERE, "index.html")

STEP_LABELS = ["Первый", "Второй", "Третий", "Четвертый",
               "Пятый", "Шестой", "Седьмой", "Восьмой"]


def esc(s):
    return html.escape(s, quote=False)


def build_panes(questions):
    assert len(questions) == 24, len(questions)
    assert len(STEP_LABELS) * 3 == len(questions)
    out = []
    for step, label in enumerate(STEP_LABELS):
        chunk = questions[step * 3: step * 3 + 3]
        cards = []
        for n, q in enumerate(chunk, start=step * 3 + 1):
            lis = "\n".join(
                '              <li class="disc-item" data-type="%s">%s</li>'
                % (it["type"], esc(it["text"]))
                for it in q["items"]
            )
            cards.append(
                '          <div class="disc-card">\n'
                '            <div class="disc-card__title">Я наиболее</div>\n'
                '            <ul class="disc-list" id="draggable-list%d">\n'
                '%s\n'
                '            </ul>\n'
                '            <div class="disc-card__foot">Я наименее</div>\n'
                '          </div>' % (n, lis)
            )
        active = " is-active" if step == 0 else ""
        selected = "true" if step == 0 else "false"
        out.append(
            '        <div class="disc-pane%s" data-step-pane="%d" id="tab%d" role="tabpanel" aria-labelledby="stepBtn%d">\n'
            '          <div class="disc-grid3">\n'
            '%s\n'
            '          </div>\n'
            '        </div>'
            % (active, step, step + 1, step + 1, "\n".join(cards))
        )
    return "\n".join(out)


def build_tabs():
    out = []
    for i, label in enumerate(STEP_LABELS):
        cls = "disc-tab is-active" if i == 0 else "disc-tab"
        sel = "true" if i == 0 else "false"
        out.append(
            '        <button class="%s" id="stepBtn%d" type="button" role="tab" aria-selected="%s" '
            'aria-controls="tab%d" data-step-btn="%d">%s</button>'
            % (cls, i + 1, sel, i + 1, i, label)
        )
    return "\n".join(out)


TEMPLATE = r'''<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="Короткий тест DISC на типы личности (Dominance, Influence, Stability, Compliance). Узнайте свой поведенческий профиль и сильные стороны.">
<title>Пройти тест DISC онлайн бесплатно — Типы личности за 5 минут</title>
<style>
/* ===== базовое ===== */
*,*::before,*::after{box-sizing:border-box}
html,body{margin:0;padding:0}
[hidden]{display:none !important}
body{
  font-family:"Manrope",-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;
  color:#1C1C1C;background:#0D0D0D;-webkit-font-smoothing:antialiased;text-rendering:optimizeLegibility;
}
button{font-family:inherit}
svg{display:block}
html.no-scroll,body.no-scroll{overflow:hidden}
html.dragging-active,html.dragging-active *{cursor:grabbing !important;-webkit-user-select:none;user-select:none}

.container{width:100%;max-width:1200px;margin:0 auto;padding:0 32px}

/* ===== первый экран ===== */
.hero{
  min-height:100vh;display:flex;align-items:center;justify-content:center;
  padding:72px 0 56px;
  background:radial-gradient(1100px 620px at 50% -8%,#18365F 0%,#101a2b 45%,#0D0D0D 78%);
}
.hero__inner{display:flex;flex-direction:column;align-items:center;text-align:center}
.hero__logo{font-size:14px;letter-spacing:.34em;font-weight:800;color:#fff;opacity:.7;text-transform:uppercase}
.hero__eyebrow{
  margin:34px 0 0;color:#6FE28A;font-size:15px;font-weight:700;letter-spacing:.16em;text-transform:uppercase;
}
.hero__title{
  margin:14px 0 0;color:#fff;font-size:clamp(34px,6.4vw,68px);line-height:1.12;letter-spacing:-1px;font-weight:800;
}
.hero__titleBreak{display:block}
.hero__subtitle{margin:16px 0 0;color:#fff;opacity:.86;font-size:clamp(17px,2.4vw,25px);font-weight:500}
.hero__btn{
  margin-top:34px;display:inline-flex;align-items:center;justify-content:center;gap:10px;
  padding:18px 42px;border:0;border-radius:12px;cursor:pointer;
  background:linear-gradient(180deg,#E6EEF9 0%,#C4DDF5 100%);
  color:#044788;font-size:17px;font-weight:700;
  transition:transform .2s ease,box-shadow .2s ease;
}
.hero__btn:hover{transform:translateY(-2px);box-shadow:0 14px 34px rgba(196,221,245,.28)}
.hero__btn:focus-visible{outline:3px solid #6FE28A;outline-offset:3px}
.hero__note{margin:16px 0 0;color:#fff;opacity:.55;font-size:14px}
.hero__types{
  list-style:none;margin:52px 0 0;padding:0;display:grid;grid-template-columns:repeat(4,minmax(0,1fr));
  gap:16px;width:100%;max-width:920px;
}
.hero__types li{
  text-align:left;background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.12);
  border-radius:14px;padding:16px 18px;color:#E7E7E7;font-size:13px;line-height:1.45;
}
.hero__types b{display:block;font-size:26px;line-height:1;color:#6FE28A;margin-bottom:8px}
.hero__types span{display:block;color:#9fb4d0;font-size:12px;margin-top:3px}

/* ===== модалка теста ===== */
.disc-modal{position:fixed;inset:0;z-index:100001;display:none}
.disc-modal.is-open{display:block}
.disc-modal__overlay{position:absolute;inset:0;background:rgba(0,0,0,.55)}
.disc-modal__dialog{
  position:relative;z-index:1;display:flex;flex-direction:column;
  width:min(1240px,calc(100% - 64px));margin:56px auto;max-height:calc(100vh - 112px);
  background:#fff;border-radius:22px;overflow:hidden;
  box-shadow:0 40px 120px rgba(0,0,0,.28);
}
.disc-modal__close{
  position:absolute;top:24px;right:24px;width:48px;height:48px;padding:0;border:0;background:transparent;
  cursor:pointer;opacity:.55;z-index:4;
}
.disc-modal__close::before,.disc-modal__close::after{
  content:"";position:absolute;left:50%;top:50%;width:38px;height:2px;border-radius:2px;background:#7A7A7A;
  transform-origin:center;
}
.disc-modal__close::before{transform:translate(-50%,-50%) rotate(45deg)}
.disc-modal__close::after{transform:translate(-50%,-50%) rotate(-45deg)}
.disc-modal__close:hover{opacity:1}
.disc-modal__close:focus-visible{outline:2px solid #1F5BD6;outline-offset:2px;border-radius:8px}
.disc-modal__head{flex:0 0 auto;padding:48px 56px 18px;text-align:center}
.disc-modal__title{margin:0;color:#0F0F0F;font-size:30px;font-weight:700;line-height:1.2}
.disc-modal__sub{margin-top:8px;color:#272727;font-size:18px}
.disc-modal__lead{margin-top:22px;color:#409C54;font-size:22px}
.disc-modal__tabs{
  flex:0 0 auto;display:flex;gap:8px;justify-content:center;padding:0 56px 8px;
}
.disc-tab{
  border:0;background:#EAF2FA;color:#2C2C2C;border-radius:10px;padding:14px 18px;
  font-size:22px;line-height:1;cursor:pointer;white-space:nowrap;
}
.disc-tab.is-active{background:#1F5BD6;color:#fff}
.disc-tab:focus-visible{outline:2px solid #1F5BD6;outline-offset:2px}
.disc-modal__body{
  flex:1 1 auto;min-height:0;overflow-y:auto;overflow-x:hidden;padding:16px 56px 28px;
  background:#fff;-webkit-overflow-scrolling:touch;overscroll-behavior:contain;
  scrollbar-width:none;-ms-overflow-style:none;
}
.disc-modal__body::-webkit-scrollbar{width:0;height:0}
.disc-foot{flex:0 0 auto;background:#fff;padding-bottom:16px}
.disc-pane{display:none}
.disc-pane.is-active{display:block}
.disc-grid3{display:grid;grid-template-columns:repeat(3,1fr);gap:26px;margin-top:18px}
.disc-card{border:1px solid rgba(0,0,0,.18);border-radius:10px;overflow:hidden;background:#fff}
.disc-card__title{padding:16px 18px;font-size:26px;font-weight:800;color:#1C1C1C}
.disc-card__foot{padding:16px 18px;font-size:24px;font-weight:800;color:#1C1C1C}
.disc-list{list-style:none;margin:0 20px;padding:0;border:1px solid rgba(0,0,0,.12);background:#fff}
.disc-item{
  position:relative;padding:18px 48px 18px 18px;font-size:20px;line-height:1.35;color:#2C2C2C;
  border-top:1px solid rgba(0,0,0,.12);cursor:grab;user-select:none;-webkit-user-select:none;
  background:#fff;touch-action:pan-y;
}
.disc-item:first-child{border-top:0}
.disc-item:focus-visible{outline:2px solid #1F5BD6;outline-offset:-2px}
.disc-handle{
  position:absolute;right:12px;top:50%;transform:translateY(-50%);
  width:28px;height:28px;display:flex;align-items:center;justify-content:center;
  cursor:grab;user-select:none;-webkit-user-select:none;touch-action:none;opacity:.75;
}
.disc-handle:hover{opacity:1}
.disc-handle svg{width:16px;height:16px;display:block;pointer-events:none}
.disc-item.is-dragging{opacity:.55}
.disc-item.is-dragging .disc-handle{cursor:grabbing}
.disc-item.is-over{outline:2px dashed rgba(31,91,214,.45);outline-offset:-6px}
.disc-list.is-reordering{touch-action:none}
.disc-progress{margin:16px 56px 0;height:18px;border-radius:999px;background:rgba(0,0,0,.08);overflow:hidden}
.disc-progress__bar{height:100%;width:0;border-radius:999px;background:#6FE28A;transition:width .2s ease}
.disc-actions{margin:16px 56px 0;display:flex;justify-content:space-between;align-items:center;gap:12px}
.disc-btn{
  border:1px solid rgba(0,0,0,.22);border-radius:999px;padding:16px 42px;font-size:24px;line-height:1;
  cursor:pointer;background:#fff;color:#1C1C1C;
}
.disc-btn--primary{border-color:transparent;background:#3A944A;color:#fff}
.disc-btn:disabled{opacity:.45;cursor:not-allowed}
.disc-btn:focus-visible{outline:2px solid #1F5BD6;outline-offset:2px}

/* ===== результат ===== */
.disc-result{
  flex:1 1 auto;min-height:0;overflow-y:auto;padding:0 56px 40px;background:#fff;
  -webkit-overflow-scrolling:touch;overscroll-behavior:contain;
}
.disc-result__head{padding-left:0;padding-right:0}
.disc-result__score{
  margin-top:4px;padding:24px 18px;border:1px solid rgba(0,0,0,.08);border-radius:14px;
  background:linear-gradient(180deg,#F6F9FC 0%,#EEF4FA 100%);
  text-align:center;font-size:clamp(24px,3.6vw,40px);font-weight:800;color:#101010;
  letter-spacing:.5px;
}
.scorebars{margin-top:26px;display:flex;flex-direction:column;gap:12px}
.scorebar{display:grid;grid-template-columns:26px 1fr 62px;align-items:center;gap:14px;font-size:17px}
.scorebar__key{font-weight:800}
.scorebar__track{position:relative;height:22px;background:#F1F3F5;border:1px solid rgba(0,0,0,.06);border-radius:6px;overflow:hidden}
.scorebar__track::before{content:"";position:absolute;left:50%;top:0;bottom:0;width:1px;background:rgba(0,0,0,.28)}
.scorebar__fill{position:absolute;top:0;bottom:0;border-radius:4px;min-width:0}
.scorebar__val{text-align:right;font-variant-numeric:tabular-nums;font-weight:700}
.disc-result__legend{margin-top:26px;display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px}
.legend-card{border:1px solid rgba(0,0,0,.14);border-radius:10px;padding:14px 16px}
.legend-card b{display:block;font-size:24px;line-height:1}
.legend-card i{display:block;font-style:normal;margin-top:6px;font-weight:700;font-size:15px}
.legend-card em{display:block;margin-top:2px;font-style:normal;font-size:12px;color:#7A7A7A}
.legend-card p{margin:8px 0 0;font-size:13px;line-height:1.45;color:#444}
.disc-result__note{margin:22px 0 0;font-size:15px;line-height:1.55;color:#555}
.disc-result__actions{margin-top:26px;display:flex;justify-content:space-between;align-items:center;gap:12px}

/* ===== адаптив ===== */
@media (max-width:1100px){
  .disc-modal__dialog{width:calc(100% - 24px);margin:12px auto;max-height:calc(100vh - 24px)}
  .disc-modal__head{padding:28px 18px 12px}
  .disc-modal__title{font-size:30px}
  .disc-modal__lead{font-size:20px;margin-top:14px}
  .disc-modal__sub{font-size:16px}
  .disc-modal__tabs{
    justify-content:flex-start;gap:10px;padding:0 18px 12px;
    overflow-x:auto;overflow-y:hidden;scroll-behavior:smooth;scroll-snap-type:x proximity;
    scroll-padding-left:18px;scroll-padding-right:18px;-webkit-overflow-scrolling:touch;
  }
  .disc-modal__tabs::-webkit-scrollbar{height:0}
  .disc-tab{flex:0 0 auto;font-size:18px;padding:12px 14px;scroll-snap-align:start}
  .disc-modal__body{padding:12px 18px 24px}
  .disc-grid3{grid-template-columns:1fr;gap:14px}
  .disc-progress{margin:14px 18px 0}
  .disc-actions{margin:14px 18px 0}
  .disc-result{padding:0 18px 28px}
  .disc-result__legend{grid-template-columns:repeat(2,minmax(0,1fr))}
}
@media (max-width:760px){
  .hero__types{grid-template-columns:repeat(2,minmax(0,1fr))}
}
@media (max-width:640px){
  .container{padding:0 18px}
  /* не даём заголовку залезать под крестик */
  .disc-modal__head{padding:26px 54px 12px 18px}
  .disc-modal__close{width:40px;height:40px;top:14px;right:14px}
  .disc-modal__close::before,.disc-modal__close::after{width:30px}
  .disc-modal__title{font-size:26px}
  .disc-card__title{font-size:20px;padding:14px 16px}
  .disc-card__foot{font-size:19px;padding:14px 16px}
  .disc-list{margin:0 12px}
  .disc-item{font-size:17px;padding:14px 44px 14px 14px}
  .disc-btn{font-size:20px;padding:14px 26px}
}
@media (max-width:520px){
  .disc-actions,.disc-result__actions{flex-direction:column-reverse;align-items:stretch}
  .disc-btn{width:100%}
  .disc-result__legend{grid-template-columns:1fr}
  .scorebar{grid-template-columns:22px 1fr 54px;gap:10px;font-size:15px}
}
</style>
</head>
<body>

<main class="hero">
  <div class="container hero__inner">
    <div class="hero__logo">Stratoplan</div>
    <p class="hero__eyebrow">Бесплатный тест</p>
    <h1 class="hero__title">Бесплатный тест DISC <span class="hero__titleBreak">для руководителей</span></h1>
    <p class="hero__subtitle">Определите ваш управленческий стиль за 5 минут</p>
    <button class="hero__btn" id="openTest" type="button" aria-controls="wizardmodal" aria-expanded="false">Пройти онлайн-тест</button>
    <p class="hero__note">Работает офлайн: результаты никуда не отправляются и не сохраняются.</p>
    <ul class="hero__types">
      <li><b>D</b>Доминирование<span>Dominance</span></li>
      <li><b>I</b>Влияние<span>Influence</span></li>
      <li><b>S</b>Стабильность<span>Stability</span></li>
      <li><b>C</b>Соответствие<span>Compliance</span></li>
    </ul>
  </div>
</main>

<!-- DISC MODAL -->
<div class="disc-modal" id="wizardmodal" aria-hidden="true">
  <div class="disc-modal__overlay" data-disc-close></div>

  <div class="disc-modal__dialog" role="dialog" aria-modal="true" aria-labelledby="discTitle">
    <button class="disc-modal__close" type="button" data-disc-close aria-label="Закрыть"></button>

    <div class="disc-modal__head" id="wizardHead">
      <h2 class="disc-modal__title" id="discTitle">Тестирование DISC</h2>
      <div class="disc-modal__sub">Помните - чем честнее вы с тестом, тем точнее результаты!</div>
      <div class="disc-modal__lead">Разместите блоки в порядке от наиболее похожего на вас до наименее похожего</div>
    </div>

    <div class="disc-modal__tabs" id="wizardTabs" role="tablist" aria-label="Шаги">
__TABS__
    </div>

    <div class="disc-modal__body" id="wizardBody">
      <div id="rootwizard" data-step="0">
__PANES__
      </div>
    </div>

    <div class="disc-foot" id="wizardFoot">
      <div class="disc-progress" aria-hidden="true">
        <div class="disc-progress__bar" id="discProgress"></div>
      </div>
      <div class="disc-actions">
        <button class="disc-btn disc-btn--ghost" type="button" data-disc-prev>Назад</button>
        <button class="disc-btn disc-btn--primary" type="button" data-disc-next>Далее</button>
        <button class="disc-btn disc-btn--primary" type="button" data-disc-finish hidden>Завершить тест</button>
      </div>
    </div>

    <section class="disc-result" id="resultView" hidden aria-label="Результаты теста">
      <div class="disc-modal__head disc-result__head">
        <h2 class="disc-modal__title">Ваш DISC-профиль:</h2>
        <div class="disc-modal__sub">Тест завершён. Результат посчитан прямо в браузере и никуда не отправляется.</div>
      </div>

      <div class="disc-result__score" id="scoreLine">D:0, I:0, S:0, C:0</div>

      <div class="scorebars" id="scoreBars"></div>

      <div class="disc-result__legend" id="scoreLegend"></div>

      <p class="disc-result__note">Как считается балл: в каждом из 24 списков прилагательных слово, стоящее первым («Я наиболее»), даёт своему типу +1, слово последним («Я наименее») — −1. Итог по типу D, I, S или C — разница таких отметок за все списки; поэтому сумма четырёх баллов всегда равна нулю. DISC описывает поведенческие предпочтения, а не оценку способностей.</p>

      <div class="disc-result__actions">
        <button class="disc-btn disc-btn--ghost" type="button" data-disc-restart>Пройти тест заново</button>
        <button class="disc-btn disc-btn--primary" type="button" data-disc-close>Закрыть</button>
      </div>
    </section>
  </div>
</div>

<script>
(function () {
  "use strict";

  var qs = function (s, r) { return (r || document).querySelector(s); };
  var qsa = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };

  var modal = qs("#wizardmodal");
  if (!modal) return;

  var wizardHead = qs("#wizardHead", modal);
  var wizardTabs = qs("#wizardTabs", modal);
  var wizardBody = qs("#wizardBody", modal);
  var wizardFoot = qs("#wizardFoot", modal);
  var resultView = qs("#resultView", modal);

  var tabs = qsa("[data-step-btn]", modal);
  var panes = qsa("[data-step-pane]", modal);
  var btnPrev = qs("[data-disc-prev]", modal);
  var btnNext = qs("[data-disc-next]", modal);
  var btnFinish = qs("[data-disc-finish]", modal);
  var progressEl = qs("#discProgress", modal);
  var btnOpen = qs("#openTest");

  var STEP_COUNT = panes.length || 8;
  var step = 0;
  var finished = false;
  var lastFocus = null;

  /* ---------- блокировка скролла страницы ---------- */
  function syncScrollLock() {
    var open = modal.classList.contains("is-open");
    document.documentElement.classList.toggle("no-scroll", open);
    document.body.classList.toggle("no-scroll", open);
  }

  /* ---------- отрисовка шага ---------- */
  function render() {
    tabs.forEach(function (t) {
      var on = Number(t.getAttribute("data-step-btn")) === step;
      t.classList.toggle("is-active", on);
      t.setAttribute("aria-selected", on ? "true" : "false");
    });
    panes.forEach(function (p) {
      p.classList.toggle("is-active", Number(p.getAttribute("data-step-pane")) === step);
    });
    if (btnPrev) btnPrev.disabled = step === 0;
    if (btnNext) btnNext.hidden = step === STEP_COUNT - 1;
    if (btnFinish) btnFinish.hidden = step !== STEP_COUNT - 1;
    if (progressEl) progressEl.style.width = ((step + 1) / STEP_COUNT) * 100 + "%";
    var root = qs("#rootwizard", modal);
    if (root) root.setAttribute("data-step", String(step));
  }

  function scrollByOptions(node, opts) {
    var left = Object.prototype.hasOwnProperty.call(opts, "left") ? opts.left : null;
    var top = Object.prototype.hasOwnProperty.call(opts, "top") ? opts.top : null;
    if (typeof node.scrollTo === "function") {
      try {
        node.scrollTo(opts);
        return;
      } catch (err) { /* старые браузеры: обычные числовые значения */ }
    }
    if (left !== null) node.scrollLeft = left;
    if (top !== null) node.scrollTop = top;
  }

  function centerActiveTab() {
    if (!wizardTabs || !wizardTabs.scrollWidth) return;
    var active = tabs.filter(function (t) {
      return Number(t.getAttribute("data-step-btn")) === step;
    })[0];
    if (!active) return;
    var cRect = wizardTabs.getBoundingClientRect();
    var tRect = active.getBoundingClientRect();
    var target = wizardTabs.scrollLeft + (tRect.left - cRect.left) + tRect.width / 2 - cRect.width / 2;
    var max = Math.max(0, wizardTabs.scrollWidth - wizardTabs.clientWidth);
    var left = Math.min(Math.max(0, target), max);
    if (Math.abs(wizardTabs.scrollLeft - left) < 2) return;
    scrollByOptions(wizardTabs, { left: left, behavior: "smooth" });
  }

  function scrollBodyTop() {
    if (!wizardBody) return;
    scrollByOptions(wizardBody, { top: 0, behavior: "smooth" });
  }

  function setStep(n) {
    var next = Math.max(0, Math.min(STEP_COUNT - 1, n));
    var changed = next !== step;
    step = next;
    render();
    if (changed) scrollBodyTop();
    centerActiveTab();
  }

  /* ---------- показ визарда / результата ---------- */
  function setView(mode) {
    var isResult = mode === "result";
    wizardHead.hidden = isResult;
    wizardTabs.hidden = isResult;
    wizardBody.hidden = isResult;
    wizardFoot.hidden = isResult;
    resultView.hidden = !isResult;
    if (isResult) resultView.scrollTop = 0;
    else scrollBodyTop();
  }

  function openModal() {
    lastFocus = document.activeElement;
    modal.classList.add("is-open");
    modal.setAttribute("aria-hidden", "false");
    syncScrollLock();
    render();
    setView(finished ? "result" : "wizard");
    if (btnOpen) btnOpen.setAttribute("aria-expanded", "true");
    var closeBtn = qs(".disc-modal__close", modal);
    if (closeBtn && closeBtn.focus) closeBtn.focus({ preventScroll: true });
    requestAnimationFrame(centerActiveTab);
  }

  function closeModal() {
    modal.classList.remove("is-open");
    modal.setAttribute("aria-hidden", "true");
    syncScrollLock();
    if (btnOpen) btnOpen.setAttribute("aria-expanded", "false");
    if (lastFocus && typeof lastFocus.focus === "function") lastFocus.focus({ preventScroll: true });
  }

  /* ---------- сбор и подсчёт ---------- */
  function collectPayload() {
    var payload = [];
    qsa(".disc-list", modal).forEach(function (ul, listIndex) {
      qsa("li", ul).forEach(function (li, idx) {
        payload.push({
          list: listIndex,
          pos: idx,
          type: li.getAttribute("data-type")
        });
      });
    });
    return payload;
  }

  function score(payload) {
    var maj = [];
    var min = [];
    payload.forEach(function (x) {
      if (x.pos === 0) maj.push(x.type);
      if (x.pos === 3) min.push(x.type);
    });
    var count = function (arr, ch) {
      return arr.reduce(function (a, v) { return a + (v === ch ? 1 : 0); }, 0);
    };
    return {
      d: count(maj, "d") - count(min, "d"),
      i: count(maj, "i") - count(min, "i"),
      s: count(maj, "s") - count(min, "s"),
      c: count(maj, "c") - count(min, "c")
    };
  }

  /* ---------- экран результата ---------- */
  var RESULT_TYPES = [
    { key: "d", letter: "D", name: "Доминирование", en: "Dominance", color: "#D64545",
      desc: "Ориентация на цель и результат, прямолинейность, готовность принимать решения." },
    { key: "i", letter: "I", name: "Влияние", en: "Influence", color: "#E8A33D",
      desc: "Общительность, энтузиазм, умение убеждать и вдохновлять людей." },
    { key: "s", letter: "S", name: "Стабильность", en: "Stability", color: "#3A944A",
      desc: "Спокойствие, надёжность, командность, устойчивость в изменениях." },
    { key: "c", letter: "C", name: "Соответствие", en: "Compliance", color: "#1F5BD6",
      desc: "Внимание к деталям, анализ, следование правилам и стандартам." }
  ];

  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text !== undefined && text !== null) n.textContent = text;
    return n;
  }

  function renderResult(res) {
    qs("#scoreLine", modal).textContent =
      "D:" + res.d + ", I:" + res.i + ", S:" + res.s + ", C:" + res.c;

    var values = {};
    RESULT_TYPES.forEach(function (t) { values[t.key] = Number(res[t.key] || 0); });
    var maxAbs = 1;
    RESULT_TYPES.forEach(function (t) {
      maxAbs = Math.max(maxAbs, Math.abs(values[t.key]));
    });

    var bars = qs("#scoreBars", modal);
    bars.textContent = "";
    RESULT_TYPES.forEach(function (t) {
      var v = values[t.key];
      var row = el("div", "scorebar");
      row.appendChild(el("span", "scorebar__key", t.letter));
      var track = el("div", "scorebar__track");
      var fill = el("div", "scorebar__fill");
      fill.style.background = t.color;
      fill.style.width = (Math.abs(v) / maxAbs * 50) + "%";
      if (v > 0) fill.style.left = "50%";
      else if (v < 0) fill.style.right = "50%";
      track.appendChild(fill);
      row.appendChild(track);
      row.appendChild(el("span", "scorebar__val", String(v)));
      bars.appendChild(row);
    });

    var legend = qs("#scoreLegend", modal);
    legend.textContent = "";
    RESULT_TYPES.forEach(function (t) {
      var card = el("div", "legend-card");
      card.appendChild(el("b", null, t.letter));
      card.appendChild(el("i", null, t.name));
      card.appendChild(el("em", null, t.en));
      card.appendChild(el("p", null, t.desc));
      legend.appendChild(card);
    });
  }

  /* ---------- порядок слов для перезапуска ---------- */
  var INITIAL = qsa(".disc-list", modal).map(function (ul) {
    return { ul: ul, items: qsa("li", ul) };
  });

  function resetOrder() {
    INITIAL.forEach(function (rec) {
      rec.items.forEach(function (li) { rec.ul.appendChild(li); });
    });
  }

  /* ---------- drag & drop (указатель + нативный HTML5 DnD) ---------- */
  var HANDLE_SVG =
    '<svg viewBox="0 0 16 16" fill="none" aria-hidden="true" focusable="false">' +
    '<circle cx="5.5" cy="4" r="1.5" fill="#B3B3B3"/>' +
    '<circle cx="10.5" cy="4" r="1.5" fill="#B3B3B3"/>' +
    '<circle cx="5.5" cy="8" r="1.5" fill="#B3B3B3"/>' +
    '<circle cx="10.5" cy="8" r="1.5" fill="#B3B3B3"/>' +
    '<circle cx="5.5" cy="12" r="1.5" fill="#B3B3B3"/>' +
    '<circle cx="10.5" cy="12" r="1.5" fill="#B3B3B3"/>' +
    "</svg>";

  var coarse = !!(window.matchMedia && window.matchMedia("(pointer: coarse)").matches);

  qsa(".disc-item", modal).forEach(function (li) {
    var h = el("span", "disc-handle");
    h.setAttribute("aria-hidden", "true");
    h.innerHTML = HANDLE_SVG;
    li.appendChild(h);
    li.setAttribute("tabindex", "0");
    // тач-устройства: тянуть можно только за «точечки», как в оригинале
    li.setAttribute("draggable", coarse ? "false" : "true");
    if (coarse) h.setAttribute("draggable", "true");
  });

  var ptr = null;    // {li, ul, id, sx, sy, started}
  var ndrag = null;  // {li, ul}
  var lastY = null;
  var rafId = 0;

  function place(li, ul, clientY) {
    var ref = null;
    var i;
    var node;
    var r;
    for (i = 0; i < ul.children.length; i++) {
      node = ul.children[i];
      if (node === li) continue;
      r = node.getBoundingClientRect();
      if (clientY < r.top + r.height / 2) { ref = node; break; }
    }
    for (i = 0; i < ul.children.length; i++) {
      if (ul.children[i] !== li) ul.children[i].classList.remove("is-over");
    }
    if (ref) {
      ref.classList.add("is-over");
      if (li.nextElementSibling !== ref) ul.insertBefore(li, ref);
    } else if (li !== ul.lastElementChild) {
      ul.appendChild(li);
    }
  }

  function markDragging(li, ul) {
    li.classList.add("is-dragging");
    ul.classList.add("is-reordering");
    document.documentElement.classList.add("dragging-active");
    document.body.classList.add("dragging-active");
  }

  function cleanupDrag(li, ul) {
    if (li) li.classList.remove("is-dragging");
    if (ul) {
      ul.classList.remove("is-reordering");
      qsa(".is-over", ul).forEach(function (x) { x.classList.remove("is-over"); });
    }
    if (!ptr && !ndrag) {
      document.documentElement.classList.remove("dragging-active");
      document.body.classList.remove("dragging-active");
    }
  }

  function ensureTick() { if (!rafId) rafId = requestAnimationFrame(tick); }

  function tick() {
    rafId = 0;
    var target = null;
    if (ptr && ptr.started) target = ptr;
    else if (ndrag) target = ndrag;
    if (!target || typeof lastY !== "number") return;
    var rect = wizardBody.getBoundingClientRect();
    var delta = 0;
    if (lastY < rect.top + 56) delta = -Math.min(18, (rect.top + 56 - lastY) / 4);
    else if (lastY > rect.bottom - 56) delta = Math.min(18, (lastY - (rect.bottom - 56)) / 4);
    if (delta) {
      var before = wizardBody.scrollTop;
      wizardBody.scrollTop += delta;
      if (wizardBody.scrollTop !== before) place(target.li, target.ul, lastY);
    }
    ensureTick();
  }

  /* --- режим указателя (мышь / сенсор) --- */
  wizardBody.addEventListener("pointerdown", function (e) {
    if (ptr || ndrag) return;
    if (e.pointerType === "mouse" && e.button !== 0) return;
    var t = e.target;
    var li = t && t.closest ? t.closest(".disc-item") : null;
    if (!li || !wizardBody.contains(li)) return;
    if (coarse && !(t.closest && t.closest(".disc-handle"))) return;
    ptr = {
      li: li,
      ul: li.parentElement,
      id: e.pointerId,
      sx: e.clientX,
      sy: e.clientY,
      started: false
    };
    try { li.setPointerCapture(e.pointerId); } catch (err) {}
  });

  window.addEventListener("pointermove", function (e) {
    if (!ptr || e.pointerId !== ptr.id) return;
    if (!ptr.started) {
      if (Math.abs(e.clientX - ptr.sx) < 4 && Math.abs(e.clientY - ptr.sy) < 4) return;
      if (ndrag) { endPointer(); return; }
      ptr.started = true;
      markDragging(ptr.li, ptr.ul);
      ensureTick();
    }
    if (e.cancelable) e.preventDefault();
    lastY = e.clientY;
    place(ptr.li, ptr.ul, e.clientY);
  }, { passive: false, capture: true });

  function endPointer() {
    if (!ptr) return;
    var p = ptr;
    ptr = null;
    try {
      if (p.started && p.li.hasPointerCapture && p.li.hasPointerCapture(p.id)) {
        p.li.releasePointerCapture(p.id);
      }
    } catch (err) {}
    if (p.started) cleanupDrag(p.li, p.ul);
  }

  window.addEventListener("pointerup", endPointer);
  window.addEventListener("pointercancel", endPointer);

  /* --- нативный HTML5 drag & drop (запасной путь, например для скриптов) --- */
  wizardBody.addEventListener("dragstart", function (e) {
    var t = e.target;
    var li = t && t.closest ? t.closest(".disc-item") : null;
    if (!li || !wizardBody.contains(li)) return;
    if (ptr && ptr.started) { e.preventDefault(); return; }
    ptr = null;
    ndrag = { li: li, ul: li.parentElement };
    markDragging(ndrag.li, ndrag.ul);
    lastY = e.clientY;
    try {
      e.dataTransfer.effectAllowed = "move";
      e.dataTransfer.setData("text/plain", li.firstChild ? li.firstChild.nodeValue : "");
    } catch (err) {}
    ensureTick();
  });

  wizardBody.addEventListener("dragover", function (e) {
    if (!ndrag) return;
    if (e.cancelable) e.preventDefault();
    try { e.dataTransfer.dropEffect = "move"; } catch (err) {}
    lastY = e.clientY;
    place(ndrag.li, ndrag.ul, e.clientY);
    ensureTick();
  });

  wizardBody.addEventListener("drop", function (e) {
    if (ndrag && e.cancelable) e.preventDefault();
  });

  function endNative() {
    if (!ndrag) return;
    var n = ndrag;
    ndrag = null;
    cleanupDrag(n.li, n.ul);
  }

  wizardBody.addEventListener("dragend", endNative);
  window.addEventListener("dragend", endNative);

  /* --- клавиатурное перемещение (доступность) --- */
  wizardBody.addEventListener("keydown", function (e) {
    var t = e.target;
    var li = t && t.closest ? t.closest(".disc-item") : null;
    if (!li || li !== t) return;
    if (e.key !== "ArrowUp" && e.key !== "ArrowDown") return;
    var ul = li.parentElement;
    if (e.key === "ArrowUp" && li.previousElementSibling) {
      ul.insertBefore(li, li.previousElementSibling);
    } else if (e.key === "ArrowDown" && li.nextElementSibling) {
      ul.insertBefore(li.nextElementSibling, li);
    } else {
      return;
    }
    e.preventDefault();
    try { li.focus({ preventScroll: false }); } catch (err) { li.focus(); }
  });

  /* ---------- навигация ---------- */
  tabs.forEach(function (t) {
    t.addEventListener("click", function () {
      setStep(Number(t.getAttribute("data-step-btn")));
    });
  });
  if (btnPrev) btnPrev.addEventListener("click", function () { setStep(step - 1); });
  if (btnNext) btnNext.addEventListener("click", function () { setStep(step + 1); });

  if (btnFinish) {
    btnFinish.addEventListener("click", function () {
      var res = score(collectPayload());
      renderResult(res);
      finished = true;
      setView("result");
    });
  }

  var btnRestart = qs("[data-disc-restart]", modal);
  if (btnRestart) {
    btnRestart.addEventListener("click", function () {
      resetOrder();
      finished = false;
      step = 0;
      render();
      setView("wizard");
      centerActiveTab();
    });
  }

  /* ---------- открытие / закрытие ---------- */
  if (btnOpen) {
    btnOpen.addEventListener("click", function (e) {
      e.preventDefault();
      openModal();
    });
  }

  qsa("[data-disc-close]", modal).forEach(function (x) {
    x.addEventListener("click", function (e) {
      e.preventDefault();
      closeModal();
    });
  });

  document.addEventListener("keydown", function (e) {
    if (e.key !== "Escape") return;
    if (modal.classList.contains("is-open")) closeModal();
  });

  window.addEventListener("resize", function () {
    if (modal.classList.contains("is-open")) centerActiveTab();
  });

  /* ---------- старт ---------- */
  render();
  syncScrollLock();
})();
</script>
</body>
</html>
'''


def main():
    with open(QUESTIONS, encoding="utf-8") as f:
        questions = json.load(f)
    html_text = (TEMPLATE
                 .replace("__PANES__", build_panes(questions))
                 .replace("__TABS__", build_tabs()))
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(html_text)
    print("written:", OUT, len(html_text), "bytes")


if __name__ == "__main__":
    main()
