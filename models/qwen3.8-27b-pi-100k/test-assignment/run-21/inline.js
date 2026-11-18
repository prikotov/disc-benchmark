
(function () {
  'use strict';

  var qs = function (s) { return document.querySelector(s); };
  var qsa = function (s) { return Array.prototype.slice.call(document.querySelectorAll(s)); };

  var startView = qs('#startView');
  var testView = qs('#testView');
  var resultView = qs('#resultView');
  var tabsEl = qs('#discTabs');
  var tabs = qsa('.disc-tab');
  var panesEl = qs('#rootwizard');
  var panes = qsa('.disc-pane');
  var btnPrev = qs('[data-disc-prev]');
  var btnNext = qs('[data-disc-next]');
  var btnFinish = qs('[data-disc-finish]');
  var progressEl = qs('#discProgress');
  var LAST_STEP = 7;
  var step = 0;

  /* --- Навигация по шагам --- */
  function isNarrow() {
    if (!window.matchMedia) return false;
    return window.matchMedia('(max-width: 767px)').matches ||
      (window.matchMedia('(pointer: coarse)').matches &&
        window.matchMedia('(max-width: 1024px)').matches);
  }

  function setStep(n) {
    step = Math.max(0, Math.min(LAST_STEP, n));
    render();
  }

  function centerActiveTab() {
    if (!isNarrow()) return;
    for (var i = 0; i < tabs.length; i++) {
      if (Number(tabs[i].dataset.stepBtn) === step) {
        tabs[i].scrollIntoView({ behavior: 'smooth', inline: 'center', block: 'nearest' });
        return;
      }
    }
  }

  function render() {
    tabs.forEach(function (t) {
      var is = Number(t.dataset.stepBtn) === step;
      t.classList.toggle('is-active', is);
      t.setAttribute('aria-selected', is ? 'true' : 'false');
    });
    panes.forEach(function (p) {
      p.classList.toggle('is-active', Number(p.dataset.stepPane) === step);
    });
    btnPrev.disabled = step === 0;
    btnNext.hidden = step === LAST_STEP;
    btnFinish.hidden = step !== LAST_STEP;
    if (progressEl) progressEl.style.width = ((step + 1) / panes.length) * 100 + '%';
    centerActiveTab();
  }

  /* --- Заглушка (ручка) перетаскивания --- */
  var HANDLE_SVG = '<svg width="16" height="12" viewBox="0 0 16 12" aria-hidden="true" focusable="false" fill="currentColor"><path d="M5 1.5C5 0.671573 5.67157 0 6.5 0C7.32843 0 8 0.671573 8 1.5C8 2.32843 7.32843 3 6.5 3C5.67157 3 5 2.32843 5 1.5ZM5 6C5 5.17157 5.67157 4.5 6.5 4.5C7.32843 4.5 8 5.17157 8 6C8 6.82843 7.32843 7.5 6.5 7.5C5.67157 7.5 5 6.82843 5 6ZM5 10.5C5 9.67157 5.67157 9 6.5 9C7.32843 9 8 9.67157 8 10.5C8 11.3284 7.32843 12 6.5 12C5.67157 12 5 11.3284 5 10.5ZM11 1.5C11 0.671573 11.6716 0 12.5 0C13.3284 0 14 0.671573 14 1.5C14 2.32843 13.3284 3 12.5 3C11.6716 3 11 2.32843 11 1.5ZM11 6C11 5.17157 11.6716 4.5 12.5 4.5C13.3284 4.5 14 5.17157 14 6C14 6.82843 13.3284 7.5 12.5 7.5C11.6716 7.5 11 6.82843 11 6ZM11 10.5C11 9.67157 11.6716 9 12.5 9C13.3284 9 14 9.67157 14 10.5C14 11.3284 13.3284 12 12.5 12C11.6716 12 11 11.3284 11 10.5Z"/></svg>';

  qsa('.disc-item').forEach(function (li) {
    var h = document.createElement('span');
    h.className = 'disc-handle';
    h.setAttribute('aria-hidden', 'true');
    h.innerHTML = HANDLE_SVG;
    li.appendChild(h);
    if (li.tabIndex === -1) li.setAttribute('tabindex', '0');
  });

  var initialOrder = qsa('.disc-list').map(function (ul) {
    return Array.prototype.slice.call(ul.children)
      .filter(function (li) { return li.tagName === 'LI'; })
      .map(function (li) {
        return { type: li.getAttribute('data-type'), text: li.textContent.trim() };
      });
  });

  /* --- Подсчёт (как в оригинале): верхний блок +1 своему типу, нижний -1 --- */
  function collectPayload() {
    var payload = [];
    qsa('.disc-list').forEach(function (ul, listIndex) {
      Array.prototype.slice.call(ul.children).filter(function (li) { return li.tagName === 'LI'; })
        .forEach(function (li, idx) {
          payload.push({ list: listIndex, pos: idx, type: li.getAttribute('data-type') });
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
      d: count(maj, 'd') - count(min, 'd'),
      i: count(maj, 'i') - count(min, 'i'),
      s: count(maj, 's') - count(min, 's'),
      c: count(maj, 'c') - count(min, 'c')
    };
  }

  function formatScore(sc) {
    return 'D:' + sc.d + ', I:' + sc.i + ', S:' + sc.s + ', C:' + sc.c;
  }

  function showOnly(view) {
    [startView, testView, resultView].forEach(function (v) { v.hidden = v !== view; });
    window.scrollTo(0, 0);
  }

  /* --- Экраны и кнопки --- */
  qs('#btnStart').addEventListener('click', function () {
    setStep(0);
    showOnly(testView);
  });

  btnPrev.addEventListener('click', function () { setStep(step - 1); });
  btnNext.addEventListener('click', function () { setStep(step + 1); });

  tabsEl.addEventListener('click', function (e) {
    var btn = e.target && e.target.closest ? e.target.closest('.disc-tab') : null;
    if (!btn) return;
    setStep(Number(btn.dataset.stepBtn));
  });

  btnFinish.addEventListener('click', function () {
    var text = formatScore(score(collectPayload()));
    qs('#discScore').textContent = text;
    qs('#discLink').value = text;
    showOnly(resultView);
  });

  qs('#btnRestart').addEventListener('click', function () {
    qsa('.disc-list').forEach(function (ul, i) {
      ul.innerHTML = '';
      initialOrder[i].forEach(function (it) {
        var li = document.createElement('li');
        li.className = 'disc-item';
        li.setAttribute('data-type', it.type);
        li.setAttribute('tabindex', '0');
        li.textContent = it.text;
        var h = document.createElement('span');
        h.className = 'disc-handle';
        h.setAttribute('aria-hidden', 'true');
        h.innerHTML = HANDLE_SVG;
        li.appendChild(h);
        ul.appendChild(li);
      });
    });
    setStep(0);
    showOnly(testView);
  });

  /* --- Копирование результата (clipboard + запасной вариант) --- */
  function setCopyState(btn, on) {
    btn.classList.toggle('is-copied', on);
    var label = btn.querySelector('.copyfield__btnText');
    if (!label) return;
    if (!btn.dataset.defaultText) btn.dataset.defaultText = label.textContent.trim();
    label.textContent = on ? 'Скопировано' : btn.dataset.defaultText;
  }

  document.addEventListener('click', async function (e) {
    var btn = e.target && e.target.closest ? e.target.closest('[data-copy]') : null;
    if (!btn || btn.dataset.copyBusy === '1') return;
    var input = document.querySelector(btn.getAttribute('data-copy'));
    if (!input) return;
    btn.dataset.copyBusy = '1';
    var text = input.value || '';
    var ok = false;
    if (navigator.clipboard && typeof navigator.clipboard.writeText === 'function') {
      try { await navigator.clipboard.writeText(text); ok = true; } catch (err) { /* ниже запасной путь */ }
    }
    if (!ok) {
      input.focus();
      input.select();
      try { ok = document.execCommand('copy'); } catch (err) { ok = false; }
      input.blur();
    }
    if (ok) setCopyState(btn, true);
    window.setTimeout(function () {
      setCopyState(btn, false);
      btn.dataset.copyBusy = '0';
    }, 1500);
  }, { passive: true });

  /* --- Перетаскивание (Pointer Events, без внешних библиотек) --- */
  var dragByHandle = !!(window.matchMedia && window.matchMedia('(pointer: coarse)').matches);
  document.body.classList.add(dragByHandle ? 'drag-mode-handle' : 'drag-mode-any');

  var pending = null;
  var drag = null;

  function addDragListeners() {
    window.addEventListener('pointermove', onPointerMove, { passive: false });
    window.addEventListener('pointerup', onPointerEnd, { passive: false });
    window.addEventListener('pointercancel', onPointerEnd, { passive: false });
  }
  function removeDragListeners() {
    window.removeEventListener('pointermove', onPointerMove);
    window.removeEventListener('pointerup', onPointerEnd);
    window.removeEventListener('pointercancel', onPointerEnd);
  }

  function beginDrag(e) {
    var li = pending.li;
    var rect = li.getBoundingClientRect();
    var clone = li.cloneNode(true);
    clone.classList.remove('is-dragging');
    clone.classList.add('disc-item--ghost');
    clone.style.position = 'fixed';
    clone.style.left = rect.left + 'px';
    clone.style.top = rect.top + 'px';
    clone.style.width = rect.width + 'px';
    clone.style.minWidth = rect.width + 'px';
    clone.style.maxWidth = rect.width + 'px';
    clone.style.height = rect.height + 'px';
    clone.style.margin = '0';
    clone.style.zIndex = '80';
    clone.style.pointerEvents = 'none';
    document.body.appendChild(clone);
    li.classList.add('is-dragging');
    document.body.classList.add('is-dragging');
    drag = { li: li, clone: clone, list: li.closest('.disc-list'), offX: e.clientX - rect.left, offY: e.clientY - rect.top };
    pending = null;
  }

  function onPointerMove(e) {
    if (pending) {
      var dx = e.clientX - pending.x;
      var dy = e.clientY - pending.y;
      if (dx * dx + dy * dy < 36) return; // порог 6px
      beginDrag(e);
    }
    if (!drag) return;
    e.preventDefault();
    drag.clone.style.left = (e.clientX - drag.offX) + 'px';
    drag.clone.style.top = (e.clientY - drag.offY) + 'px';

    // Живая переупорядочка: правило «до/после по середине элемента» (как в оригинале)
    var sibs = Array.prototype.slice.call(drag.list.children)
      .filter(function (n) { return n.tagName === 'LI' && n !== drag.li; });
    for (var i = 0; i < sibs.length; i++) {
      var sib = sibs[i];
      var r = sib.getBoundingClientRect();
      var before = (e.clientY - r.top) < r.height / 2;
      // то же правило, что в оригинале: указатель над серединой соседнего — до него, иначе — после
      var liAfterSib = !(drag.li.compareDocumentPosition(sib) & Node.DOCUMENT_POSITION_FOLLOWING);
      if (before && liAfterSib) drag.list.insertBefore(drag.li, sib);
      else if (!before && !liAfterSib) drag.list.insertBefore(drag.li, sib.nextSibling);
    }

    // Автоскролл контейнера у краёв (удобно на мобильных)
    if (panesEl.scrollHeight > panesEl.clientHeight + 4) {
      var pr = panesEl.getBoundingClientRect();
      var zone = 48;
      var stepPx = 14;
      if (e.clientY < pr.top + zone) panesEl.scrollTop -= stepPx;
      else if (e.clientY > pr.bottom - zone) panesEl.scrollTop += stepPx;
    }
  }

  function onPointerEnd() {
    removeDragListeners();
    if (drag) {
      drag.clone.remove();
      drag.li.classList.remove('is-dragging');
      drag = null;
    }
    pending = null;
    document.body.classList.remove('is-dragging');
  }

  panesEl.addEventListener('pointerdown', function (e) {
    if (drag || pending) return;
    var li = e.target && e.target.closest ? e.target.closest('.disc-item') : null;
    if (!li) return;
    var pane = li.closest('.disc-pane');
    if (!pane || !pane.classList.contains('is-active')) return;
    if (dragByHandle) {
      var handle = e.target.closest('.disc-handle');
      if (!handle || handle.parentNode !== li) return;
    } else if (e.pointerType === 'mouse' && e.button !== 0) {
      return;
    }
    pending = { li: li, x: e.clientX, y: e.clientY };
    addDragListeners();
  }, { passive: true });

  /* --- Управление с клавиатуры: стрелки вверх/вниз меняют порядок --- */
  panesEl.addEventListener('keydown', function (e) {
    var li = e.target && e.target.closest ? e.target.closest('.disc-item') : null;
    if (!li) return;
    if (e.key === 'ArrowUp' && li.previousElementSibling) {
      e.preventDefault();
      li.parentNode.insertBefore(li, li.previousElementSibling);
      li.focus();
    } else if (e.key === 'ArrowDown' && li.nextElementSibling) {
      e.preventDefault();
      li.parentNode.insertBefore(li.nextElementSibling, li);
      li.focus();
    }
  });

  render();
  showOnly(startView);
})();
