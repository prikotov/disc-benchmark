
    (() => {
      'use strict';

      const qs = (selector, root = document) => root.querySelector(selector);
      const qsa = (selector, root = document) => Array.from(root.querySelectorAll(selector));

      const wizard = qs('#rootwizard');
      const screenTest = qs('#screen-test');
      const screenResult = qs('#screen-result');
      const tabs = qsa('[data-step-btn]');
      const panes = qsa('[data-step-pane]', wizard);
      const tabsWrap = qs('#steps');
      const prevBtn = qs('#prev-btn');
      const nextBtn = qs('#next-btn');
      const finishBtn = qs('#finish-btn');
      const progressBar = qs('#discProgress');
      const progressTrack = qs('#progress-track');
      const stepCurrent = qs('#step-current');
      const liveStatus = qs('#live-status');
      const scoreString = qs('#score-string');
      const scoreEls = {
        d: qs('#score-d'),
        i: qs('#score-i'),
        s: qs('#score-s'),
        c: qs('#score-c')
      };
      const restartBtn = qs('#restart-btn');
      const testTitle = qs('#test-title');
      const resultTitle = qs('#result-title');
      const lists = qsa('.disc-list', wizard);
      const items = qsa('.disc-item', wizard);
      const totalSteps = panes.length;

      const initialOrder = new Map();
      lists.forEach((list) => {
        initialOrder.set(list, Array.from(list.children).filter((el) => el.classList.contains('disc-item')));
      });

      let step = 0;
      let drag = null;

      const announce = (message) => {
        if (!liveStatus) return;
        liveStatus.textContent = '';
        window.setTimeout(() => {
          liveStatus.textContent = message;
        }, 20);
      };

      const scrollToTest = () => {
        const top = screenTest.getBoundingClientRect().top + window.scrollY - 16;
        window.scrollTo({
          top: Math.max(0, top),
          behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth'
        });
      };

      const centerActiveTab = (behavior = 'smooth') => {
        if (!tabsWrap || tabsWrap.scrollWidth <= tabsWrap.clientWidth + 2) return;
        const active = tabs[step];
        if (!active) return;
        const left = active.offsetLeft - (tabsWrap.clientWidth - active.offsetWidth) / 2;
        tabsWrap.scrollTo({
          left: Math.max(0, left),
          behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : behavior
        });
      };

      const render = ({ scroll = false, announceStep = false } = {}) => {
        tabs.forEach((tab, index) => {
          const active = index === step;
          tab.classList.toggle('is-active', active);
          tab.setAttribute('aria-selected', active ? 'true' : 'false');
          tab.tabIndex = active ? 0 : -1;
        });

        panes.forEach((pane, index) => {
          const active = index === step;
          pane.classList.toggle('is-active', active);
          pane.hidden = !active;
        });

        prevBtn.disabled = step === 0;
        nextBtn.hidden = step === totalSteps - 1;
        finishBtn.hidden = step !== totalSteps - 1;

        const percent = ((step + 1) / totalSteps) * 100;
        progressBar.style.width = percent.toFixed(4) + '%';
        progressTrack.setAttribute('aria-valuenow', String(Math.round(percent)));
        stepCurrent.textContent = String(step + 1);
        wizard.dataset.step = String(step);

        if (announceStep) {
          announce('Шаг ' + (step + 1) + ' из ' + totalSteps);
        }

        requestAnimationFrame(() => centerActiveTab('auto'));

        if (scroll) {
          scrollToTest();
        }
      };

      const setStep = (next, options = {}) => {
        const clamped = Math.max(0, Math.min(totalSteps - 1, next));
        if (clamped === step && !options.force) return;
        if (drag) cleanupDrag(false);
        step = clamped;
        render({ scroll: options.scroll, announceStep: options.announceStep });
      };

      tabs.forEach((tab) => {
        tab.addEventListener('click', () => {
          setStep(Number(tab.dataset.stepBtn), { scroll: true, announceStep: true });
        });

        tab.addEventListener('keydown', (event) => {
          if (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight') return;
          event.preventDefault();
          const direction = event.key === 'ArrowRight' ? 1 : -1;
          const next = (step + direction + totalSteps) % totalSteps;
          setStep(next, { scroll: true, announceStep: true });
          tabs[next].focus({ preventScroll: true });
        });
      });

      prevBtn.addEventListener('click', () => {
        setStep(step - 1, { scroll: true, announceStep: true });
      });

      nextBtn.addEventListener('click', () => {
        setStep(step + 1, { scroll: true, announceStep: true });
      });

      const calculateScore = () => {
        const score = { d: 0, i: 0, s: 0, c: 0 };
        lists.forEach((list) => {
          const listItems = Array.from(list.children).filter((el) => el.classList.contains('disc-item'));
          const first = listItems[0];
          const last = listItems[listItems.length - 1];
          if (first && Object.prototype.hasOwnProperty.call(score, first.dataset.type)) {
            score[first.dataset.type] += 1;
          }
          if (last && Object.prototype.hasOwnProperty.call(score, last.dataset.type)) {
            score[last.dataset.type] -= 1;
          }
        });
        return score;
      };

      const showResult = () => {
        if (drag) cleanupDrag(false);
        const score = calculateScore();
        scoreString.textContent = 'D:' + score.d + ', I:' + score.i + ', S:' + score.s + ', C:' + score.c;
        Object.keys(scoreEls).forEach((key) => {
          scoreEls[key].textContent = String(score[key]);
        });

        screenTest.hidden = true;
        screenResult.hidden = false;
        document.title = 'Ваш DISC-профиль';
        window.scrollTo({ top: 0, behavior: 'auto' });

        requestAnimationFrame(() => {
          resultTitle.focus({ preventScroll: true });
          announce('Тест завершён. ' + scoreString.textContent);
        });
      };

      const restoreInitialOrder = () => {
        lists.forEach((list) => {
          const order = initialOrder.get(list) || [];
          const frag = document.createDocumentFragment();
          order.forEach((item) => frag.appendChild(item));
          list.appendChild(frag);
        });
      };

      const restart = () => {
        restoreInitialOrder();
        step = 0;
        screenResult.hidden = true;
        screenTest.hidden = false;
        document.title = 'Тест DISC — поведенческий профиль';
        render({ force: true });
        window.scrollTo({ top: 0, behavior: 'auto' });
        requestAnimationFrame(() => {
          testTitle.focus({ preventScroll: true });
          announce('Тест начат заново. Шаг 1 из 8.');
        });
      };

      finishBtn.addEventListener('click', showResult);
      restartBtn.addEventListener('click', restart);

      const moveItem = (item, direction) => {
        const list = item.parentElement;
        if (!list || !list.classList.contains('disc-list')) return;
        if (direction < 0) {
          const previous = item.previousElementSibling;
          if (!previous) return;
          list.insertBefore(item, previous);
        } else {
          const next = item.nextElementSibling;
          if (!next) return;
          list.insertBefore(next, item);
        }
        item.focus({ preventScroll: true });
        announce('Порядок изменён. Позиция ' + (Array.from(list.children).indexOf(item) + 1) + ' из 4.');
      };

      items.forEach((item) => {
        item.setAttribute('aria-describedby', 'drag-instructions');
        item.addEventListener('keydown', (event) => {
          if (!event.altKey || (event.key !== 'ArrowUp' && event.key !== 'ArrowDown')) return;
          event.preventDefault();
          moveItem(item, event.key === 'ArrowUp' ? -1 : 1);
        });
      });

      wizard.addEventListener('dragstart', (event) => {
        if (event.target.closest('.disc-item')) event.preventDefault();
      });

      const clearDropMarks = () => {
        items.forEach((item) => item.classList.remove('is-drop-before'));
        lists.forEach((list) => list.classList.remove('is-drop-end'));
      };

      const updateDropTarget = (clientY) => {
        if (!drag) return;
        const siblings = Array.from(drag.list.children).filter(
          (el) => el.classList.contains('disc-item') && el !== drag.item
        );

        let before = null;
        for (const sibling of siblings) {
          const rect = sibling.getBoundingClientRect();
          if (clientY < rect.top + rect.height / 2) {
            before = sibling;
            break;
          }
        }

        drag.before = before;
        clearDropMarks();

        if (before) {
          before.classList.add('is-drop-before');
        } else {
          drag.list.classList.add('is-drop-end');
        }
      };

      const autoScrollTick = () => {
        if (!drag) return;
        const margin = 74;
        const y = drag.lastClientY;
        let delta = 0;

        if (y < margin) {
          delta = -Math.max(2, (margin - y) / 4);
        } else if (y > window.innerHeight - margin) {
          delta = Math.max(2, (y - (window.innerHeight - margin)) / 4);
        }

        if (delta !== 0) {
          const beforeScroll = window.scrollY;
          window.scrollBy(0, delta);
          if (window.scrollY !== beforeScroll) updateDropTarget(y);
        }

        drag.raf = window.requestAnimationFrame(autoScrollTick);
      };

      const cleanupDrag = (commit) => {
        if (!drag) return;

        const current = drag;
        drag = null;

        if (current.raf) window.cancelAnimationFrame(current.raf);

        try {
          if (current.item.hasPointerCapture && current.item.hasPointerCapture(current.pointerId)) {
            current.item.releasePointerCapture(current.pointerId);
          }
        } catch (_) {}

        document.removeEventListener('pointermove', onPointerMove);
        document.removeEventListener('pointerup', onPointerUp);
        document.removeEventListener('pointercancel', onPointerCancel);
        document.removeEventListener('keydown', onDragKeyDown);

        if (commit) {
          if (current.before) {
            current.list.insertBefore(current.item, current.before);
          } else {
            current.list.appendChild(current.item);
          }
        }

        current.item.classList.remove('is-ghost-source');
        current.list.classList.remove('is-reordering');
        clearDropMarks();
        if (current.ghost && current.ghost.parentNode) current.ghost.parentNode.removeChild(current.ghost);
        document.body.classList.remove('is-dragging');

        if (commit) {
          current.item.focus({ preventScroll: true });
          const position = Array.from(current.list.children).indexOf(current.item) + 1;
          announce('Качество перемещено. Позиция ' + position + ' из 4.');
        }
      };

      const activateDrag = () => {
        if (!drag || drag.active) return;

        const rect = drag.item.getBoundingClientRect();
        const ghost = document.createElement('div');
        ghost.className = 'disc-item disc-drag-ghost';
        ghost.innerHTML = drag.item.innerHTML;
        ghost.setAttribute('aria-hidden', 'true');
        ghost.style.left = rect.left + 'px';
        ghost.style.top = rect.top + 'px';
        ghost.style.width = rect.width + 'px';
        ghost.style.height = rect.height + 'px';

        document.body.appendChild(ghost);
        drag.item.classList.add('is-ghost-source');
        drag.list.classList.add('is-reordering');
        document.body.classList.add('is-dragging');
        drag.ghost = ghost;
        drag.active = true;
        drag.offsetY = drag.startY - rect.top;
        drag.ghost.style.top = (drag.lastClientY - drag.offsetY) + 'px';
        drag.raf = window.requestAnimationFrame(autoScrollTick);
      };

      const onPointerMove = (event) => {
        if (!drag || event.pointerId !== drag.pointerId) return;

        drag.lastClientY = event.clientY;

        if (!drag.active) {
          const distance = Math.hypot(event.clientX - drag.startX, event.clientY - drag.startY);
          if (distance < 4) return;
          activateDrag();
        }

        if (!drag.active) return;
        event.preventDefault();
        drag.ghost.style.top = (event.clientY - drag.offsetY) + 'px';
        updateDropTarget(event.clientY);
      };

      const onPointerUp = (event) => {
        if (!drag || event.pointerId !== drag.pointerId) return;
        cleanupDrag(drag.active);
      };

      const onPointerCancel = (event) => {
        if (!drag || event.pointerId !== drag.pointerId) return;
        cleanupDrag(false);
      };

      const onDragKeyDown = (event) => {
        if (event.key === 'Escape' && drag) {
          event.preventDefault();
          cleanupDrag(false);
        }
      };

      const onPointerDown = (event) => {
        if (drag) return;
        if (event.pointerType === 'mouse' && event.button !== 0) return;

        const item = event.target.closest('.disc-item');
        if (!item || !wizard.contains(item)) return;

        const fromHandle = Boolean(event.target.closest('.disc-handle'));
        if (event.pointerType === 'touch' && !fromHandle) return;
        if (event.pointerType === 'pen' && !fromHandle) return;

        const list = item.parentElement;
        if (!list || !list.classList.contains('disc-list')) return;

        event.preventDefault();
        item.focus({ preventScroll: true });

        drag = {
          item,
          list,
          ghost: null,
          active: false,
          pointerId: event.pointerId,
          startX: event.clientX,
          startY: event.clientY,
          offsetY: 0,
          lastClientY: event.clientY,
          before: item.nextElementSibling,
          raf: 0
        };

        try {
          item.setPointerCapture(event.pointerId);
        } catch (_) {}

        document.addEventListener('pointermove', onPointerMove, { passive: false });
        document.addEventListener('pointerup', onPointerUp);
        document.addEventListener('pointercancel', onPointerCancel);
        document.addEventListener('keydown', onDragKeyDown);
      };

      wizard.addEventListener('pointerdown', onPointerDown);

      render({ force: true });
    })();
  