/* =================================== */
/* =================================== */
/* =================================== */
/* Danylo Oliinyk - https://iamdev.lol/ */
/* =====October 2025 For Statoplan =====*/
/* =================================== */
/* =================================== */
/* =================================== */
/* 01. Script for the speakers slider */
/* 02. Script for the video slider */
/* 03. Script for displaying news */
/* 04. Script for the popup */
/* 05. Script for smooth scroll and navigation */
/* 06. Script for the burger menu */
/* 07. Script for the accordeon */
/* =================================== */
/* =================================== */
/* =================================== */


/* 01. Script for the speakers slider start*/
document.addEventListener('DOMContentLoaded', () => {
  const root  = document.querySelector('#speaker .speaker__content');
  if (!root) return;

  const track = root.querySelector('.speaker__track');
  const prev  = root.querySelector('.speaker__nav-left');
  const next  = root.querySelector('.speaker__nav-right');

  if (!track || !prev || !next) return;

  const state = {
    index: 0,
    max:   0,
    gap:   0,
    slideW: 0
  };

  function measure() {
    const first = track.querySelector('.speaker__item');
    if (!first) return;

    const cs = getComputedStyle(track);
    state.gap = parseFloat(cs.columnGap || cs.gap || 0) || 0;
    state.slideW = first.getBoundingClientRect().width;

    const viewportW = track.parentElement.getBoundingClientRect().width;

    // сколько ПОЛНЫХ карточек реально влезает
    const perView = Math.max(
      1,
      Math.floor((viewportW + state.gap) / (state.slideW + state.gap))
    );

    state.max = Math.max(0, track.children.length - perView);
    state.index = Math.min(state.index, state.max);

    update();
    toggle();
  }

  function update() {
    const offset = -(state.slideW + state.gap) * state.index;
    track.style.transform = `translateX(${offset}px)`;
  }

  function toggle() {
    prev.classList.toggle('is-disabled', state.index === 0);
    next.classList.toggle('is-disabled', state.index === state.max);
  }

  prev.addEventListener('click', (e) => {
    e.preventDefault();
    if (state.index > 0) {
      state.index--;
      update();
      toggle();
    }
  });

  next.addEventListener('click', (e) => {
    e.preventDefault();
    if (state.index < state.max) {
      state.index++;
      update();
      toggle();
    }
  });

  window.addEventListener('resize', measure, { passive: true });

  measure();
});

/* 01. Script for the speakers slider  end */


/* 02. Script for the video slider start */
document.addEventListener('DOMContentLoaded', () => {
  const root = document.querySelector('#video');
  if (!root) return;

  /* slider */
  const track = root.querySelector('.video__track');
  const items = Array.from(track.children);
  const prev  = root.querySelector('.video__nav-left');
  const next  = root.querySelector('.video__nav-right');

  const GAP = 30;
  let perView = 2;

  const mqMobile = window.matchMedia('(max-width:640px)');
  function recalcPerView(){ perView = mqMobile.matches ? 1 : 2; }
  recalcPerView();
  mqMobile.addEventListener('change', recalcPerView);

  let index = 0;

  function clampIndex(){
    const max = Math.max(0, items.length - perView);
    if (index < 0) index = 0;
    if (index > max) index = max;
    prev.classList.toggle('is-disabled', index === 0);
    next.classList.toggle('is-disabled', index === max);
  }

  function slide(){
    const itemW = items[0]?.getBoundingClientRect().width || 0;
    const offset = index * (itemW + GAP);
    track.style.transform = `translateX(${-offset}px)`;
  }

  prev?.addEventListener('click', e => { e.preventDefault(); index--; clampIndex(); slide(); });
  next?.addEventListener('click', e => { e.preventDefault(); index++; clampIndex(); slide(); });
  window.addEventListener('resize', () => { clampIndex(); slide(); });

  clampIndex(); slide();

  /* players */
  root.querySelectorAll('.video__player').forEach(setupPlayer);

  function setupPlayer(box){
    const poster = box.dataset.poster || '';
    if (poster) box.style.backgroundImage = `url("${poster}")`;

    function play(){
      const src = box.dataset.src || '';
      if (!src) return;

      // MP4/WEBM
      if (/\.(mp4|m4v|webm)(\?|$)/i.test(src)) {
        const v = document.createElement('video');
        v.src = src;
        v.controls = true;
        v.autoplay = true;
        v.playsInline = true;
        v.poster = poster || '';
        v.style.width = '100%';
        v.style.height = '100%';
        v.style.display = 'block';
        box.replaceChildren(v);
        return;
      }

      // Iframe embeds (YouTube/Vimeo/др.)
      const iframe = document.createElement('iframe');
      iframe.src = src.includes('autoplay=1') ? src : (src + (src.includes('?') ? '&' : '?') + 'autoplay=1');
      iframe.allow = 'autoplay; encrypted-media; picture-in-picture';
      iframe.allowFullscreen = true;
      iframe.title = 'Видео';
      iframe.style.width = '100%';
      iframe.style.height = '100%';
      iframe.frameBorder = '0';
      box.replaceChildren(iframe);
    }

    box.addEventListener('click', play);
    box.addEventListener('keydown', e => {
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); play(); }
    });
  }
});

