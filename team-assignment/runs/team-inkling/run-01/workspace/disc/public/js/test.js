(function () {
  const STEPS = window.STEPS || [];
  const KEY = 'disc-test-state';
  let state = { step: 0, answers: {} }; // answers: {questionId: [0..3] order of item indices}
  try { const saved = JSON.parse(localStorage.getItem(KEY)); if (saved && saved.answers) state = saved; } catch (e) {}

  const wizard = document.getElementById('wizard');
  const emailStep = document.getElementById('emailStep');
  const resultStep = document.getElementById('resultStep');
  const stepContainer = document.getElementById('stepContainer');
  const backBtn = document.getElementById('backBtn');
  const nextBtn = document.getElementById('nextBtn');
  const progressBar = document.getElementById('progressBar');
  const progressText = document.getElementById('progressText');
  const totalSteps = Object.keys(STEPS).length;

  function persist() { localStorage.setItem(KEY, JSON.stringify(state)); }

  function getQuestions() { return STEPS[state.step]; }

  function stepComplete() {
    const qs = getQuestions();
    return qs.every(q => state.answers[q.id] && state.answers[q.id].length === 4);
  }

  function render() {
    const stepIdx = state.step;
    const qs = STEPS[stepIdx];
    stepContainer.innerHTML = '';
    qs.forEach((q, i) => {
      const card = document.createElement('div');
      card.className = 'question';
      card.innerHTML = '<h3>Вопрос ' + (stepIdx * 3 + i + 1) + '</h3>';
      // ensure default order (as given)
      if (!state.answers[q.id]) {
        state.answers[q.id] = [0, 1, 2, 3];
        persist();
      }
      const order = state.answers[q.id]; // array of item indices, top=most similar
      order.forEach((itemIdx, pos) => {
        card.appendChild(renderItem(q.id, itemIdx, pos, order));
      });
      stepContainer.appendChild(card);
    });

    backBtn.disabled = stepIdx === 0;
    nextBtn.textContent = stepIdx === totalSteps - 1 ? 'Завершить' : 'Далее';
    nextBtn.disabled = !stepComplete();
    progressBar.style.width = ((stepIdx) / totalSteps * 100) + '%';
    progressText.textContent = 'Шаг ' + (stepIdx + 1) + ' из ' + totalSteps;
  }

  function renderItem(qId, itemIdx, pos, order) {
    const q = STEPS[state.step].find(q => q.id === qId);
    const el = document.createElement('div');
    el.className = 'item';
    el.dataset.qid = qId;
    el.dataset.item = itemIdx;
    el.innerHTML = '<span class="item-handle">⠿</span><span class="item-text">' + escapeHtml(q.items[itemIdx].text) + '</span>';

    // up/down buttons (mouse+touch friendly)
    const btnUp = document.createElement('button');
    btnUp.className = 'btn btn-secondary'; btnUp.textContent = '↑'; btnUp.setAttribute('aria-label', 'Выше');
    btnUp.onclick = () => move(qId, pos, -1);
    const btnDown = document.createElement('button');
    btnDown.className = 'btn btn-secondary'; btnDown.textContent = '↓'; btnDown.setAttribute('aria-label', 'Ниже');
    btnDown.onclick = () => move(qId, pos, +1);
    btnUp.style.padding = '6px 10px'; btnDown.style.padding = '6px 10px';
    el.appendChild(btnUp); el.appendChild(btnDown);

    attachDrag(el, qId, pos);
    return el;
  }

  function escapeHtml(s) { const d = document.createElement('div'); d.textContent = s; return d.innerHTML; }

  function move(qId, pos, delta) {
    const order = state.answers[qId];
    const newPos = pos + delta;
    if (newPos < 0 || newPos >= order.length) return;
    [order[pos], order[newPos]] = [order[newPos], order[pos]];
    state.answers[qId] = order;
    persist();
    render();
  }

  // HTML5 drag & drop (desktop) + pointer-based touch fallback via buttons
  function attachDrag(el, qId, pos) {
    el.setAttribute('draggable', 'true');
    el.addEventListener('dragstart', (e) => { el.classList.add('dragging'); e.dataTransfer.setData('text/plain', String(pos)); });
    el.addEventListener('dragend', () => el.classList.remove('dragging'));
    el.addEventListener('dragover', (e) => { e.preventDefault(); });
    el.addEventListener('drop', (e) => {
      e.preventDefault();
      const from = parseInt(e.dataTransfer.getData('text/plain'), 10);
      const to = parseInt(el.dataset.pos, 10);
      if (isNaN(from) || isNaN(to) || from === to) return;
      const order = state.answers[qId];
      const [item] = order.splice(from, 1);
      order.splice(to, 0, item);
      state.answers[qId] = order;
      persist();
      render();
    });
  }

  // set data-pos on each item after render (needed for drop target)
  function markPositions() {
    document.querySelectorAll('#stepContainer .item').forEach((el, idx) => {
      // within question, compute local pos
    });
  }

  backBtn.onclick = () => { if (state.step > 0) { state.step--; persist(); render(); } };
  nextBtn.onclick = () => {
    if (!stepComplete()) return;
    if (state.step < totalSteps - 1) { state.step++; persist(); render(); }
    else { showEmailStep(); }
  };

  function showEmailStep() {
    wizard.classList.add('hidden');
    emailStep.classList.remove('hidden');
    emailStep.querySelector('input').focus();
  }

  document.getElementById('emailForm').onsubmit = async (e) => {
    e.preventDefault();
    const email = document.getElementById('email').value.trim();
    const err = document.getElementById('emailError');
    err.textContent = '';
    nextBtn.disabled = true;
    try {
      const res = await fetch('/test/finish', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, answers: state.answers }),
      });
      const data = await res.json();
      if (!res.ok || !data.ok) { err.textContent = data.error || 'Ошибка'; nextBtn.disabled = false; return; }
      showResult(data);
      localStorage.removeItem(KEY);
    } catch (e2) {
      err.textContent = 'Не удалось связаться с сервером';
      nextBtn.disabled = false;
    }
  };

  function showResult(data) {
    emailStep.classList.add('hidden');
    wizard.classList.add('hidden');
    resultStep.classList.remove('hidden');
    const labels = { d: 'D — Доминирование', i: 'I — Влияние', s: 'S — Стабильность', c: 'C — Сознательность' };
    const sc = document.getElementById('scores');
    sc.innerHTML = '';
    for (const k of ['d','i','s','c']) {
      const card = document.createElement('div'); card.className = 'score-card';
      card.innerHTML = '<div class="label">' + labels[k] + '</div><div class="value">' + data.scores[k] + '</div>';
      sc.appendChild(card);
    }
    const interpBlock = document.getElementById('interpretationBlock');
    if (data.interpretation) {
      const div = document.createElement('div'); div.className = 'interpretation'; div.textContent = data.interpretation;
      interpBlock.appendChild(div);
    } else {
      interpBlock.innerHTML = '<div class="interpretation">Интерпретация временно недоступна — результаты подсчитаны, но текст индивидуального описания не получен.</div>';
    }
    const ms = document.getElementById('mailStatus');
    if (data.mail_sent) {
      ms.className = 'mail-status';
      ms.textContent = 'Результат отправлен на ' + data.email + '.';
    } else {
      ms.className = 'mail-status error';
      ms.textContent = data.mail_reason || 'Отправка письма недоступна.';
    }
  }

  // set data-pos correctly on drop targets: render() re-renders; attach positions there
  const origRender = render;
  render = function () {
    origRender();
    document.querySelectorAll('#stepContainer .question').forEach(card => {
      card.querySelectorAll('.item').forEach((el, i) => { el.dataset.pos = i; });
    });
  };

  render();
})();
