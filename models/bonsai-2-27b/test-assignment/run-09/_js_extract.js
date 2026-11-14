

(function(){
  const $ = (s,r)=> (r||document).querySelector(s);
  const $$ = (s,r)=> Array.from((r||document).querySelectorAll(s));

  const modal = $('#wizardmodal');
  const rootwizard = $('#rootwizard');
  const tabsEl = $('#discTabs');
  const tabs = $$('#discTabs .disc-tab');
  const panes = $$('#rootwizard .disc-pane');
  const prevBtn = $('[data-disc-prev]');
  const nextBtn = $('[data-disc-next]');
  const finishBtn = $('[data-disc-finish]');
  const progress = $('#discProgress');
  const progressWrap = $('.disc-progress');
  const btnStart = $('#btnStart');
  const modalCloseBtn = $('#modalCloseBtn');
  const result = $('#discResult');
  const resultScore = $('#discResultScore');
  const resultChart = $('#discResultChart');

  const headEl = $('.disc-modal__head');      // wizard head (first in DOM)
  const wizardActions = $('#wizardActions');

  let step = 0;
  const STEPS = 8;

  /* initial order per list, for reset */
  const initialOrder = {};
  $$('.disc-list').forEach(ul=>{ initialOrder[ul] = Array.from(ul.children); });

  function lockScroll(on){
    document.body.classList.toggle('no-scroll', !!on);
  }
  function startTest(){
    $$('.disc-list').forEach(ul=>{
      (initialOrder[ul]||[]).forEach(el=> ul.appendChild(el));
    });
    hideResult();
    render(0);
  }
  function openModal(){
    startTest();
    modal.classList.add('is-open');
    modal.setAttribute('aria-hidden','false');
    lockScroll(true);
    setTimeout(()=> modalCloseBtn.focus(),0);
  }
  function closeModal(){
    modal.classList.remove('is-open');
    modal.setAttribute('aria-hidden','true');
    lockScroll(false);
    clearDrag();
  }

  function render(stepIdx){
    step = ((stepIdx % STEPS) + STEPS) % STEPS;
    panes.forEach((p,i)=> p.classList.toggle('is-active', i===step));
    tabs.forEach((t,i)=> t.classList.toggle('is-active', i===step));
    progress.style.width = (step / STEPS * 100) + '%';
    prevBtn.disabled = (step === 0);
    nextBtn.style.display = (step === STEPS-1) ? 'none' : '';
    finishBtn.hidden = (step !== STEPS-1);
  }
  function goNext(){ if(step === STEPS-1) return; render(step+1); }
  function goPrev(){ if(step === 0) return; render(step-1); }
  prevBtn.onclick = goPrev;
  nextBtn.onclick = goNext;

  function score(payload){
    const maj = [], min = [];
    payload.forEach(x=>{ if(x.pos===0) maj.push(x.type); if(x.pos===3) min.push(x.type); });
    const cnt=(a,ch)=> a.reduce((s,v)=> s + (v===ch ? 1:0), 0);
    return {
      d: cnt(maj,'d')-cnt(min,'d'),
      i: cnt(maj,'i')-cnt(min,'i'),
      s: cnt(maj,'s')-cnt(min,'s'),
      c: cnt(maj,'c')-cnt(min,'c')
    };
  }
  function showResult(res){
    headEl.style.display = 'none';
    tabsEl.style.display = 'none';
    rootwizard.style.display = 'none';
    progressWrap.style.display = 'none';
    wizardActions.style.display = 'none';
    result.hidden = false;
    resultScore.textContent = 'D:'+res.d+', I:'+res.i+', S:'+res.s+', C:'+res.c;
    const chart = [['D','Доминирование',res.d],['I','Влияние',res.i],['S','Стабильность',res.s],['C','Соответствие',res.c]];
    resultChart.innerHTML = chart.map(([code,label,val])=>{
      const w = Math.max(0, Math.min(100, (val+8)/16*100));
      return '<div class="disc-type" data-type="'+code+'">'+
        '<span class="disc-type__label">'+label+'</span>'+
        '<span class="disc-type__bar"><i class="disc-type__fill disc-type__fill--'+code+'" style="width:'+w+'%"></i></span>'+
        '<span class="disc-type__value">'+val+'</span>'+
      '</div>';
    }).join('');
    result.focus && result.focus();
  }
  function hideResult(){
    headEl.style.display = '';
    tabsEl.style.display = '';
    rootwizard.style.display = '';
    progressWrap.style.display = '';
    wizardActions.style.display = '';
    result.hidden = true;
  }

  /* finish */
  finishBtn.onclick = function(){
    const payload = [];
    $$('.disc-list').forEach((ul,li)=>{
      Array.from(ul.children).forEach((liEl, idx)=>{
        payload.push({ list:li, pos:idx, type:liEl.getAttribute('data-type') });
      });
    });
    showResult(score(payload));
  };
  $('[data-disc-retry]').onclick = startTest;
  $$('[data-disc-close]').forEach(b=> b.onclick = closeModal);

  btnStart.onclick = openModal;
  document.addEventListener('keydown', e=>{
    if(e.key==='Escape' && modal.classList.contains('is-open')) closeModal();
  });

  /* ---- drag & drop (pointer-based: mouse + touch) ---- */
  let drag = null;
  const itemsIn = (list)=> Array.from(list.children);

  function moveToIndex(list,item,idx){
    const items = itemsIn(list), n = items.length;
    const current = items.indexOf(item);
    if(idx === current || idx < 0) return;
    idx = Math.min(idx, n-1);
    if(idx === current) return;
    const ref = items[idx];
    if(idx > current){
      list.insertBefore(item, ref ? ref.nextSibling : null);
    }else{
      list.insertBefore(item, ref);
    }
  }
  function getTargetIndex(y,list,item){
    const items = itemsIn(list);
    const last = items.indexOf(item);
    let target = last;
    for(const it of items){
      if(it === item) continue;
      const r = it.getBoundingClientRect();
      const idx = items.indexOf(it);
      if(y >= r.top + r.height/2){
        if(idx > last) target = idx;
      }else{
        if(idx < last) target = idx;
      }
    }
    return target;
  }
  function onMove(e){
    if(!drag) return;
    const dx = e.clientX - drag.x0, dy = e.clientY - drag.y0;
    if(!drag.moved && Math.hypot(dx,dy) < 5) return;
    if(!drag.moved){ drag.moved = true; drag.item.classList.add('is-dragging'); }
    const list = drag.list, item = drag.item, y = e.clientY;
    const items = itemsIn(list);
    items.forEach(it=> it.classList.remove('is-over'));
    let over = null;
    for(const it of items){
      if(it === item) continue;
      const r = it.getBoundingClientRect();
      if(y >= r.top - 4 && y <= r.bottom + 4){ over = it; break; }
    }
    if(over) over.classList.add('is-over');
    const target = getTargetIndex(y,list,item);
    moveToIndex(list,item,target);
  }
  function onUp(e){
    if(!drag) return;
    const { item, pointerId } = drag;
    try{ item.releasePointerCapture(pointerId); }catch(err){}
    item.classList.remove('is-dragging');
    $$('.disc-item').forEach(it=> it.classList.remove('is-over'));
    item.removeEventListener('pointermove', onMove);
    item.removeEventListener('pointerup', onUp);
    item.removeEventListener('pointercancel', onUp);
    drag = null;
  }
  function clearDrag(){ if(drag){ onUp({}); } }
  function startDrag(e,item,list){
    if(drag) return;
    e.preventDefault();
    drag = { item, list, pointerId:e.pointerId, x0:e.clientX, y0:e.clientY, moved:false };
    try{ item.setPointerCapture(e.pointerId); }catch(err){}
    item.addEventListener('pointermove', onMove);
    item.addEventListener('pointerup', onUp);
    item.addEventListener('pointercancel', onUp);
  }
  $$('.disc-list').forEach(list=>{
    list.addEventListener('pointerdown', e=>{
      const item = e.target.closest('.disc-item');
      if(!item) return;
      startDrag(e,item,list);
    });
  });
})();