/* 02. Script for the video slider end */

/* 03. Script for displaying news start */
/* document.addEventListener('DOMContentLoaded', () => {
  const root = document.querySelector('#news');
  if (!root) return;

  const rows = [...root.querySelectorAll('.news__wrap .news__row')];
  const btn  = root.querySelector('.news__btn-group .btn');

  rows.slice(1).forEach(r => r.classList.remove('active'));

  btn?.addEventListener('click', e => {
    e.preventDefault();
    const hidden = rows.slice(1).filter(r => !r.classList.contains('active'));
    if (hidden.length) {
      hidden.forEach(r => r.classList.add('active'));
      btn.textContent = 'Свернуть';
    } else {
      rows.slice(1).forEach(r => r.classList.remove('active'));
      btn.textContent = 'Больше новостей';
      root.scrollIntoView({behavior:'smooth', block:'start'});
    }
  });
}); */
/* 03. Script for displaying news end */



/* Script for the Pop-Up start*/
(function(){
  const OPEN_IDS = new Set(['#tospeak', '#sponsored']);

  function openModal(id){
    const m = document.querySelector(id);
    if (!m) return;
    m.classList.add('is-open');
    m.setAttribute('aria-hidden', 'false');
    document.body.classList.add('no-scroll');
  }
  function closeModal(m){
    if (!m) return;
    m.classList.remove('is-open');
    m.setAttribute('aria-hidden', 'true');
    document.body.classList.remove('no-scroll');
    if (location.hash && (location.hash === '#tospeak' || location.hash === '#sponsored')) {
      history.replaceState('', document.title, location.pathname + location.search);
    }
  }

  document.addEventListener('click', (e) => {
    const a = e.target.closest('a[href^="#"]');
    if (a && OPEN_IDS.has(a.getAttribute('href'))) {
      e.preventDefault();
      openModal(a.getAttribute('href'));
      return;
    }
    if (e.target.matches('[data-close]')) {
      closeModal(e.target.closest('.modal'));
      return;
    }
    const modal = e.target.classList.contains('modal') ? e.target : null;
    if (modal) closeModal(modal);
  });

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      document.querySelectorAll('.modal.is-open').forEach(closeModal);
    }
  });

  if (OPEN_IDS.has(location.hash)) openModal(location.hash);
  window.addEventListener('hashchange', () => {
    if (OPEN_IDS.has(location.hash)) openModal(location.hash);
  });
})();

/* Script for the Pop-Up end*/


/* 05. Script for smooth scroll and navigation start */
/* (function(){
  const EASE = 0.10;           // инерция
  const STEP = 0.50;             // базовый шаг для колёсика
  let target = window.scrollY;
  let y = target;
  let rafId = null;

  const header = document.querySelector('header');
  const headerH = () => (header ? header.offsetHeight : 0);

  function isScrollable(el){
    while (el && el !== document.body){
      const s = getComputedStyle(el);
      const canScroll = /(auto|scroll)/.test(s.overflow + s.overflowY + s.overflowX);
      if (canScroll && el.scrollHeight > el.clientHeight) return true;
      el = el.parentElement;
    }
    return false;
  }

  function animate(){
    const diff = target - y;
    if (Math.abs(diff) < 0.1){
      y = target;
      window.scrollTo(0, y);
      rafId = null;
      return;
    }
    y += diff * EASE;
    window.scrollTo(0, y);
    rafId = requestAnimationFrame(animate);
  }

  function clamp(v){
    const max = Math.max(0, document.documentElement.scrollHeight - window.innerHeight);
    return Math.min(Math.max(0, v), max);
  }

  function toY(pos){
    target = clamp(pos);
    if (!rafId) rafId = requestAnimationFrame(animate);
  }

  window.addEventListener('wheel', (e) => {
    if (e.defaultPrevented) return;
    if (isScrollable(e.target)) return;
    e.preventDefault();
    const delta = (Math.abs(e.deltaY) > 1 ? e.deltaY : Math.sign(e.deltaY)) * STEP;
    toY((target = clamp(target + delta)));
  }, { passive: false });

  window.addEventListener('scroll', () => {
    if (!rafId) { target = window.scrollY; y = window.scrollY; }
  }, { passive: true });

  window.addEventListener('resize', () => { target = clamp(target); y = clamp(y); });


  document.addEventListener('click', (e) => {
    const a = e.target.closest('a[href^="#"]');
    if (!a) return;
    const href = a.getAttribute('href');
    if (!href || href === '#') return;

    const id = href.slice(1);
    const el = document.getElementById(id);
    if (!el) return;

    e.preventDefault();
    const rectTop = el.getBoundingClientRect().top;
    const offset = headerH();
    const dest = (window.scrollY || 0) + rectTop - offset;
    toY(dest);

    if (history.replaceState) {
      history.replaceState('', document.title, location.pathname + location.search);
    }
  }, { passive: false });

  window.addEventListener('load', () => {
    if (location.hash && location.hash.length > 1){
      const el = document.getElementById(location.hash.slice(1));
      if (el){
        const rectTop = el.getBoundingClientRect().top;
        toY((window.scrollY || 0) + rectTop - headerH());
        history.replaceState('', document.title, location.pathname + location.search);
      }
    }
  });
})(); */
/* 05. Script for smooth scroll and navigation end */

