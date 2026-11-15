/* DISC (JS) — полный файл: тест-модалка -> apruve -> redirect после успеха формы */
(() => {
  // =========================
  // helpers
  // =========================
  const qs = (s, r = document) => r.querySelector(s);
  const qsa = (s, r = document) => Array.from(r.querySelectorAll(s));

  const base64urlEncode = (bytes) => {
    let bin = "";
    bytes.forEach((b) => (bin += String.fromCharCode(b)));
    return btoa(bin).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
  };

  const strToBytes = (s) => new TextEncoder().encode(String(s || ""));

  const concatBytes = (a, b) => {
    const out = new Uint8Array(a.length + b.length);
    out.set(a, 0);
    out.set(b, a.length);
    return out;
  };

  // ✅ Скролл: блокируем только когда реально открыта одна из модалок
  const syncScrollLock = () => {
    const anyOpen = !!document.querySelector(".disc-modal.is-open, .apruve.is-open");
    document.documentElement.classList.toggle("no-scroll", anyOpen);
    document.body.classList.toggle("no-scroll", anyOpen);
  };

  const openModal = (el) => {
    if (!el) return;
    el.classList.add("is-open");
    el.setAttribute("aria-hidden", "false");
    syncScrollLock();
  };

  const closeModal = (el) => {
    if (!el) return;
    el.classList.remove("is-open");
    el.setAttribute("aria-hidden", "true");
    syncScrollLock();
  };

  // =========================
  // DOM anchors
  // =========================
  const wizard = qs("#wizardmodal");
  if (!wizard) return;

  const apruve = qs("#apruve"); // вторая модалка

  const btnOpenWizard = qs('[data-modal-open="wizardmodal"], [data-disc-open]');
  const btnCloseWizard = qsa("[data-disc-close]", wizard);

  const tabs = qsa("[data-step-btn]", wizard);
  const panes = qsa("[data-step-pane]", wizard);

  const btnPrev = qs("[data-disc-prev]", wizard);
  const btnNext = qs("[data-disc-next]", wizard);
  const btnFinish = qs("[data-disc-finish]", wizard);

  const progressEl = qs("#discProgress", wizard);

  // =========================
  // state
  // =========================
  let step = 0;
  let lastFocus = null;

  // для редиректа после успешного сабмита формы
  const STORAGE_TOKEN_KEY = "disc_result_token_v1";
  let resultToken = null;

  // =========================
  // modal: wizard
  // =========================
  const openWizard = () => {
    lastFocus = document.activeElement;
    openModal(wizard);
    qs(".disc-modal__close", wizard)?.focus({ preventScroll: true });
    render();
    requestAnimationFrame(() => centerActiveTab("auto"));
  };

  const closeWizard = () => {
    closeModal(wizard);
    if (lastFocus && typeof lastFocus.focus === "function") {
      lastFocus.focus({ preventScroll: true });
    }
  };

  // =========================
  // modal: apruve
  // =========================
  const openApruve = () => openModal(apruve);
  const closeApruve = () => closeModal(apruve);

  // на старте apruve скрываем, если не включен дебаг
  // (оставь data-force-open="1" на #apruve если хочешь видеть всегда)
  if (apruve && !apruve.hasAttribute("data-force-open")) {
    closeApruve();
  }

  // =========================
  // steps
  // =========================
  const setStep = (n) => {
    step = Math.max(0, Math.min(7, n));
    render();
  };

  const render = () => {
    tabs.forEach((t) => {
      const is = Number(t.dataset.stepBtn) === step;
      t.classList.toggle("is-active", is);
      t.setAttribute("aria-selected", is ? "true" : "false");
    });

    panes.forEach((p) => p.classList.toggle("is-active", Number(p.dataset.stepPane) === step));

    if (btnPrev) btnPrev.disabled = step === 0;
    if (btnNext) btnNext.hidden = step === 7;
    if (btnFinish) btnFinish.hidden = step !== 7;

    if (progressEl) {
      const pct = ((step + 1) / 8) * 100;
      progressEl.style.width = pct + "%";
    }


    // mobile UX hooks
    if (isMobileUI && isMobileUI()) {
      if (step !== lastRenderedStep) {
        lastRenderedStep = step;
        // после перерендера/изменения классов — центрируем активный таб
        requestAnimationFrame(() => centerActiveTab("smooth"));
      }
      if (pendingScrollTop) {
        pendingScrollTop = false;
        // вверх внутри .disc-modal__body
        requestAnimationFrame(() => scrollStepTop("smooth"));
      }
    }
  };

    // =========================
  // mobile UX:
  // 1) центрируем активный таб в горизонтальном скролле
  // 2) после "Далее" скроллим контент шага вверх
  // =========================

  const tabsScroller = qs(".disc-modal__tabs", wizard);
  const wizardBodyScroller = qs(".disc-modal__body", wizard) || wizard;

  const isMobileUI = () =>
    (window.matchMedia && window.matchMedia("(max-width: 767px)").matches) ||
    (window.matchMedia && window.matchMedia("(pointer: coarse)").matches && window.matchMedia("(max-width: 1024px)").matches);

  let lastCenteredStep = -1;

  let pendingScrollTop = false;
  let lastRenderedStep = -1;

  const centerActiveTab = (behavior = "smooth") => {
    if (!isMobileUI()) return;
    if (!tabsScroller || !tabsScroller.scrollWidth) return;

    const activeTab = tabs.find((t) => Number(t.dataset.stepBtn) === step);
    if (!activeTab) return;

    const container = tabsScroller;
    const containerRect = container.getBoundingClientRect();
    const tabRect = activeTab.getBoundingClientRect();

    // позиция центра таба относительно скролл-контейнера
    const tabCenterX = (tabRect.left - containerRect.left) + tabRect.width / 2;
    const targetLeft = container.scrollLeft + tabCenterX - container.clientWidth / 2;

    const maxLeft = Math.max(0, container.scrollWidth - container.clientWidth);
    const clamped = Math.min(Math.max(0, targetLeft), maxLeft);

    // если уже близко — не дёргаем
    if (Math.abs(container.scrollLeft - clamped) < 2) return;

    container.scrollTo({ left: clamped, behavior });
  };

  const scrollStepTop = (behavior = "smooth") => {
    if (!isMobileUI()) return;
    if (!wizardBodyScroller) return;

    // скроллим именно внутренний скролл модалки (а не window)
    wizardBodyScroller.scrollTo({ top: 0, behavior });
  };


  // =========================
  // =========================
  // sortable lists (SortableJS: touch + desktop)
  // =========================
  // Требование:
  // - mobile/tablet: drag только за "точечки" (handle)
  // - desktop: drag как раньше (за весь элемент)
  const dragByHandle = !!(window.matchMedia && window.matchMedia("(pointer: coarse)").matches);

  const HANDLE_SVG = `
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16" fill="none">
      <path d="M5 4C5 3.86 5 3.791 5.008 3.733C5.03345 3.54971 5.11803 3.37973 5.24888 3.24888C5.37973 3.11803 5.54971 3.03345 5.733 3.008C5.79 3 5.86 3 6 3C6.14 3 6.209 3 6.267 3.008C6.45029 3.03345 6.62027 3.11803 6.75112 3.24888C6.88197 3.37973 6.96655 3.54971 6.992 3.733C7 3.79 7 3.86 7 4C7 4.14 7 4.209 6.992 4.267C6.96655 4.45029 6.88197 4.62027 6.75112 4.75112C6.62027 4.88197 6.45029 4.96655 6.267 4.992C6.21 5 6.14 5 6 5C5.86 5 5.791 5 5.733 4.992C5.54971 4.96655 5.37973 4.88197 5.24888 4.75112C5.11803 4.62027 5.03345 4.45029 5.008 4.267C5 4.21 5 4.14 5 4ZM5 8C5 7.86 5 7.791 5.008 7.733C5.03345 7.54971 5.11803 7.37973 5.24888 7.24888C5.37973 7.11803 5.54971 7.03345 5.733 7.008C5.79 7 5.86 7 6 7C6.14 7 6.209 7 6.267 7.008C6.45029 7.03345 6.62027 7.11803 6.75112 7.24888C6.88197 7.37973 6.96655 7.54971 6.992 7.733C7 7.79 7 7.86 7 8C7 8.14 7 8.209 6.992 8.267C6.96655 8.45029 6.88197 8.62027 6.75112 8.75112C6.62027 8.88197 6.45029 8.96655 6.267 8.992C6.21 9 6.14 9 6 9C5.86 9 5.791 9 5.733 8.992C5.54971 8.96655 5.37973 8.88197 5.24888 8.75112C5.11803 8.62027 5.03345 8.45029 5.008 8.267C5 8.21 5 8.14 5 8ZM5 12C5 11.861 5 11.791 5.008 11.733C5.0336 11.55 5.11812 11.3804 5.24876 11.2498C5.37939 11.1191 5.54904 11.0346 5.732 11.009C5.791 11.001 5.86 11.001 5.999 11.001C6.138 11.001 6.209 11.001 6.266 11.009C6.44896 11.0346 6.61861 11.1191 6.74924 11.2498C6.87988 11.3804 6.9644 11.55 6.99 11.733C6.998 11.791 6.998 11.861 6.998 12C6.998 12.139 6.998 12.209 6.99 12.267C6.9644 12.45 6.87988 12.6196 6.74924 12.7502C6.61861 12.8809 6.44896 12.9654 6.266 12.991C6.208 12.999 6.138 12.999 5.999 12.999C5.86 12.999 5.79 12.999 5.732 12.991C5.54904 12.9654 5.37939 12.8809 5.24876 12.7502C5.11812 12.6196 5.0336 12.45 5.008 12.267C5 12.209 5 12.139 5 12ZM9 4C9 3.86 9 3.791 9.008 3.733C9.03345 3.54971 9.11803 3.37973 9.24888 3.24888C9.37973 3.11803 9.54971 3.03345 9.733 3.008C9.79 3 9.86 3 10 3C10.14 3 10.209 3 10.267 3.008C10.4503 3.03345 10.6203 3.11803 10.7511 3.24888C10.882 3.37973 10.9665 3.54971 10.992 3.733C11 3.79 11 3.86 11 4C11 4.14 11 4.209 10.992 4.267C10.9665 4.45029 10.882 4.62027 10.7511 4.75112C10.6203 4.88197 10.4503 4.96655 10.267 4.992C10.21 5 10.14 5 10 5C9.86 5 9.791 5 9.733 4.992C9.54971 4.96655 9.37973 4.88197 9.24888 4.75112C9.11803 4.62027 9.03345 4.45029 9.008 4.267C9 4.21 9 4.14 9 4ZM9 8C9 7.86 9 7.791 9.008 7.733C9.03345 7.54971 9.11803 7.37973 9.24888 7.24888C9.37973 7.11803 9.54971 7.03345 9.733 7.008C9.79 7 9.86 7 10 7C10.14 7 10.209 7 10.267 7.008C10.4503 3.03345 10.6203 7.11803 10.7511 7.24888C10.882 7.37973 10.9665 7.54971 10.992 7.733C11 7.79 11 7.86 11 8C11 8.14 11 8.209 10.992 8.267C10.9665 8.45029 10.882 8.62027 10.7511 8.75112C10.6203 8.88197 10.4503 8.96655 10.267 8.992C10.21 9 10.14 9 10 9C9.86 9 9.791 9 9.733 8.992C9.54971 8.96655 9.37973 8.88197 9.24888 8.75112C9.11803 8.62027 9.03345 8.45029 9.008 8.267C9 8.21 9 8.14 9 8ZM9 12C9 11.861 9 11.791 9.008 11.733C9.0336 11.55 9.11812 11.3804 9.24876 11.2498C9.37939 11.1191 9.54904 11.0346 9.732 11.009C9.791 11.001 9.86 11.001 9.999 11.001C10.139 11.001 10.209 11.001 10.266 11.009C10.449 11.0346 10.6186 11.1191 10.7492 11.2498C10.8799 11.3804 10.9644 11.55 10.99 11.733C10.998 11.791 10.998 11.861 10.998 12C10.998 12.139 10.998 12.209 10.99 12.267C10.9644 12.45 10.8799 12.6196 10.7492 12.7502C10.6186 12.8809 10.449 12.9654 10.266 12.991C10.208 12.999 10.138 12.999 9.999 12.999C9.86 12.999 9.79 12.999 9.732 12.991C9.54904 12.9654 9.37939 12.8809 9.24876 12.7502C9.11812 12.6196 9.0336 12.45 9.008 12.267C9 12.209 9 12.139 9 12Z" fill="#B3B3B3"/>
    </svg>
  `.trim();

  const ensureHandles = (ul) => {
    // добавляем "точечки" (handle) в каждый элемент, если их нет
    qsa("li", ul).forEach((li) => {
      if (qs(".disc-handle", li)) return;

      const h = document.createElement("span");
      h.className = "disc-handle";
      h.setAttribute("aria-hidden", "true");
      h.innerHTML = HANDLE_SVG;
      li.appendChild(h);
    });
  };

  // HTML5 DnD (fallback) — работает только на desktop, на iOS/мобилках drag-события не стреляют.
  const makeSortable = (ul) => {
    const items = () => qsa("li", ul);

    ensureHandles(ul);

    items().forEach((li) => {
      const handle = qs(".disc-handle", li);

      // desktop (как было): тащим за весь li
      if (!dragByHandle) {
        li.setAttribute("draggable", "true");
        handle?.setAttribute("draggable", "false");

        li.addEventListener("dragstart", (e) => {
          li.classList.add("is-dragging");
          e.dataTransfer.effectAllowed = "move";
        });

        li.addEventListener("dragend", () => {
          li.classList.remove("is-dragging");
          items().forEach((x) => x.classList.remove("is-over"));
        });
      }

      // mobile/tablet: тащим только за handle
      if (dragByHandle) {
        li.setAttribute("draggable", "false");
        if (handle) handle.setAttribute("draggable", "true");

        handle?.addEventListener("dragstart", (e) => {
          li.classList.add("is-dragging");
          e.dataTransfer.effectAllowed = "move";
        });

        handle?.addEventListener("dragend", () => {
          li.classList.remove("is-dragging");
          items().forEach((x) => x.classList.remove("is-over"));
        });
      }

      li.addEventListener("dragover", (e) => {
        e.preventDefault();
        const dragging = qs(".is-dragging", ul);
        if (!dragging || dragging === li) return;

        li.classList.add("is-over");
        const rect = li.getBoundingClientRect();
        const before = e.clientY - rect.top < rect.height / 2;
        ul.insertBefore(dragging, before ? li : li.nextSibling);
      });

      li.addEventListener("dragleave", () => li.classList.remove("is-over"));
      li.addEventListener("drop", (e) => {
        e.preventDefault();
        li.classList.remove("is-over");
      });
    });
  };

  const ensureSortableLoaded = () => {
    if (window.Sortable) return Promise.resolve(true);

    return new Promise((resolve) => {
      const s = document.createElement("script");
      s.src = "https://cdn.jsdelivr.net/npm/sortablejs@1.15.2/Sortable.min.js";
      s.async = true;
      s.onload = () => resolve(true);
      s.onerror = () => resolve(false);
      document.head.appendChild(s);
    });
  };

  const initSortable = () => {
    const lists = qsa(".disc-list", wizard);

    // ensure handles exist for SortableJS too
    lists.forEach(ensureHandles);

    const initHtml5Fallback = () => lists.forEach(makeSortable);

    ensureSortableLoaded().then((ok) => {
      if (!ok || !window.Sortable) {
        initHtml5Fallback();
        return;
      }

      lists.forEach((ul) => {
        if (ul.__discSortable) return;

        ul.__discSortable = window.Sortable.create(ul, {
          animation: 150,

          // desktop: как раньше (за весь элемент)
          // mobile/tablet: только за handle
          ...(dragByHandle ? { handle: ".disc-handle" } : {}),

          // ✅ ВАЖНО: на части desktop-браузеров HTML5 DnD внутри overflow-контейнеров
          // ведёт себя нестабильно. Поэтому используем fallback везде.
          forceFallback: true,
          fallbackOnBody: true,
          fallbackTolerance: dragByHandle ? 6 : 0,

          // scroll внутри модалки
          scroll: true,
          scrollSensitivity: 30,
          scrollSpeed: 12,

          // классы под ваш CSS (.disc-item.is-dragging / .disc-item.is-over)
          chosenClass: "is-dragging",
          dragClass: "is-dragging",
          ghostClass: "is-over",

          onChoose: () => ul.classList.add("is-reordering"),
          onUnchoose: () => ul.classList.remove("is-reordering"),
          onEnd: () => ul.classList.remove("is-reordering"),
        });
      });
    });
  };
  // =========================
  // collect + score (минимально жизнеспособно)
  // =========================
  const collectPayload = () => {
    // собираем все списки: в каждом idx позиции, type = d/i/s/c
    const payload = [];
    const lists = qsa(".disc-list", wizard);

    lists.forEach((ul, listIndex) => {
      const lis = qsa("li", ul);
      lis.forEach((li, idx) => {
        payload.push({
          list: listIndex,
          pos: idx,
          type: li.getAttribute("data-type"),
        });
      });
    });

    return payload;
  };

  const score = (payload) => {
    // логика как в твоем черновике: major = позиция 0, minor = позиция 3
    const maj = [];
    const min = [];

    payload.forEach((x) => {
      if (x.pos === 0) maj.push(x.type);
      if (x.pos === 3) min.push(x.type);
    });

    const count = (arr, ch) => arr.reduce((a, v) => a + (v === ch ? 1 : 0), 0);

    return {
      d: count(maj, "d") - count(min, "d"),
      i: count(maj, "i") - count(min, "i"),
      s: count(maj, "s") - count(min, "s"),
      c: count(maj, "c") - count(min, "c"),
    };
  };

  // =========================
  // "шифрование" результата в URL-токен (AES-GCM через WebCrypto)
  // =========================
  const SECRET = "disc@v1::client-only"; // менять можно, но тогда меняй и на странице result (дешифратор)

  const getAesKey = async () => {
    const hash = await crypto.subtle.digest("SHA-256", strToBytes(SECRET));
    return crypto.subtle.importKey("raw", hash, { name: "AES-GCM" }, false, ["encrypt", "decrypt"]);
  };

  const encryptToToken = async (obj) => {
    const key = await getAesKey();
    const iv = crypto.getRandomValues(new Uint8Array(12));
    const plain = strToBytes(JSON.stringify(obj));
    const cipher = new Uint8Array(await crypto.subtle.encrypt({ name: "AES-GCM", iv }, key, plain));
    // token = base64url(iv + cipher)
    return base64urlEncode(concatBytes(iv, cipher));
  };

  // =========================
  // redirect
  // =========================
  const redirectToResult = () => {
    const token = sessionStorage.getItem(STORAGE_TOKEN_KEY) || resultToken;
    if (!token) return;
    // требование: disc/result/?<token>
    (window.top || window).location.assign(
  `https://stratoplan-school.com/disc/result/?${encodeURIComponent(token)}`
);

  };

  // =========================
  // formdesigner: гибрид (как в app.js + native form242... data.success)
  // =========================
  let fdArmed = false;
  let fdArmTs = 0;
  let fdTimer = null;

  const isTrue = (v) => v === true || v === "true" || v === 1 || v === "1";

  window.addEventListener("message", (e) => {
    const origin = String(e.origin || "");
    let msg = e.data;

    // иногда прилетает строкой
    if (typeof msg === "string") {
      try {
        msg = JSON.parse(msg);
      } catch (_) {
        // ignore
      }
    }
    if (!msg || typeof msg !== "object") return;

    // 1) твои события из iframe (как в app.js)
    if (msg.type === "fd-form-invalid") {
      fdArmed = false;
      clearTimeout(fdTimer);
      return;
    }

    if (msg.type === "fd-form-submit") {
      fdArmed = true;
      fdArmTs = Date.now();
      clearTimeout(fdTimer);
      // страховка 20с: если успех не пришёл — разармим
      fdTimer = setTimeout(() => {
        fdArmed = false;
      }, 20000);
      return;
    }

    if (msg.type === "fd-form-success") {
      clearTimeout(fdTimer);
      fdArmed = false;
      redirectToResult();
      return;
    }

    // 2) нативные сообщения formdesigner: {type:"form242546-...", data:{success:true/false}}
    const isFD = origin.includes("formdesigner.ru") || origin.includes("formdesigner.");
    if (!isFD) return;

    // редиректим только если была попытка сабмита недавно (не ловим фон)
    if (!fdArmed) return;
    if (Date.now() - fdArmTs > 60000) return;

    const ok = isTrue(msg?.data?.success) || isTrue(msg?.success);
    if (ok) {
      clearTimeout(fdTimer);
      fdArmed = false;
      redirectToResult();
    }
  });

  // =========================
  // wiring: wizard open/close
  // =========================
  btnOpenWizard?.addEventListener("click", (e) => {
    e.preventDefault();
    openWizard();
  });

  btnCloseWizard.forEach((x) =>
    x.addEventListener("click", (e) => {
      e.preventDefault();
      closeWizard();
    })
  );

  // Esc закрывает верхнюю открытую модалку (если открыта apruve — закрываем ее, иначе wizard)
  document.addEventListener("keydown", (e) => {
    if (e.key !== "Escape") return;

    if (apruve && apruve.classList.contains("is-open")) {
      closeApruve();
      return;
    }
    if (wizard.classList.contains("is-open")) {
      closeWizard();
    }
  });

  // tabs / nav
  tabs.forEach((t) => t.addEventListener("click", () => setStep(Number(t.dataset.stepBtn))));
  btnPrev?.addEventListener("click", () => setStep(step - 1));
  btnNext?.addEventListener("click", () => { pendingScrollTop = true; setStep(step + 1); });
// =========================
  // finish: НЕ логировать, открыть apruve, сохранить токен
  // =========================
  btnFinish?.addEventListener("click", async () => {
    try {
      const payload = collectPayload();
      const res = score(payload);

      // тут готовим данные для result-страницы
      const pack = {
        v: 1,
        ts: Date.now(),
        score: res,
        // payload,
      };

      resultToken = await encryptToToken(pack);
      sessionStorage.setItem(STORAGE_TOKEN_KEY, resultToken);

      // закрываем тест, открываем apruve
closeWizard();
openApruve();

// ✅ ARM вручную: на мобилках часто НЕ приходит fd-form-submit
fdArmed = true;
fdArmTs = Date.now();
clearTimeout(fdTimer);
fdTimer = setTimeout(() => {
  fdArmed = false;
}, 60000);
    } catch (_) {
      // без console
    }
  });

  // init
  initSortable();
  render();
  syncScrollLock(); // если модалки закрыты — скролл будет включен
})();
