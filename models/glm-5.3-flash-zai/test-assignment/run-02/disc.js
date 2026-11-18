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
  };

  // =========================
  // sortable lists (HTML5 drag)
  // =========================
  const makeSortable = (ul) => {
    const items = () => qsa("li", ul);

    items().forEach((li) => {
      li.setAttribute("draggable", "true");

      li.addEventListener("dragstart", (e) => {
        li.classList.add("is-dragging");
        e.dataTransfer.effectAllowed = "move";
      });

      li.addEventListener("dragend", () => {
        li.classList.remove("is-dragging");
        items().forEach((x) => x.classList.remove("is-over"));
      });

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

  const initSortable = () => qsa(".disc-list", wizard).forEach(makeSortable);

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
    window.location.assign(`/disc/result/?${encodeURIComponent(token)}`);
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
  btnNext?.addEventListener("click", () => setStep(step + 1));

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
    } catch (_) {
      // без console
    }
  });

  // init
  initSortable();
  render();
  syncScrollLock(); // если модалки закрыты — скролл будет включен
})();
