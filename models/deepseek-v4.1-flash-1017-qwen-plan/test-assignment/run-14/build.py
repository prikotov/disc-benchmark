import json, html
from pathlib import Path

base = Path(__file__).parent
data = json.loads((base / 'src' / 'questions_extracted.json').read_text(encoding='utf-8'))
assert len(data) == 24
for lst in data:
    assert len(lst) == 4
    assert sorted(t for t, _ in lst) == ['c', 'd', 'i', 's']

labels = ['Первый', 'Второй', 'Третий', 'Четвертый', 'Пятый', 'Шестой', 'Седьмой', 'Восьмой']

grip = '''<svg class="icon icon--grip" viewBox="0 0 16 16" aria-hidden="true"><use href="#icon-grip"></use></svg>'''

def item_html(text, typ, idx):
    return (
        f'<li class="disc-item" data-type="{typ}" tabindex="0">'
        f'<span class="disc-item__text">{text}</span>'
        f'<span class="disc-handle" title="Перетащите, чтобы изменить порядок" aria-hidden="true">{grip}</span>'
        f'</li>'
    )

cards = []
list_no = 1
for step in range(8):
    cards_step = []
    for card in range(3):
        entries = data[step * 3 + card]
        lis = '\n'.join('              ' + item_html(text, typ, list_no) for typ, text in entries)
        cards_step.append(f'''          <article class="disc-card">
            <div class="disc-card__top">
              <span class="disc-card__label">Я наиболее</span>
              <svg class="disc-card__arrow disc-card__arrow--up" viewBox="0 0 24 24" aria-hidden="true"><use href="#icon-chevron-up"></use></svg>
            </div>
            <ul class="disc-list" id="draggable-list{list_no}" aria-label="Вопрос {list_no}">
{lis}
            </ul>
            <div class="disc-card__bottom">
              <span class="disc-card__label">Я наименее</span>
              <svg class="disc-card__arrow disc-card__arrow--down" viewBox="0 0 24 24" aria-hidden="true"><use href="#icon-chevron-down"></use></svg>
            </div>
          </article>''')
        list_no += 1
    pane_hidden = '' if step == 0 else ' hidden'
    pane_active = ' is-active' if step == 0 else ''
    cards.append(f'''      <div class="disc-pane{pane_active}" data-step-pane="{step}" id="tab{step+1}" role="tabpanel" aria-labelledby="step-tab-{step}"{pane_hidden}>
        <div class="disc-grid3">
{chr(10).join(cards_step)}
        </div>
      </div>''')

tabs = []
for i, label in enumerate(labels):
    active = ' is-active' if i == 0 else ''
    selected = 'true' if i == 0 else 'false'
    tabindex = '0' if i == 0 else '-1'
    tabs.append(f'        <button class="disc-tab{active}" id="step-tab-{i}" type="button" role="tab" aria-selected="{selected}" aria-controls="tab{i+1}" tabindex="{tabindex}" data-step-btn="{i}">{label}</button>')

