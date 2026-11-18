(() => {
  const ENDPOINT = "./click-track.php";
  const TRACK_HOST_SUFFIX = "stratoplan-school.com";

  // стабильный uid для уникальных (в рамках браузера)
  function getUid() {
    const key = "disc_uid_v1";
    let uid = localStorage.getItem(key);
    if (!uid) {
      uid = (crypto.randomUUID && crypto.randomUUID()) || ("u_" + Math.random().toString(16).slice(2));
      localStorage.setItem(key, uid);
    }
    return uid;
  }

  function toUrl(href) {
    try { return new URL(href, location.href); } catch { return null; }
  }

  function isTracked(url) {
    if (!url) return false;
    const h = url.hostname.toLowerCase();
    // stratoplan-school.com и любые поддомены
    return h === TRACK_HOST_SUFFIX || h.endsWith("." + TRACK_HOST_SUFFIX);
  }

  function label(el) {
    const t = (el.innerText || el.textContent || "").trim().replace(/\s+/g, " ");
    if (t) return t.slice(0, 160);
    const aria = el.getAttribute("aria-label");
    if (aria) return aria.slice(0, 160);
    return el.tagName.toLowerCase();
  }

  document.addEventListener("click", (e) => {
    const a = e.target.closest("a[href]");
    if (!a) return;

    const url = toUrl(a.getAttribute("href"));
    if (!isTracked(url)) return;

    // канонизация: убираем hash? нет — оставляем, он важен
    const payload = {
      uid: getUid(),
      from: location.href,
      to: url.href,
      text: label(a),
      ts: Date.now()
    };

    // не блокируем навигацию: sendBeacon или fetch keepalive
    const body = JSON.stringify(payload);

    if (navigator.sendBeacon) {
      navigator.sendBeacon(ENDPOINT, new Blob([body], { type: "application/json" }));
    } else {
      fetch(ENDPOINT, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body,
        keepalive: true
      }).catch(() => {});
    }
  }, true);
})();