/* 06. Script for the accordeon  Start*/
// Accordeon Start
(function () {
  const root = document.querySelector('.program__acc-wrap');
  if (!root) return;

  const items = Array.from(root.querySelectorAll('.program__acc'));
  if (!items.length) return;

  const PLUS = '<svg xmlns="http://www.w3.org/2000/svg" width="19" height="19" viewBox="0 0 19 19" fill="none"><path d="M9.1667 1V17.3334M1 9.16668H17.3333" stroke="#215FCB" stroke-width="2" stroke-linecap="square" stroke-linejoin="round"/></svg>';
  const MINUS = '<svg xmlns="http://www.w3.org/2000/svg" width="19" height="19" viewBox="0 0 19 19" fill="none"><path d="M1 9.16668H17.3333" stroke="#215FCB" stroke-width="2" stroke-linecap="square" stroke-linejoin="round"/></svg>';

  // Инициализация: все закрыты, везде плюс
  items.forEach(item => {
    const text = item.querySelector('.program__acc-text');
    const icon = item.querySelector('.program__acc-col-right');
    if (text) text.classList.remove('acc-text-active');
    if (icon) icon.innerHTML = PLUS;
  });

  function toggleAcc(target) {
    const targetText = target.querySelector('.program__acc-text');
    const targetIcon = target.querySelector('.program__acc-col-right');
    if (!targetText || !targetIcon) return;

    const willOpen = !targetText.classList.contains('acc-text-active');

    // позиция блока ДО изменений
    const beforeTop = target.getBoundingClientRect().top;

    // закрываем всех и ставим плюсики
    items.forEach(item => {
      const text = item.querySelector('.program__acc-text');
      const icon = item.querySelector('.program__acc-col-right');
      if (!text || !icon) return;
      text.classList.remove('acc-text-active');
      icon.innerHTML = PLUS;
    });

    // открываем только целевой (если нужно)
    if (willOpen) {
      targetText.classList.add('acc-text-active');
      targetIcon.innerHTML = MINUS;
    }

    // компенсация скролла — оставляем заголовок на месте
    requestAnimationFrame(() => {
      const afterTop = target.getBoundingClientRect().top;
      const diff = afterTop - beforeTop;
      if (Math.abs(diff) > 1) {
        window.scrollBy(0, diff);
      }
    });
  }

  root.addEventListener('click', (e) => {
    const acc = e.target.closest('.program__acc');
    if (!acc || !root.contains(acc)) return;
    e.preventDefault();
    toggleAcc(acc);
  });
})();