template = r'''<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light">
  <meta name="description" content="Тест DISC: 8 шагов и 24 вопроса. Расставьте качества по степени сходства и узнайте свои баллы.">
  <title>Тест DISC — поведенческий профиль</title>
  <style>
    :root{
      --bg:#f2eee6;
      --surface:#fffdf8;
      --ink:#1b2321;
      --muted:#6d746f;
      --line:rgba(27,35,33,.12);
      --line-strong:rgba(27,35,33,.2);
      --soft:#ece7dd;
      --accent:#206b55;
      --accent-strong:#175241;
      --accent-soft:#e2efe9;
      --d:#c6533e;
      --i:#b88326;
      --s:#2f7d5f;
      --c:#356aa4;
      --font-display:Georgia,"Iowan Old Style","Palatino Linotype","Times New Roman",serif;
      --font-sans:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;
      --shadow:0 28px 70px -42px rgba(27,35,33,.45),0 1px 0 rgba(255,255,255,.7) inset;
    }

    *,*::before,*::after{box-sizing:border-box}

    html{
      -webkit-text-size-adjust:100%;
      scroll-behavior:smooth;
    }

    body{
      margin:0;
      min-height:100vh;
      color:var(--ink);
      font-family:var(--font-sans);
      font-size:16px;
      line-height:1.45;
      background-color:var(--bg);
      background-image:
        radial-gradient(58rem 34rem at 4% -12%,rgba(206,228,215,.9),transparent 62%),
        radial-gradient(46rem 30rem at 102% -4%,rgba(239,218,190,.78),transparent 58%),
        linear-gradient(180deg,#f8f5ef 0%,#f2eee6 54%,#f5f1e9 100%);
      background-repeat:no-repeat;
    }

    body.is-dragging,
    body.is-dragging *{
      cursor:grabbing!important;
      user-select:none!important;
    }

    [hidden]{display:none!important}

    .app{
      width:100%;
      max-width:1240px;
      margin:0 auto;
      padding:0 28px 30px;
      display:flex;
      min-height:100vh;
      flex-direction:column;
    }

    .site-header{
      display:flex;
      align-items:center;
      justify-content:space-between;
      gap:18px;
      padding:22px 0 18px;
    }

    .brand{
      display:inline-flex;
      align-items:center;
      gap:11px;
      color:var(--ink);
      text-decoration:none;
    }

    .brand-mark{
      width:39px;
      height:39px;
      flex:none;
      filter:drop-shadow(0 5px 8px rgba(27,35,33,.09));
    }

    .brand-text{
      display:flex;
      align-items:baseline;
      gap:6px;
      font-size:17px;
      font-weight:750;
      letter-spacing:.16em;
    }

    .brand-text span{
      color:var(--muted);
      font-size:13px;
      font-weight:600;
      letter-spacing:.02em;
    }

    .header-meta{
      display:flex;
      align-items:center;
      gap:9px;
      color:var(--muted);
      font-size:13px;
      font-weight:550;
      white-space:nowrap;
    }

    .header-meta__dot{
      width:7px;
      height:7px;
      border-radius:50%;
      background:var(--accent);
      box-shadow:0 0 0 4px rgba(32,107,85,.11);
      flex:none;
    }

    .header-meta__sep{opacity:.45}

    main{
      flex:1;
      display:flex;
      flex-direction:column;
    }

    .screen{
      width:100%;
      animation:screenIn .4s cubic-bezier(.2,.75,.25,1) both;
    }

    @keyframes screenIn{
      from{opacity:0;transform:translateY(8px)}
      to{opacity:1;transform:none}
    }

    .test-shell{
      width:100%;
      padding:32px 36px 26px;
      border:1px solid var(--line);
      border-radius:28px;
      background:rgba(255,253,248,.86);
      box-shadow:var(--shadow);
      -webkit-backdrop-filter:blur(10px);
      backdrop-filter:blur(10px);
    }

    .test-head__top{
      display:flex;
      align-items:center;
      justify-content:space-between;
      gap:18px;
      min-height:18px;
    }

    .eyebrow{
      display:inline-flex;
      align-items:center;
      gap:8px;
      color:var(--accent);
      font-size:11px;
      line-height:1;
      font-weight:750;
      letter-spacing:.15em;
      text-transform:uppercase;
    }

    .eyebrow__dot{
      width:6px;
      height:6px;
      border-radius:50%;
      background:var(--accent);
      flex:none;
    }

    .test-meta{
      color:var(--muted);
      font-size:12px;
      font-weight:600;
      letter-spacing:.02em;
      white-space:nowrap;
    }

    .test-title{
      margin:10px 0 7px;
      font-family:var(--font-display);
      font-size:clamp(38px,5vw,56px);
      font-weight:600;
      line-height:.98;
      letter-spacing:-.045em;
    }

    .test-sub{
      max-width:790px;
      margin:0;
      color:var(--ink);
      font-size:15.5px;
    }

    .test-lead{
      max-width:790px;
      margin:6px 0 0;
      color:var(--muted);
      font-size:15px;
    }

    .disc-modal__tabs{
      display:flex;
      flex-wrap:wrap;
      gap:7px;
      margin-top:21px;
      scrollbar-width:none;
    }

    .disc-modal__tabs::-webkit-scrollbar{display:none}

    .disc-tab{
      appearance:none;
      border:1px solid transparent;
      border-radius:999px;
      padding:9px 14px;
      background:var(--soft);
      color:var(--muted);
      font:inherit;
      font-size:12.5px;
      line-height:1;
      font-weight:650;
      letter-spacing:.01em;
      cursor:pointer;
      transition:background .18s ease,color .18s ease,box-shadow .18s ease,transform .18s ease;
    }

    .disc-tab:hover{
      background:#e5ded1;
      color:var(--ink);
    }

    .disc-tab.is-active{
      background:var(--ink);
      color:#fff;
      box-shadow:0 7px 16px -9px rgba(27,35,33,.65);
    }

    .disc-tab:focus-visible{
      outline:2px solid var(--accent);
      outline-offset:2px;
    }

    .step-status{
      display:flex;
      align-items:center;
      justify-content:space-between;
      gap:16px;
      margin-top:17px;
      color:var(--muted);
      font-size:12.5px;
      font-weight:550;
    }

    .step-status strong{
      color:var(--ink);
      font-weight:750;
    }

    .step-status__hint{
      display:inline-flex;
      align-items:center;
      gap:6px;
      text-align:right;
    }

    .step-status__hint .icon{
      width:14px;
      height:14px;
      color:var(--muted);
    }

    .disc-progress{
      height:6px;
      margin-top:9px;
      overflow:hidden;
      border-radius:999px;
      background:#e7e1d6;
    }

    .disc-progress__bar{
      width:12.5%;
      height:100%;
      border-radius:inherit;
      background:linear-gradient(90deg,var(--accent),#6e9b6d 58%,#c3a14d);
      transition:width .34s cubic-bezier(.2,.75,.25,1);
    }

    .wizard{margin-top:21px}

    .disc-pane{display:none}

    .disc-pane.is-active{
      display:block;
      animation:paneIn .28s cubic-bezier(.2,.75,.25,1) both;
    }

    @keyframes paneIn{
      from{opacity:0;transform:translateY(5px)}
      to{opacity:1;transform:none}
    }

    .disc-grid3{
      display:grid;
      grid-template-columns:repeat(3,minmax(0,1fr));
      gap:14px;
    }

    .disc-card{
      display:flex;
      flex-direction:column;
      min-width:0;
      overflow:hidden;
      border:1px solid var(--line);
      border-radius:18px;
      background:#fff;
      box-shadow:0 13px 30px -28px rgba(27,35,33,.5);
    }

    .disc-card__top,
    .disc-card__bottom{
      display:flex;
      align-items:center;
      justify-content:space-between;
      gap:10px;
      padding:13px 14px;
      background:#faf7f1;
    }

    .disc-card__bottom{
      border-top:1px solid var(--line);
      background:#f7f3ec;
    }

    .disc-card__label{
      color:#5d625e;
      font-size:11px;
      line-height:1;
      font-weight:750;
      letter-spacing:.13em;
      text-transform:uppercase;
    }

    .disc-card__arrow{
      width:15px;
      height:15px;
      flex:none;
      color:#9b988e;
      fill:none;
      stroke:currentColor;
      stroke-width:2;
      stroke-linecap:round;
      stroke-linejoin:round;
    }

    .disc-card__arrow--up{color:var(--accent)}

    .disc-list{
      flex:1;
      margin:0;
      padding:0;
      list-style:none;
    }

    .disc-item{
      position:relative;
      display:flex;
      align-items:center;
      min-height:57px;
      padding:11px 45px 11px 15px;
      border-top:1px solid var(--line);
      background:#fff;
      color:var(--ink);
      font-size:14.5px;
      line-height:1.28;
      cursor:grab;
      touch-action:pan-y;
      user-select:none;
      -webkit-user-select:none;
      -webkit-tap-highlight-color:transparent;
      transition:background .16s ease,box-shadow .16s ease;
    }

    .disc-item:first-child{border-top:0}

    .disc-item:hover{background:#fcfaf6}

    .disc-item:focus-visible{
      z-index:2;
      outline:2px solid var(--accent);
      outline-offset:-3px;
    }

    .disc-item__text{
      flex:1;
      min-width:0;
    }

    .disc-handle{
      position:absolute;
      top:50%;
      right:6px;
      display:grid;
      width:36px;
      height:42px;
      place-items:center;
      transform:translateY(-50%);
      border-radius:10px;
      color:#a49e92;
      cursor:grab;
      touch-action:none;
      transition:background .16s ease,color .16s ease;
    }

    .disc-handle:hover{
      background:var(--soft);
      color:var(--ink);
    }

    .disc-handle .icon{
      width:16px;
      height:16px;
      display:block;
      pointer-events:none;
    }

    .disc-item.is-ghost-source{
      background:#fcfaf6;
      opacity:.22;
    }

    .disc-item.is-drop-before::before{
      position:absolute;
      z-index:4;
      top:-1px;
      right:8px;
      left:8px;
      height:3px;
      border-radius:999px;
      background:var(--accent);
      content:"";
    }

    .disc-list.is-drop-end::after{
      display:block;
      height:3px;
      margin:0 8px;
      border-radius:999px;
      background:var(--accent);
      content:"";
    }

    .disc-drag-ghost{
      position:fixed!important;
      z-index:10000;
      width:auto;
      margin:0!important;
      border:1px solid var(--line-strong)!important;
      border-radius:13px!important;
      background:#fff!important;
      box-shadow:0 18px 38px -15px rgba(27,35,33,.4)!important;
      opacity:.98!important;
      pointer-events:none!important;
      transform:rotate(-1deg) scale(1.018);
      transform-origin:50% 50%;
      cursor:grabbing!important;
    }

    .disc-actions{
      display:flex;
      align-items:center;
      justify-content:space-between;
      gap:12px;
      margin-top:22px;
      padding-top:18px;
      border-top:1px solid var(--line);
    }

    .disc-actions__right{
      display:flex;
      align-items:center;
      justify-content:flex-end;
      gap:9px;
    }

    .disc-btn{
      appearance:none;
      display:inline-flex;
      align-items:center;
      justify-content:center;
      gap:8px;
      min-height:47px;
      padding:0 23px;
      border:1px solid var(--line-strong);
      border-radius:999px;
      background:#fff;
      color:var(--ink);
      font:inherit;
      font-size:14px;
      line-height:1;
      font-weight:700;
      cursor:pointer;
      transition:background .18s ease,border-color .18s ease,color .18s ease,transform .18s ease,box-shadow .18s ease;
    }

    .disc-btn:hover:not(:disabled){transform:translateY(-1px)}

    .disc-btn:active:not(:disabled){transform:none}

    .disc-btn:focus-visible{
      outline:2px solid var(--accent);
      outline-offset:3px;
    }

    .disc-btn:disabled{
      opacity:.36;
      cursor:not-allowed;
    }

    .disc-btn .icon{
      width:17px;
      height:17px;
      fill:none;
      stroke:currentColor;
      stroke-width:2;
      stroke-linecap:round;
      stroke-linejoin:round;
    }

    .disc-btn--ghost{
      background:transparent;
      border-color:transparent;
      color:var(--muted);
    }

    .disc-btn--ghost:hover:not(:disabled){
      background:var(--soft);
      color:var(--ink);
    }

    .disc-btn--primary{
      border-color:var(--accent);
      background:var(--accent);
      color:#fff;
      box-shadow:0 12px 22px -14px rgba(32,107,85,.75);
    }

    .disc-btn--primary:hover:not(:disabled){
      border-color:var(--accent-strong);
      background:var(--accent-strong);
    }

    .disc-btn--finish{
      border-color:var(--ink);
      background:var(--ink);
      box-shadow:0 12px 22px -14px rgba(27,35,33,.7);
    }

    .disc-btn--finish:hover:not(:disabled){
      border-color:#0f1715;
      background:#0f1715;
    }

    .keyboard-hint{
      margin:15px 0 0;
      color:#96938a;
      font-size:11.5px;
      line-height:1.4;
      text-align:center;
    }

    .keyboard-hint kbd{
      display:inline-block;
      padding:1px 5px;
      border:1px solid var(--line);
      border-bottom-color:var(--line-strong);
      border-radius:5px;
      background:#fbf9f4;
      color:#79766d;
      font:inherit;
      font-size:10.5px;
    }

    .result-shell{
      width:100%;
      max-width:1000px;
      margin:0 auto;
      padding:42px 48px 36px;
      border:1px solid var(--line);
      border-radius:30px;
      background:rgba(255,253,248,.9);
      box-shadow:var(--shadow);
      -webkit-backdrop-filter:blur(10px);
      backdrop-filter:blur(10px);
      text-align:center;
    }

    .result-head .eyebrow{justify-content:center}

    .result-title{
      margin:11px 0 8px;
      font-family:var(--font-display);
      font-size:clamp(38px,5vw,58px);
      font-weight:600;
      line-height:.98;
      letter-spacing:-.045em;
    }

    .result-sub{
      margin:0;
      color:var(--muted);
      font-size:15px;
    }

    .score-hero{
      max-width:760px;
      margin:26px auto 20px;
      padding:21px 25px 23px;
      border-radius:22px;
      background:
        radial-gradient(38rem 20rem at 10% -50%,rgba(63,133,106,.32),transparent 65%),
        linear-gradient(135deg,#1c2924,#111917);
      color:#fff;
      box-shadow:0 24px 45px -32px rgba(17,25,23,.9);
    }

    .score-hero__label{
      margin-bottom:10px;
      color:rgba(255,255,255,.58);
      font-size:10.5px;
      font-weight:750;
      letter-spacing:.17em;
      text-transform:uppercase;
    }

    .score-string{
      font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace;
      font-size:clamp(19px,3.5vw,32px);
      line-height:1.15;
      font-weight:600;
      letter-spacing:.035em;
      font-variant-numeric:tabular-nums;
      overflow-wrap:anywhere;
    }

    .score-grid{
      display:grid;
      grid-template-columns:repeat(4,minmax(0,1fr));
      gap:11px;
      margin:0 auto;
      text-align:left;
    }

    .score-card{
      position:relative;
      min-width:0;
      overflow:hidden;
      padding:17px 17px 16px;
      border:1px solid var(--line);
      border-radius:17px;
      background:#fff;
      box-shadow:0 10px 24px -24px rgba(27,35,33,.45);
      --card-color:var(--accent);
    }

    .score-card::before{
      position:absolute;
      top:0;
      right:0;
      left:0;
      height:4px;
      background:var(--card-color);
      content:"";
    }

    .score-card--d{--card-color:var(--d)}
    .score-card--i{--card-color:var(--i)}
    .score-card--s{--card-color:var(--s)}
    .score-card--c{--card-color:var(--c)}

    .score-card__letter{
      color:var(--card-color);
      font-family:var(--font-display);
      font-size:39px;
      line-height:1;
      font-weight:600;
      letter-spacing:-.04em;
    }

    .score-card__name{
      margin-top:9px;
      color:var(--ink);
      font-size:12.5px;
      line-height:1.2;
      font-weight:750;
      letter-spacing:.02em;
    }

    .score-card__ru{
      margin-top:2px;
      color:var(--muted);
      font-size:11.5px;
      line-height:1.25;
    }

    .score-card__value{
      margin-top:15px;
      color:var(--card-color);
      font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace;
      font-size:29px;
      line-height:1;
      font-weight:650;
      font-variant-numeric:tabular-nums;
    }

    .score-card__value-label{
      margin-top:4px;
      color:#aaa59a;
      font-size:10px;
      font-weight:650;
      letter-spacing:.08em;
      text-transform:uppercase;
    }

    .result-note{
      max-width:720px;
      margin:23px auto 0;
      color:var(--muted);
      font-size:13px;
      line-height:1.65;
    }

    .result-note p{margin:0}

    .result-note p + p{margin-top:5px}

    .result-actions{
      display:flex;
      justify-content:center;
      margin-top:25px;
    }

    .site-footer{
      display:flex;
      align-items:center;
      justify-content:space-between;
      gap:16px;
      padding:20px 2px 0;
      color:#8d8b82;
      font-size:11px;
      line-height:1.4;
    }

    .site-footer span:first-child{
      font-weight:650;
      letter-spacing:.04em;
    }

    .sr-only{
      position:absolute!important;
      width:1px!important;
      height:1px!important;
      padding:0!important;
      margin:-1px!important;
      overflow:hidden!important;
      clip:rect(0,0,0,0)!important;
      white-space:nowrap!important;
      border:0!important;
    }

    .svg-sprite{
      position:absolute;
      width:0;
      height:0;
      overflow:hidden;
    }

    .icon{
      display:block;
      width:18px;
      height:18px;
      fill:none;
      stroke:currentColor;
      stroke-width:2;
      stroke-linecap:round;
      stroke-linejoin:round;
    }

    .icon--grip{
      fill:currentColor;
      stroke:none;
    }

    @media (max-width:900px){
      .app{padding-right:20px;padding-left:20px}
      .test-shell{padding:26px 24px 22px;border-radius:24px}
      .disc-grid3{grid-template-columns:1fr;gap:11px}
      .disc-card__top,.disc-card__bottom{padding:12px 14px}
      .disc-item{min-height:54px}
      .result-shell{padding:34px 28px 30px;border-radius:25px}
      .score-grid{grid-template-columns:repeat(2,minmax(0,1fr))}
      .header-meta{font-size:12px}
    }

    @media (max-width:640px){
      .app{padding:0 13px 24px}
      .site-header{padding:17px 0 13px}
      .brand-mark{width:34px;height:34px}
      .brand-text{font-size:15px}
      .brand-text span{font-size:11px}
      .header-meta__extra{display:none}
      .test-shell{padding:22px 15px 17px;border-radius:21px}
      .test-head__top{gap:10px}
      .eyebrow{font-size:10px;letter-spacing:.12em}
      .test-meta{font-size:11px}
      .test-title{font-size:clamp(35px,10vw,44px);margin-top:9px}
      .test-sub{font-size:14px}
      .test-lead{font-size:13.5px}
      .disc-modal__tabs{
        flex-wrap:nowrap;
        justify-content:flex-start;
        margin-right:-15px;
        padding-right:15px;
        overflow-x:auto;
        overscroll-behavior-x:contain;
        -webkit-overflow-scrolling:touch;
      }
      .disc-tab{flex:0 0 auto;padding:9px 13px;font-size:12px}
      .step-status{margin-top:14px;font-size:11.5px}
      .step-status__hint{font-size:0;gap:0}
      .step-status__hint .icon{width:16px;height:16px}
      .wizard{margin-top:17px}
      .disc-actions{
        flex-direction:column-reverse;
        align-items:stretch;
        gap:8px;
        margin-top:18px;
        padding-top:15px;
      }
      .disc-actions__right{flex-direction:column;align-items:stretch}
      .disc-btn{width:100%;min-height:48px}
      .keyboard-hint{display:none}
      .result-shell{padding:27px 15px 24px;border-radius:22px}
      .result-title{font-size:clamp(36px,11vw,46px)}
      .result-sub{font-size:13.5px}
      .score-hero{margin-top:22px;padding:18px 14px 20px;border-radius:18px}
      .score-grid{gap:8px}
      .score-card{padding:14px 13px 13px;border-radius:14px}
      .score-card__letter{font-size:33px}
      .score-card__name{font-size:11.5px}
      .score-card__ru{font-size:10.5px}
      .score-card__value{font-size:25px;margin-top:12px}
      .result-note{font-size:12px;line-height:1.6}
      .site-footer{flex-direction:column;align-items:flex-start;gap:5px;padding:17px 2px 0;font-size:10.5px}
    }

    @media (max-width:390px){
      .header-meta{display:none}
      .disc-item{font-size:13.5px;padding-left:13px}
      .score-grid{grid-template-columns:1fr 1fr}
    }

    @media (prefers-reduced-motion:reduce){
      html{scroll-behavior:auto}
      *,*::before,*::after{
        animation-duration:.01ms!important;
        animation-iteration-count:1!important;
        transition-duration:.01ms!important;
      }
    }
  </style>
</head>
<body>
  <svg class="svg-sprite" aria-hidden="true" focusable="false">
    <symbol id="icon-grip" viewBox="0 0 16 16">
      <g fill="currentColor">
        <circle cx="5.4" cy="4" r="1.15"/><circle cx="10.6" cy="4" r="1.15"/>
        <circle cx="5.4" cy="8" r="1.15"/><circle cx="10.6" cy="8" r="1.15"/>
        <circle cx="5.4" cy="12" r="1.15"/><circle cx="10.6" cy="12" r="1.15"/>
      </g>
    </symbol>
    <symbol id="icon-chevron-up" viewBox="0 0 24 24">
      <path d="m6 15 6-6 6 6"/>
    </symbol>
    <symbol id="icon-chevron-down" viewBox="0 0 24 24">
      <path d="m6 9 6 6 6-6"/>
    </symbol>
    <symbol id="icon-arrow-right" viewBox="0 0 24 24">
      <path d="M4.5 12h15M13 5.5l6.5 6.5-6.5 6.5"/>
    </symbol>
    <symbol id="icon-arrow-left" viewBox="0 0 24 24">
      <path d="M19.5 12h-15M11 5.5 4.5 12l6.5 6.5"/>
    </symbol>
    <symbol id="icon-check" viewBox="0 0 24 24">
      <path d="m4.5 12.5 5 5 10-11"/>
    </symbol>
    <symbol id="icon-restart" viewBox="0 0 24 24">
      <path d="M20 11a8 8 0 1 0-2.3 6.1M20 4v7h-7"/>
    </symbol>
    <symbol id="icon-move" viewBox="0 0 24 24">
      <path d="M12 3v18M8 7l4-4 4 4M8 17l4 4 4-4M3 12h18M7 8l-4 4 4 4M17 8l4 4-4 4"/>
    </symbol>
  </svg>

  <div class="app">
    <header class="site-header">
      <div class="brand" aria-label="DISC — поведенческий тест">
        <svg class="brand-mark" viewBox="0 0 40 40" aria-hidden="true">
          <rect x="1" y="1" width="17.5" height="17.5" rx="6" fill="#c6533e"/>
          <rect x="21.5" y="1" width="17.5" height="17.5" rx="6" fill="#b88326"/>
          <rect x="1" y="21.5" width="17.5" height="17.5" rx="6" fill="#2f7d5f"/>
          <rect x="21.5" y="21.5" width="17.5" height="17.5" rx="6" fill="#356aa4"/>
        </svg>
        <span class="brand-text">DISC <span>поведенческий тест</span></span>
      </div>
      <div class="header-meta">
        <span class="header-meta__dot" aria-hidden="true"></span>
        <span>8 шагов</span>
        <span class="header-meta__sep" aria-hidden="true">·</span>
        <span>24 вопроса</span>
        <span class="header-meta__extra">
          <span class="header-meta__sep" aria-hidden="true">·</span>
          без отправки данных
        </span>
      </div>
    </header>

    <main>
      <section class="screen screen--test" id="screen-test" aria-labelledby="test-title">
        <div class="test-shell">
          <div class="test-head">
            <div class="test-head__top">
              <div class="eyebrow"><span class="eyebrow__dot" aria-hidden="true"></span>поведенческий профиль</div>
              <div class="test-meta">DISC · 24 вопроса</div>
            </div>
            <h1 class="test-title" id="test-title" tabindex="-1">Тест DISC</h1>
            <p class="test-sub">Помните — чем честнее вы с тестом, тем точнее результаты!</p>
            <p class="test-lead">Разместите блоки в порядке от наиболее похожего на вас до наименее похожего.</p>
            <p class="sr-only" id="drag-instructions">В каждом вопросе четыре качества. Перетаскивайте качества мышью за любую часть строки или на сенсорном экране за ручку справа. С клавиатуры используйте Alt и стрелки вверх или вниз, чтобы изменить порядок.</p>
          </div>

          <div class="disc-modal__tabs" role="tablist" aria-label="Шаги теста" id="steps">
@@TABS@@
          </div>

          <div class="step-status">
            <div>Шаг <strong id="step-current">1</strong> из 8</div>
            <div class="step-status__hint">
              <svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><use href="#icon-move"></use></svg>
              <span>перетащите карточку</span>
            </div>
          </div>

          <div class="disc-progress" id="progress-track" role="progressbar" aria-label="Прогресс теста" aria-valuemin="0" aria-valuemax="100" aria-valuenow="12">
            <div class="disc-progress__bar" id="discProgress"></div>
          </div>

          <div class="wizard" id="rootwizard" data-step="0">
@@PANES@@
          </div>

          <div class="disc-actions">
            <button class="disc-btn disc-btn--ghost" type="button" data-disc-prev id="prev-btn" disabled>
              <svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><use href="#icon-arrow-left"></use></svg>
              Назад
            </button>
            <div class="disc-actions__right">
              <button class="disc-btn disc-btn--primary" type="button" data-disc-next id="next-btn">
                Далее
                <svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><use href="#icon-arrow-right"></use></svg>
              </button>
              <button class="disc-btn disc-btn--primary disc-btn--finish" type="button" data-disc-finish id="finish-btn" hidden>
                <svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><use href="#icon-check"></use></svg>
                Завершить тест
              </button>
            </div>
          </div>

          <p class="keyboard-hint">С клавиатуры: <kbd>Alt</kbd> + <kbd>↑</kbd> / <kbd>↓</kbd> — изменить порядок качества.</p>
          <div class="sr-only" id="live-status" aria-live="polite"></div>
        </div>
      </section>

      <section class="screen screen--result" id="screen-result" aria-labelledby="result-title" hidden>
        <div class="result-shell">
          <div class="result-head">
            <div class="eyebrow"><span class="eyebrow__dot" aria-hidden="true"></span>тест завершён</div>
            <h1 class="result-title" id="result-title" tabindex="-1">Ваш DISC-профиль</h1>
            <p class="result-sub">Спасибо за ответы. Вот ваши баллы по четырём типам поведения.</p>
          </div>

          <div class="score-hero">
            <div class="score-hero__label">Итоговый профиль</div>
            <div class="score-string" id="score-string">D:0, I:0, S:0, C:0</div>
          </div>

          <div class="score-grid" aria-label="Баллы по типам DISC">
            <article class="score-card score-card--d">
              <div class="score-card__letter">D</div>
              <div class="score-card__name">Dominance</div>
              <div class="score-card__ru">Доминирование</div>
              <div class="score-card__value" id="score-d">0</div>
              <div class="score-card__value-label">балл</div>
            </article>
            <article class="score-card score-card--i">
              <div class="score-card__letter">I</div>
              <div class="score-card__name">Influence</div>
              <div class="score-card__ru">Влияние</div>
              <div class="score-card__value" id="score-i">0</div>
              <div class="score-card__value-label">балл</div>
            </article>
            <article class="score-card score-card--s">
              <div class="score-card__letter">S</div>
              <div class="score-card__name">Stability</div>
              <div class="score-card__ru">Стабильность</div>
              <div class="score-card__value" id="score-s">0</div>
              <div class="score-card__value-label">балл</div>
            </article>
            <article class="score-card score-card--c">
              <div class="score-card__letter">C</div>
              <div class="score-card__name">Compliance</div>
              <div class="score-card__ru">Соответствие</div>
              <div class="score-card__value" id="score-c">0</div>
              <div class="score-card__value-label">балл</div>
            </article>
          </div>

          <div class="result-note">
            <p>По каждому типу балл равен количеству выборов «Я наиболее» минус количество выборов «Я наименее».</p>
            <p>Все вычисления выполняются локально в браузере. Результат никуда не отправляется.</p>
          </div>

          <div class="result-actions">
            <button class="disc-btn disc-btn--primary" type="button" id="restart-btn">
              <svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><use href="#icon-restart"></use></svg>
              Пройти ещё раз
            </button>
          </div>
        </div>
      </section>
    </main>

    <footer class="site-footer">
      <span>DISC · поведенческий тест</span>
      <span>Работает офлайн · без регистрации и отправки данных</span>
    </footer>
  </div>

  <script>
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
  </script>
</body>
</html>
'''

out = template.replace('@@TABS@@', '\n'.join(tabs)).replace('@@PANES@@', '\n'.join(cards))
(base / 'index.html').write_text(out, encoding='utf-8')
print('wrote index.html', len(out), 'bytes')