/* Script for the accordeon  End*/
(() => {
  const burger = document.getElementById('burger-icon');
  const nav    = document.getElementById('nav-links');
  if (!burger || !nav) return;

  // a11y
  burger.setAttribute('role','button');
  burger.setAttribute('aria-controls','nav-links');
  burger.setAttribute('aria-expanded','false');
  burger.tabIndex = 0;

  const mq = window.matchMedia('(max-width:1024px)');

  const open = () => {
    nav.classList.add('active');
    document.documentElement.style.overflow = 'hidden';
    burger.setAttribute('aria-expanded','true');
  };

  const close = () => {
    nav.classList.remove('active');
    document.documentElement.style.overflow = '';
    burger.setAttribute('aria-expanded','false');
  };

  const toggle = () => (nav.classList.contains('active') ? close() : open());

  burger.addEventListener('click', toggle);
  burger.addEventListener('keydown', e => {
    if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggle(); }
  });

  // клик по ссылке — закрыть
  nav.addEventListener('click', e => {
    if (e.target.closest('.header__link')) close();
  });

  // клик вне меню — закрыть
  document.addEventListener('click', e => {
    if (!mq.matches) return;
    const t = e.target;
    if (nav.classList.contains('active') && !nav.contains(t) && !burger.contains(t)) close();
  });

  // Esc
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') close();
  });

  // ресет при изменении брейкпоинта
  window.addEventListener('resize', () => {
    if (!mq.matches) close();
  });
})();


document.querySelectorAll('a[href^="#"]').forEach(anchor => {
  anchor.addEventListener('click', function (e) {
    const targetId = this.getAttribute('href').substring(1); // убираем #
    if (!targetId) return;

    const target = document.getElementById(targetId);
    if (!target) return;

    e.preventDefault(); // отключаем стандартный переход с якорем в URL

    const headerOffset = 80; // подгони под высоту своего фиксированного хедера
    const elementPosition = target.getBoundingClientRect().top + window.pageYOffset;
    const offsetPosition = elementPosition - headerOffset;

    window.scrollTo({
      top: offsetPosition,
      behavior: 'smooth'
    });
  });
});

/* =================================== */

/* ===== Modal: Регистрация ===== */
(() => {
  const modal  = document.getElementById('reg-modal');
  if (!modal) return;

  const html   = document.documentElement;
  const body   = document.body;
  const dialog = modal.querySelector('.modal__dialog');

  // Делегирование: ловим клики по .js-reg-alt или a[href="#reg-alt"]
  document.addEventListener('click', (e) => {
    const t = e.target.closest('a.js-reg-alt, a[href="#reg-alt"]');
    if (!t) return;
    e.preventDefault();
    open();
  });

  // Кнопки закрытия и клик по бэкдропу
  modal.addEventListener('click', (e) => {
    if (
      e.target.closest('[data-close="modal"], .modal__close') ||
      e.target.classList.contains('modal__backdrop')
    ) {
      close();
    }
  });

  // Esc + trap focus
  document.addEventListener('keydown', (e) => {
    if (!isOpen()) return;
    if (e.key === 'Escape') close();
    if (e.key === 'Tab') trapFocus(e);
  });

  let prevFocus = null;

  function isOpen() {
    return modal.classList.contains('is-open');
  }

  function open() {
    if (isOpen()) return;
    prevFocus = document.activeElement;
    modal.classList.add('is-open');
    html.classList.add('modal-lock');
    body.classList.add('modal-lock');
    focusFirst();
  }

  function close() {
    if (!isOpen()) return;
    modal.classList.remove('is-open');
    html.classList.remove('modal-lock');
    body.classList.remove('modal-lock');
    if (prevFocus && typeof prevFocus.focus === 'function') {
      prevFocus.focus({ preventScroll: true });
    }
  }

  function focusables() {
    return modal.querySelectorAll(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
  }

  function focusFirst() {
    const f = focusables();
    (f[0] || dialog).focus({ preventScroll: true });
  }

  function trapFocus(e) {
    const f = Array.from(focusables());
    if (!f.length) return;
    const i = f.indexOf(document.activeElement);
    if (e.shiftKey && (i <= 0)) { e.preventDefault(); f[f.length - 1].focus(); }
    else if (!e.shiftKey && (i === f.length - 1)) { e.preventDefault(); f[0].focus(); }
  }
})();
/* =================================== */
document.addEventListener('DOMContentLoaded', function () {
    const tabs = document.querySelectorAll('.program__tabs-btn');
    const panes = document.querySelectorAll('.program-tabs__pane');

    if (!tabs.length || !panes.length) return;

    const activateTab = (target) => {
        tabs.forEach((tab) => {
            tab.classList.toggle('is-active', tab.dataset.target === target);
        });

        panes.forEach((pane) => {
            pane.classList.toggle('is-active', pane.dataset.tab === target);
        });
    };

    tabs.forEach((tab) => {
        tab.addEventListener('click', function (e) {
            e.preventDefault();
            const target = this.dataset.target;
            if (!target) return;
            activateTab(target);
        });
    });
});

/* =================================== */
/* Danylo Oliinyk - https://iamdev.lol/ */
/* =====October 2025 For Statoplan =====*/
/* =================================== */
/* =================================== */
/* =================================== */