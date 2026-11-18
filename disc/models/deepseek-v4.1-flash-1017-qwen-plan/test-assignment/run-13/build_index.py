import json, html

questions = json.load(open('questions.json', encoding='utf-8'))
STEP_NAMES = ["Первый", "Второй", "Третий", "Четвертый", "Пятый", "Шестой", "Седьмой", "Восьмой"]

def esc(s):
    return html.escape(s, quote=False)

# Cards, three questions per step
question_no = 1
step_panes = []
for step in range(8):
    cards = []
    for q in range(3):
        items = questions[step * 3 + q]
        qn = question_no
        question_no += 1
        opts = []
        for pos, item in enumerate(items):
            opts.append(
                f'''<li class="option disc-item" data-type="{item['type']}" data-pos="{pos}" data-orig="{pos}" tabindex="0" aria-posinset="{pos + 1}" aria-setsize="4">\n'''
                f'''  <span class="option-rank" aria-hidden="true" data-rank="{pos + 1}"></span>\n'''
                f'''  <span class="option-text">{esc(item['text'])}</span>\n'''
                f'''  <span class="option-handle disc-handle" aria-hidden="true"><svg viewBox="0 0 14 20" fill="currentColor" focusable="false"><circle cx="4" cy="4" r="1.5"/><circle cx="10" cy="4" r="1.5"/><circle cx="4" cy="10" r="1.5"/><circle cx="10" cy="10" r="1.5"/><circle cx="4" cy="16" r="1.5"/><circle cx="10" cy="16" r="1.5"/></svg></span>\n'''
                f'''</li>'''
            )
        cards.append(
            f'''<article class="q-card disc-card" aria-labelledby="q-title-{qn}">\n'''
            f'''  <div class="q-head">\n'''
            f'''    <span class="q-index" id="q-title-{qn}">Вопрос {qn:02d}</span>\n'''
            f'''    <span class="q-range disc-card__title"><svg viewBox="0 0 14 14" fill="none" aria-hidden="true" focusable="false"><path d="M7 11.3V2.7M3.3 6.4 7 2.7l3.7 3.7" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>Я наиболее</span>\n'''
            f'''  </div>\n'''
            f'''  <ul class="rank-list disc-list" id="draggable-list{qn}" data-question="{qn}" aria-label="Вопрос {qn}: расположите варианты от наиболее похожего на вас до наименее похожего" aria-describedby="rankHelp">\n'''
            + '\n'.join(opts) +
            f'''\n  </ul>\n'''
            f'''  <div class="q-foot disc-card__foot"><svg viewBox="0 0 14 14" fill="none" aria-hidden="true" focusable="false"><path d="M7 2.7v8.6M3.3 7.6 7 11.3l3.7-3.7" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>Я наименее</div>\n'''
            f'''</article>'''
        )
    panes = f'''<div class="step-pane disc-pane{' is-active' if step == 0 else ''}" id="step-pane-{step}" role="tabpanel" aria-labelledby="step-tab-{step}" data-step-pane="{step}"{' hidden' if step else ''}>\n<div class="questions-grid disc-grid3">\n''' + '\n'.join(cards) + '\n</div>\n</div>'
    step_panes.append(panes)

tabs = []
for i, name in enumerate(STEP_NAMES):
    tabs.append(
        f'''<button class="step-tab disc-tab{' is-active' if i == 0 else ''}" id="step-tab-{i}" type="button" role="tab" aria-selected="{'true' if i == 0 else 'false'}" aria-controls="step-pane-{i}" data-step="{i}" data-step-btn="{i}" tabindex="{'0' if i == 0 else '-1'}"><span class="step-num" aria-hidden="true" data-step-num="{i + 1:02d}"></span><span>{name}</span></button>'''
    )

HTML = r'''<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light">
<meta name="theme-color" content="#eef2ea">
<title>Тест DISC — Школа менеджмента Stratoplan</title>
<meta name="description" content="Пройдите тест DISC: расставьте варианты по порядку и узнайте свои баллы по шкалам D, I, S и C.">
<style>
:root{
  --bg:#eef2ea;
  --bg-soft:#f5f8f2;
  --surface:#fbfcf9;
  --surface-2:#f4f7f1;
  --white:#ffffff;
  --ink:#10241c;
  --ink-soft:#4b5d53;
  --muted:#68766d;
  --line:#dbe4da;
  --line-strong:#c6d3c6;
  --brand:#1f6649;
  --brand-deep:#123e2d;
  --brand-mid:#3f8b68;
  --brand-soft:#e5f1e9;
  --lime:#c7e86b;
  --d:#b4533b;
  --d-soft:#f7e8e3;
  --i:#b98227;
  --i-soft:#faf0dc;
  --s:#2c7d57;
  --s-soft:#e4f2e9;
  --c:#3c5f9e;
  --c-soft:#e8edf7;
  --shadow:0 28px 80px rgba(22, 55, 40, .10), 0 2px 6px rgba(22, 55, 40, .04);
  --font:-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "Noto Sans", sans-serif;
  --mono:ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace;
}
*,*::before,*::after{box-sizing:border-box}
html{scroll-behavior:smooth}
body{
  margin:0;
  min-height:100vh;
  font-family:var(--font);
  color:var(--ink);
  background:
    radial-gradient(1100px 680px at 12% -8%, #fbfdf7 0%, rgba(251,253,247,0) 60%),
    radial-gradient(900px 560px at 100% 2%, #e2ede1 0%, rgba(226,237,225,0) 58%),
    var(--bg);
  -webkit-font-smoothing:antialiased;
  text-rendering:optimizeLegibility;
}
body::before{
  content:"";
  position:fixed;
  inset:0;
  z-index:-1;
  pointer-events:none;
  background-image:
    linear-gradient(rgba(18,62,45,.022) 1px, transparent 1px),
    linear-gradient(90deg, rgba(18,62,45,.022) 1px, transparent 1px);
  background-size:46px 46px;
  mask-image:linear-gradient(to bottom, #000 0%, rgba(0,0,0,.35) 55%, transparent 88%);
  -webkit-mask-image:linear-gradient(to bottom, #000 0%, rgba(0,0,0,.35) 55%, transparent 88%);
}
button{font:inherit}
button, [tabindex]{-webkit-tap-highlight-color:transparent}
[hidden]{display:none !important}
.sr-only{
  position:absolute !important;
  width:1px;height:1px;
  padding:0;margin:-1px;
  overflow:hidden;clip:rect(0,0,0,0);
  white-space:nowrap;border:0;
}
.wrap{width:min(1180px, calc(100% - 40px));margin-inline:auto}

/* header */
.site-header{padding:24px 0 6px}
.header-row{display:flex;align-items:center;justify-content:space-between;gap:20px}
.brand{display:flex;align-items:center;gap:11px;min-width:0}
.brand-mark{width:39px;height:39px;display:block;flex:0 0 auto;filter:drop-shadow(0 5px 10px rgba(18,62,45,.16))}
.brand-name{display:block;font-size:13.5px;line-height:1;letter-spacing:.18em;font-weight:800;color:var(--brand-deep)}
.brand-sub{display:block;margin-top:5px;font-size:9.5px;line-height:1;letter-spacing:.13em;text-transform:uppercase;color:var(--muted);font-weight:650}
.header-pill{
  display:inline-flex;align-items:center;gap:8px;
  padding:8px 12px;border:1px solid rgba(198,211,198,.85);
  border-radius:999px;background:rgba(251,252,249,.62);
  color:var(--ink-soft);font-size:11.5px;line-height:1;font-weight:600;
  backdrop-filter:blur(8px);-webkit-backdrop-filter:blur(8px);white-space:nowrap;
}
.header-pill svg{width:15px;height:15px;color:var(--brand);flex:0 0 auto}

/* main shell */
.page{padding:18px 0 30px}
.app-view{position:relative;background:var(--surface);border:1px solid rgba(198,211,198,.9);border-radius:30px;box-shadow:var(--shadow);overflow:hidden;isolation:isolate}
.app-view::before{content:"";position:absolute;inset:0 0 auto;height:5px;background:linear-gradient(90deg,var(--d) 0 25%,var(--i) 25% 50%,var(--s) 50% 75%,var(--c) 75% 100%);z-index:2}
.test-top{padding:38px 48px 0;text-align:center}
.eyebrow{display:inline-flex;align-items:center;gap:8px;margin:0;font-size:10.5px;line-height:1;font-weight:750;letter-spacing:.16em;text-transform:uppercase;color:var(--brand)}
.eyebrow::before{content:"";width:18px;height:1px;background:var(--brand);opacity:.55}
.eyebrow::after{content:"";width:18px;height:1px;background:var(--brand);opacity:.55}
.title{margin:13px 0 0;font-size:clamp(42px,5.6vw,65px);line-height:.95;letter-spacing:-.055em;font-weight:800;color:var(--brand-deep)}
.disc-word{display:inline-flex;letter-spacing:-.045em;margin-left:.05em}
.disc-word span{display:inline-block}
.disc-word .d{color:var(--d)}
.disc-word .i{color:var(--i)}
.disc-word .s{color:var(--s)}
.disc-word .c{color:var(--c)}
.hero-sub{max-width:620px;margin:16px auto 0;font-size:15.5px;line-height:1.55;color:var(--ink-soft)}
.hero-lead{
  display:inline-block;max-width:720px;margin:17px auto 0;
  padding:10px 15px;border:1px solid #d3e5d7;border-radius:12px;
  background:linear-gradient(180deg,#f0f8f1,#e8f3ea);
  color:#28563e;font-size:14px;line-height:1.45;font-weight:650;
}
.hero-meta{display:flex;justify-content:center;align-items:center;gap:0;flex-wrap:wrap;margin:17px 0 0;color:var(--muted);font-size:12px;font-weight:600}
.hero-meta span{display:inline-flex;align-items:center;gap:6px;padding:0 13px;white-space:nowrap}
.hero-meta span + span{border-left:1px solid var(--line-strong)}
.hero-meta svg{width:14px;height:14px;color:var(--brand-mid);flex:0 0 auto}
.hero-meta b{font-weight:750;color:var(--ink-soft)}

/* stepper */
.stepper{padding:28px 48px 0}
.steps{
  display:flex;gap:4px;overflow-x:auto;overscroll-behavior-inline:contain;
  padding:4px;background:var(--surface-2);border:1px solid var(--line);border-radius:14px;
  scrollbar-width:none;-webkit-overflow-scrolling:touch;scroll-behavior:smooth;
}
.steps::-webkit-scrollbar{display:none}
.step-tab{
  appearance:none;border:0;background:transparent;color:#63736a;
  flex:1 0 auto;display:inline-flex;align-items:center;justify-content:center;gap:7px;
  min-height:38px;padding:8px 11px;border-radius:10px;
  font-size:12.5px;line-height:1.1;font-weight:650;white-space:nowrap;cursor:pointer;
  transition:background .2s ease,color .2s ease,box-shadow .2s ease,transform .2s ease;
}
.step-tab .step-num::before{content:attr(data-step-num)}
.step-tab .step-num{font-size:9.5px;line-height:1;letter-spacing:.08em;font-weight:750;opacity:.5;font-variant-numeric:tabular-nums}
.step-tab:hover{background:rgba(255,255,255,.85);color:var(--brand-deep)}
.step-tab.is-active{background:var(--brand-deep);color:#fff;box-shadow:0 6px 15px rgba(18,62,45,.18)}
.step-tab.is-active .step-num{opacity:1;color:var(--lime)}
.step-tab:focus-visible{outline:2px solid var(--brand);outline-offset:2px}
.step-tab:active{transform:translateY(1px)}

/* progress */
.progress-wrap{padding:18px 48px 0}
.progress-top{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:7px;color:var(--muted);font-size:10.5px;line-height:1;font-weight:700;letter-spacing:.11em;text-transform:uppercase}
.progress-top .now{color:var(--brand-deep);letter-spacing:.06em}
.progress-top .pct{font-variant-numeric:tabular-nums;letter-spacing:.04em}
.progress-track{height:6px;border-radius:999px;background:#e3ebe1;overflow:hidden}
.progress-bar{height:100%;width:12.5%;border-radius:inherit;background:linear-gradient(90deg,var(--brand) 0%,#61a17a 62%,var(--lime) 100%);transition:width .38s cubic-bezier(.2,.8,.2,1)}

/* question panes */
.panes{padding:24px 48px 0}
.step-pane{animation:paneIn .34s cubic-bezier(.2,.8,.2,1) both}
@keyframes paneIn{from{opacity:0;transform:translateY(7px)}to{opacity:1;transform:translateY(0)}}
.questions-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:18px;align-items:start}
.q-card{background:var(--white);border:1px solid var(--line);border-radius:16px;overflow:hidden;transition:border-color .2s ease,box-shadow .2s ease,transform .2s ease}
.q-card:hover{border-color:var(--line-strong);box-shadow:0 12px 32px rgba(24,60,44,.065)}
.q-card:focus-within{border-color:#b8ccba;box-shadow:0 0 0 3px rgba(31,102,73,.08)}
.q-head{display:flex;align-items:center;justify-content:space-between;gap:8px;min-height:44px;padding:11px 14px;border-bottom:1px solid var(--line);background:linear-gradient(180deg,#fafcf8,#f5f9f3)}
.q-index{font-size:9.5px;line-height:1;letter-spacing:.12em;text-transform:uppercase;font-weight:750;color:#6f7e75;white-space:nowrap}
.q-range{display:inline-flex;align-items:center;gap:5px;font-size:11px;line-height:1;font-weight:750;letter-spacing:.01em;color:var(--brand);white-space:nowrap}
.q-range svg{width:12px;height:12px;flex:0 0 auto}
.q-foot{display:flex;align-items:center;gap:5px;padding:10px 14px;border-top:1px solid var(--line);background:#fbfcfa;color:#718077;font-size:10.5px;line-height:1;font-weight:650}
.q-foot svg{width:12px;height:12px;flex:0 0 auto}
.rank-list{list-style:none;margin:0;padding:0;position:relative}
.option{
  position:relative;display:flex;align-items:center;gap:10px;
  min-height:56px;padding:11px 13px;background:#fff;
  border-top:1px solid var(--line);
  color:#2d3d35;font-size:14.5px;line-height:1.3;font-weight:500;
  cursor:grab;user-select:none;-webkit-user-select:none;-webkit-touch-callout:none;-webkit-user-drag:none;
  transition:background .18s ease,color .18s ease;
}
.option:first-child{border-top:0}
.option:hover{background:#f8faf6}
.option:focus-visible{outline:2px solid var(--brand);outline-offset:-3px;z-index:1}
.option-rank::before{content:attr(data-rank)}
.option-rank{
  width:24px;height:24px;flex:0 0 24px;display:grid;place-items:center;
  border:1px solid var(--line-strong);border-radius:50%;background:#fff;
  color:#6f7e75;font-size:9.5px;line-height:1;font-weight:750;font-variant-numeric:tabular-nums;
  transition:background .18s ease,color .18s ease,border-color .18s ease;
}
.option-text{flex:1 1 auto;min-width:0}
.option-handle{width:17px;height:26px;flex:0 0 17px;display:grid;place-items:center;color:#8e9c93;cursor:grab;touch-action:none}
.option:hover .option-handle{color:#627468}
.option-handle svg{display:block;width:12px;height:18px}
.option[data-pos="0"]{background:linear-gradient(90deg,rgba(199,232,107,.17),rgba(255,255,255,0) 72%)}
.option[data-pos="0"]:hover{background:linear-gradient(90deg,rgba(199,232,107,.24),#f8faf6 72%)}
.option[data-pos="0"] .option-rank{background:var(--brand);border-color:var(--brand);color:#fff}
.option[data-pos="3"]{background:#fbfcfa;color:#67756c}
.option[data-pos="3"]:hover{background:#f6f8f4}
.option[data-pos="3"] .option-rank{background:#f1f4ef;color:#98a49c}
.option.is-dragging{opacity:.24;background:var(--brand-soft)}
.rank-list.is-sorting{cursor:grabbing}
.rank-list.is-sorting .option{cursor:grabbing}
.option.drag-ghost{
  position:fixed;z-index:9999;margin:0;pointer-events:none;
  background:#fff;border:1px solid #9dbba6;border-radius:13px;
  box-shadow:0 20px 48px rgba(17,52,36,.22),0 4px 12px rgba(17,52,36,.10);
  transform-origin:center;will-change:transform;opacity:.99;
}
.option.drag-ghost .option-handle{color:var(--brand)}
.touch-word{display:none}
@media (pointer: coarse){.touch-word{display:inline}.mouse-word{display:none}}
body.is-drag-active{cursor:grabbing;user-select:none}
body.is-drag-active *{cursor:grabbing !important}
.drag-hint{display:flex;align-items:center;justify-content:center;gap:7px;margin:16px 0 0;color:#6f7e75;font-size:11.5px;line-height:1.4;text-align:center}
.drag-hint svg{width:14px;height:14px;flex:0 0 auto;color:var(--brand-mid)}

/* actions */
.actions{display:flex;align-items:center;gap:12px;padding:20px 48px 34px}
.btn{
  appearance:none;display:inline-flex;align-items:center;justify-content:center;gap:8px;
  min-height:46px;padding:12px 20px;border-radius:999px;border:1px solid transparent;
  font-size:13.5px;line-height:1;font-weight:700;letter-spacing:.005em;white-space:nowrap;cursor:pointer;
  transition:background .2s ease,border-color .2s ease,color .2s ease,box-shadow .2s ease,transform .2s ease,opacity .2s ease;
}
.btn svg{width:15px;height:15px;flex:0 0 auto}
.btn:focus-visible{outline:2px solid var(--brand);outline-offset:3px}
.btn:active{transform:translateY(1px)}
.btn-ghost{background:#fff;border-color:var(--line-strong);color:var(--ink-soft)}
.btn-ghost:hover:not(:disabled){background:#f5f8f2;border-color:#b4c6b6;color:var(--brand-deep)}
.btn-ghost:disabled{opacity:.42;cursor:not-allowed}
.btn-primary{background:var(--brand-deep);border-color:var(--brand-deep);color:#fff;box-shadow:0 8px 20px rgba(18,62,45,.17)}
.btn-primary:hover{background:#1a533c;border-color:#1a533c;box-shadow:0 10px 24px rgba(18,62,45,.22)}
.btn-primary svg{color:var(--lime)}
.btn-restart{background:var(--brand-deep);border-color:var(--brand-deep);color:#fff}
.btn-restart:hover{background:#1a533c;border-color:#1a533c}
.btn-restart svg{color:var(--lime)}
.action-hint{max-width:320px;margin:0 auto;color:#6f7e75;font-size:11.5px;line-height:1.45;text-align:center}
.action-hint b{font-weight:700;color:#68786e}

/* result */
.result-inner{padding:50px 48px 44px;text-align:center}
.result-top{max-width:840px;margin:0 auto}
.result-badge{
  width:62px;height:62px;margin:0 auto 18px;display:grid;place-items:center;
  border-radius:50%;background:var(--brand-soft);border:1px solid #cfe4d5;
  color:var(--brand);box-shadow:inset 0 0 0 7px rgba(255,255,255,.55);
}
.result-badge svg{width:27px;height:27px}
.result-title{margin:0;font-size:clamp(32px,4.2vw,48px);line-height:1.02;letter-spacing:-.045em;color:var(--brand-deep);font-weight:800}
.result-sub{margin:13px auto 0;max-width:590px;color:var(--ink-soft);font-size:14.5px;line-height:1.55}
.score-line{
  display:inline-block;margin:24px auto 0;padding:12px 20px;
  border-radius:12px;background:var(--brand-deep);color:#fff;
  font-family:var(--mono);font-size:14px;line-height:1;font-weight:600;letter-spacing:.01em;
  box-shadow:0 10px 26px rgba(18,62,45,.16);
}
.score-line .score-label{color:#a9c7b1;font-weight:500}
.dim-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;max-width:880px;margin:22px auto 0;text-align:left}
.dim-card{position:relative;overflow:hidden;padding:16px 15px 14px;background:#fff;border:1px solid var(--line);border-radius:15px}
.dim-card::before{content:"";position:absolute;inset:0 auto 0 0;width:3px;background:var(--accent)}
.dim-top{display:flex;align-items:center;gap:9px;min-width:0}
.dim-letter{width:31px;height:31px;flex:0 0 31px;display:grid;place-items:center;border-radius:9px;background:var(--soft);color:var(--accent);font-size:15px;line-height:1;font-weight:800}
.dim-name{font-size:11.5px;line-height:1.2;font-weight:650;color:#65736b;min-width:0}
.dim-value{margin:14px 0 0;font-size:34px;line-height:.9;letter-spacing:-.05em;font-weight:800;color:var(--ink);font-variant-numeric:tabular-nums}
.dim-scale{position:relative;height:5px;margin-top:14px;background:#edf1eb;border-radius:999px}
.dim-scale::before{content:"";position:absolute;left:50%;top:-2px;bottom:-2px;width:1px;background:#c8d4c8}
.dim-marker{position:absolute;top:50%;left:50%;width:11px;height:11px;border-radius:50%;background:var(--accent);border:2px solid #fff;box-shadow:0 1px 4px rgba(0,0,0,.18);transform:translate(-50%,-50%);transition:left .5s cubic-bezier(.2,.8,.2,1)}
.dim-card.d-d{--accent:var(--d);--soft:var(--d-soft)}
.dim-card.d-i{--accent:var(--i);--soft:var(--i-soft)}
.dim-card.d-i .dim-letter{color:#95651b}
.dim-card.d-s{--accent:var(--s);--soft:var(--s-soft)}
.dim-card.d-c{--accent:var(--c);--soft:var(--c-soft)}
.result-note{max-width:730px;margin:24px auto 0;padding:14px 17px;border:1px solid var(--line);border-radius:13px;background:var(--surface-2);color:#637269;font-size:12px;line-height:1.58;text-align:left}
.result-note b{color:#506258;font-weight:700}
.result-actions{display:flex;justify-content:center;flex-wrap:wrap;gap:10px;margin-top:24px}
.result-footnote{margin:18px auto 0;color:#6f7e75;font-size:11px;line-height:1.5}

@keyframes resultIn{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:translateY(0)}}
.result-view .result-inner{animation:resultIn .42s cubic-bezier(.2,.8,.2,1) both}

/* footer */
.site-footer{padding:0 0 34px;color:#6c7b72;font-size:11.5px;line-height:1.5}
.footer-row{display:flex;align-items:center;justify-content:space-between;gap:16px;flex-wrap:wrap;padding-top:17px;border-top:1px solid rgba(198,211,198,.8)}
.footer-row p{margin:0}
.footer-row .footer-note{display:inline-flex;align-items:center;gap:6px}
.footer-row svg{width:13px;height:13px;color:var(--brand-mid)}

/* responsive */
@media (max-width: 1000px){
  .questions-grid{grid-template-columns:1fr;gap:14px}
  .q-card{max-width:760px;width:100%;margin-inline:auto}
  .option{min-height:54px}
}
@media (max-width: 760px){
  .wrap{width:calc(100% - 24px)}
  .site-header{padding-top:16px}
  .header-pill{font-size:10.5px;padding:7px 10px}
  .header-pill .pill-long{display:none}
  .page{padding-top:12px}
  .app-view{border-radius:22px}
  .test-top{padding:30px 20px 0}
  .title{font-size:clamp(39px,11vw,54px)}
  .hero-sub{font-size:14px;margin-top:13px}
  .hero-lead{font-size:12.5px;margin-top:14px;padding:9px 12px}
  .hero-meta{margin-top:14px;font-size:10.5px}
  .hero-meta span{padding:0 9px}
  .hero-meta b{font-weight:700}
  .stepper{padding:22px 16px 0}
  .steps{border-radius:12px}
  .step-tab{flex:0 0 auto;min-width:66px;font-size:11.5px;padding:8px 10px}
  .progress-wrap{padding:15px 20px 0}
  .panes{padding:18px 16px 0}
  .q-card{border-radius:14px}
  .q-head{padding:10px 12px}
  .option{padding:11px 12px;font-size:14px}
  .drag-hint{margin-top:14px;font-size:10.5px;padding:0 10px}
  .actions{padding:16px 16px 24px;gap:9px;flex-wrap:wrap}
  .action-hint{display:none}
  .btn{min-height:45px;font-size:12.5px;padding:11px 15px}
  .actions .btn-primary,.actions .btn-restart{margin-left:auto}
  .result-inner{padding:36px 18px 30px}
  .result-badge{width:54px;height:54px;margin-bottom:15px}
  .result-badge svg{width:24px;height:24px}
  .result-sub{font-size:13px}
  .score-line{font-size:12px;padding:11px 15px;margin-top:20px}
  .dim-grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:9px;margin-top:18px}
  .dim-card{padding:13px 12px 12px}
  .dim-value{font-size:29px;margin-top:12px}
  .dim-scale{margin-top:12px}
  .result-note{font-size:11px;padding:12px 13px;margin-top:20px}
  .result-actions{margin-top:20px}
  .site-footer{padding-bottom:24px;font-size:10.5px}
  .footer-row{padding-top:14px}
}
@media (max-width: 460px){
  .brand-name{font-size:12px;letter-spacing:.15em}
  .brand-sub{font-size:8.5px}
  .brand-mark{width:34px;height:34px}
  .header-pill{padding:7px 9px}
  .title{font-size:clamp(36px,12vw,46px)}
  .hero-meta span{padding:0 7px}
  .hero-meta span:nth-child(2){border-left:0}
  .option{font-size:13.5px;gap:8px}
  .option-rank{width:22px;height:22px;flex-basis:22px}
  .option-handle{width:15px;flex-basis:15px}
  .actions .btn{flex:1 1 auto}
  .dim-value{font-size:27px}
}
@media (pointer: coarse){
  .option{cursor:default}
  .option-handle{cursor:grab;padding:5px 0;height:36px;width:26px;flex-basis:26px;touch-action:none;color:#77877d}
  .option-handle svg{width:13px;height:19px}
  .drag-hint .mouse-word{display:none}
}
@media (prefers-reduced-motion: reduce){
  html{scroll-behavior:auto}
  *,*::before,*::after{animation-duration:.001ms !important;animation-iteration-count:1 !important;transition-duration:.001ms !important}
}
</style>
</head>
<body>
<header class="site-header">
  <div class="wrap header-row">
    <div class="brand" aria-label="Stratoplan. Школа менеджмента">
      <svg class="brand-mark" viewBox="0 0 44 44" aria-hidden="true" focusable="false">
        <circle cx="22" cy="22" r="21" fill="#123e2d"/>
        <path d="M22 2.5A19.5 19.5 0 0 1 41.5 22H22Z" fill="#b4533b"/>
        <path d="M41.5 22A19.5 19.5 0 0 1 22 41.5V22Z" fill="#b98227"/>
        <path d="M22 41.5A19.5 19.5 0 0 1 2.5 22H22Z" fill="#2c7d57"/>
        <path d="M2.5 22A19.5 19.5 0 0 1 22 2.5V22Z" fill="#3c5f9e"/>
        <circle cx="22" cy="22" r="6" fill="#fbfcf9"/>
        <circle cx="22" cy="22" r="2.4" fill="#123e2d"/>
      </svg>
      <span class="brand-copy">
        <span class="brand-name">STRATOPLAN</span>
        <span class="brand-sub">Школа менеджмента</span>
      </span>
    </div>
    <div class="header-pill" title="Все вычисления выполняются локально в вашем браузере">
      <svg viewBox="0 0 18 18" fill="none" aria-hidden="true" focusable="false"><path d="M9 1.7 15 3.9v4.7c0 3.5-2.5 6.2-6 7.7-3.5-1.5-6-4.2-6-7.7V3.9L9 1.7Z" stroke="currentColor" stroke-width="1.35" stroke-linejoin="round"/><path d="m6.2 8.8 1.9 1.9 3.7-4" stroke="currentColor" stroke-width="1.35" stroke-linecap="round" stroke-linejoin="round"/></svg>
      <span>Офлайн<span class="pill-long"> · без отправки данных</span></span>
    </div>
  </div>
</header>

<main class="page">
  <div class="wrap">
    <p id="rankHelp" class="sr-only">Чтобы изменить порядок, перетащите вариант, а с клавиатуры используйте стрелки вверх и вниз. Первый вариант — наиболее похожий на вас, последний — наименее похожий.</p>
    <p id="liveStatus" class="sr-only" role="status" aria-live="polite"></p>

    <section class="app-view test-view disc-modal disc-modal__dialog is-open" id="wizardmodal" aria-labelledby="pageTitle">
      <div class="test-top disc-modal__head">
        <p class="eyebrow">Поведенческий профиль</p>
        <h1 class="title disc-modal__title" id="pageTitle" tabindex="-1">Тест <span class="disc-word"><span class="d">D</span><span class="i">I</span><span class="s">S</span><span class="c">C</span></span></h1>
        <p class="hero-sub disc-modal__sub">Помните — чем честнее вы с тестом, тем точнее результаты!</p>
        <p class="hero-lead disc-modal__lead">Разместите блоки в порядке от наиболее похожего на вас до наименее похожего</p>
        <div class="hero-meta" role="group" aria-label="Параметры теста">
          <span><svg viewBox="0 0 16 16" fill="none" aria-hidden="true" focusable="false"><rect x="2.2" y="2.2" width="11.6" height="11.6" rx="2.2" stroke="currentColor" stroke-width="1.3"/><path d="M5 6h6M5 8.5h6M5 11h3.8" stroke="currentColor" stroke-width="1.25" stroke-linecap="round"/></svg><b>24</b> вопроса</span>
          <span><svg viewBox="0 0 16 16" fill="none" aria-hidden="true" focusable="false"><circle cx="8" cy="8" r="5.7" stroke="currentColor" stroke-width="1.3"/><path d="M8 4.5V8l2.2 1.4" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"/></svg><b>≈5</b> минут</span>
          <span><svg viewBox="0 0 16 16" fill="none" aria-hidden="true" focusable="false"><path d="M3 3.2h10M3 8h10M3 12.8h6.4" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/></svg><b>8</b> шагов</span>
        </div>
      </div>

      <div class="stepper">
        <div class="steps disc-modal__tabs" id="stepsScroller" role="tablist" aria-label="Шаги теста">
__TABS__
        </div>
      </div>

      <div class="progress-wrap">
        <div class="progress-top">
          <span class="now" id="stepCounter">Шаг 1 из 8</span>
          <span class="pct" id="progressPercent">12%</span>
        </div>
        <div class="progress-track disc-progress" id="progressTrack" role="progressbar" aria-label="Прогресс теста" aria-valuemin="0" aria-valuemax="8" aria-valuenow="1" aria-valuetext="Шаг 1 из 8">
          <div class="progress-bar disc-progress__bar" id="discProgress"></div>
        </div>
      </div>

      <div class="panes disc-modal__body" id="rootwizard">
__PANES__
      </div>

      <p class="drag-hint">
        <svg viewBox="0 0 16 16" fill="none" aria-hidden="true" focusable="false"><path d="M5 3.3v9.4M3.1 4.9 5 3l1.9 1.9M11 12.7V3.3M9.1 11.1 11 13l1.9-1.9" stroke="currentColor" stroke-width="1.25" stroke-linecap="round" stroke-linejoin="round"/></svg>
        <span><span class="mouse-word">Перетаскивайте варианты, чтобы изменить порядок</span><span class="touch-word">Перетаскивайте варианты за ручку, чтобы изменить порядок</span> · с клавиатуры — <b>↑</b> <b>↓</b></span>
      </p>

      <div class="actions disc-actions">
        <button class="btn btn-ghost disc-btn disc-btn--ghost" id="prevBtn" type="button" data-disc-prev disabled>
          <svg viewBox="0 0 16 16" fill="none" aria-hidden="true" focusable="false"><path d="M13 8H3M7.2 3.8 3 8l4.2 4.2" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
          Назад
        </button>
        <p class="action-hint">Сначала поставьте сверху <b>наиболее</b> похожий на вас вариант, снизу — <b>наименее</b> похожий.</p>
        <button class="btn btn-primary disc-btn disc-btn--primary" id="nextBtn" type="button" data-disc-next>
          Далее
          <svg viewBox="0 0 16 16" fill="none" aria-hidden="true" focusable="false"><path d="M3 8h10M8.8 3.8 13 8l-4.2 4.2" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
        </button>
        <button class="btn btn-primary disc-btn disc-btn--primary" id="finishBtn" type="button" data-disc-finish hidden>
          Завершить тест
          <svg viewBox="0 0 16 16" fill="none" aria-hidden="true" focusable="false"><path d="m3 8.4 3.1 3.1L13 4.6" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>
        </button>
      </div>
    </section>

    <section class="app-view result-view result" id="result" aria-labelledby="resultTitle" hidden>
      <div class="result-inner">
        <div class="result-top">
          <div class="result-badge" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none" focusable="false"><path d="m5 12.5 4.4 4.4L19 7.3" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
          </div>
          <h2 class="result-title result__score-title" id="resultTitle" tabindex="-1">Ваш DISC-профиль</h2>
          <p class="result-sub">Тест завершён. Ниже — ваши баллы по каждой шкале.</p>
          <div class="score-line result__score" id="scoreLine"><span id="scoreLineText">D:0, I:0, S:0, C:0</span></div>
          <div class="dim-grid" role="group" aria-label="Баллы по шкалам">
            <article class="dim-card d-d">
              <div class="dim-top"><span class="dim-letter" aria-hidden="true">D</span><span class="dim-name">Доминирование</span></div>
              <div class="dim-value" id="scoreD">0</div>
              <div class="dim-scale" aria-hidden="true"><span class="dim-marker" id="markerD"></span></div>
            </article>
            <article class="dim-card d-i">
              <div class="dim-top"><span class="dim-letter" aria-hidden="true">I</span><span class="dim-name">Влияние</span></div>
              <div class="dim-value" id="scoreI">0</div>
              <div class="dim-scale" aria-hidden="true"><span class="dim-marker" id="markerI"></span></div>
            </article>
            <article class="dim-card d-s">
              <div class="dim-top"><span class="dim-letter" aria-hidden="true">S</span><span class="dim-name">Стабильность</span></div>
              <div class="dim-value" id="scoreS">0</div>
              <div class="dim-scale" aria-hidden="true"><span class="dim-marker" id="markerS"></span></div>
            </article>
            <article class="dim-card d-c">
              <div class="dim-top"><span class="dim-letter" aria-hidden="true">C</span><span class="dim-name">Соответствие</span></div>
              <div class="dim-value" id="scoreC">0</div>
              <div class="dim-scale" aria-hidden="true"><span class="dim-marker" id="markerC"></span></div>
            </article>
          </div>
          <p class="result-note"><b>Как считаются баллы:</b> по каждой шкале из числа вариантов, выбранных вами как «наиболее», вычитается число вариантов, выбранных как «наименее». Поэтому баллы могут быть отрицательными.</p>
          <div class="result-actions">
            <button class="btn btn-restart disc-btn" id="restartBtn" type="button" data-disc-restart>
              <svg viewBox="0 0 16 16" fill="none" aria-hidden="true" focusable="false"><path d="M13.2 7.1A5.4 5.4 0 1 1 11.6 3M11.6 3v3.8H7.8" stroke="currentColor" stroke-width="1.45" stroke-linecap="round" stroke-linejoin="round"/></svg>
              Пройти ещё раз
            </button>
          </div>
          <p class="result-footnote">Все вычисления выполнены локально в вашем браузере. Результат никуда не отправляется.</p>
        </div>
      </div>
    </section>
  </div>
</main>

<footer class="site-footer">
  <div class="wrap footer-row">
    <p>Тест DISC · Школа менеджмента Stratoplan</p>
    <p class="footer-note">
      <svg viewBox="0 0 16 16" fill="none" aria-hidden="true" focusable="false"><path d="M8 1.6 13.4 3.7v4.1c0 3.1-2.2 5.5-5.4 6.8-3.2-1.3-5.4-3.7-5.4-6.8V3.7L8 1.6Z" stroke="currentColor" stroke-width="1.2" stroke-linejoin="round"/></svg>
      Работает офлайн, без бэкенда и отправки данных
    </p>
  </div>
</footer>

<script>
(() => {
  "use strict";

  const doc = document;
  const $ = (sel, root = doc) => root.querySelector(sel);
  const $$ = (sel, root = doc) => Array.from(root.querySelectorAll(sel));
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  const motion = () => (reduceMotion.matches ? "auto" : "smooth");

  const testView = $("#wizardmodal");
  const resultView = $("#result");
  const tabs = $$(".step-tab", $("#stepsScroller"));
  const tabList = $("#stepsScroller");
  const panes = $$(".step-pane", $("#rootwizard"));
  const prevBtn = $("#prevBtn");
  const nextBtn = $("#nextBtn");
  const finishBtn = $("#finishBtn");
  const restartBtn = $("#restartBtn");
  const progressBar = $("#discProgress");
  const progressTrack = $("#progressTrack");
  const progressPercent = $("#progressPercent");
  const stepCounter = $("#stepCounter");
  const liveStatus = $("#liveStatus");
  const scoreLine = $("#scoreLine");
  const scoreLineText = $("#scoreLineText");
  const resultTitle = $("#resultTitle");
  const testTitle = $("#pageTitle");
  const TOTAL_STEPS = 8;
  const TOTAL_QUESTIONS = 24;
  let step = 0;

  const scoreIds = { d: "#scoreD", i: "#scoreI", s: "#scoreS", c: "#scoreC" };
  const markerIds = { d: "#markerD", i: "#markerI", s: "#markerS", c: "#markerC" };

  function announce(message) {
    if (!liveStatus) return;
    liveStatus.textContent = "";
    window.setTimeout(() => { liveStatus.textContent = message; }, 30);
  }

  function updateList(list) {
    const items = Array.from(list.children).filter((el) => el.classList.contains("option"));
    items.forEach((item, index) => {
      item.dataset.pos = String(index);
      item.setAttribute("aria-posinset", String(index + 1));
      item.setAttribute("aria-setsize", String(items.length));
      const rank = item.querySelector(".option-rank");
      if (rank) rank.dataset.rank = String(index + 1);
    });
  }

  function updateAllLists() {
    $$(".rank-list").forEach(updateList);
  }

  function centerActiveTab() {
    if (!tabList) return;
    const active = tabs[step];
    if (!active) return;
    const navRect = tabList.getBoundingClientRect();
    const tabRect = active.getBoundingClientRect();
    if (tabRect.left >= navRect.left && tabRect.right <= navRect.right) return;
    const target = tabList.scrollLeft + (tabRect.left - navRect.left) - (tabList.clientWidth - tabRect.width) / 2;
    tabList.scrollTo({ left: Math.max(0, target), behavior: motion() });
  }

  function scrollTestIntoView() {
    const anchor = $(".stepper") || testView;
    const top = anchor.getBoundingClientRect().top + window.scrollY - 10;
    if (window.scrollY > top + 24) {
      window.scrollTo({ top: Math.max(0, top), behavior: motion() });
    }
    centerActiveTab();
  }

  function setStep(next, options = {}) {
    const target = Math.max(0, Math.min(TOTAL_STEPS - 1, Number(next) || 0));
    step = target;

    tabs.forEach((tab, index) => {
      const active = index === step;
      tab.classList.toggle("is-active", active);
      tab.setAttribute("aria-selected", active ? "true" : "false");
      tab.tabIndex = active ? 0 : -1;
    });
    panes.forEach((pane, index) => {
      const active = index === step;
      pane.hidden = !active;
      pane.classList.toggle("is-active", active);
    });

    prevBtn.disabled = step === 0;
    nextBtn.hidden = step === TOTAL_STEPS - 1;
    finishBtn.hidden = step !== TOTAL_STEPS - 1;

    const human = step + 1;
    const percent = Math.round((human / TOTAL_STEPS) * 100);
    stepCounter.textContent = "Шаг " + human + " из " + TOTAL_STEPS;
    progressPercent.textContent = percent + "%";
    progressBar.style.width = ((human / TOTAL_STEPS) * 100) + "%";
    progressTrack.setAttribute("aria-valuenow", String(human));
    progressTrack.setAttribute("aria-valuetext", "Шаг " + human + " из " + TOTAL_STEPS);

    if (options.scroll) {
      window.requestAnimationFrame(scrollTestIntoView);
    } else {
      centerActiveTab();
    }
  }

  tabs.forEach((tab, index) => {
    tab.addEventListener("click", () => setStep(index, { scroll: true }));
    tab.addEventListener("keydown", (event) => {
      let target = null;
      if (event.key === "ArrowRight") target = (index + 1) % tabs.length;
      else if (event.key === "ArrowLeft") target = (index - 1 + tabs.length) % tabs.length;
      else if (event.key === "Home") target = 0;
      else if (event.key === "End") target = tabs.length - 1;
      if (target === null) return;
      event.preventDefault();
      setStep(target);
      window.requestAnimationFrame(() => tabs[target].focus({ preventScroll: true }));
    });
  });

  prevBtn.addEventListener("click", () => setStep(step - 1, { scroll: true }));
  nextBtn.addEventListener("click", () => setStep(step + 1, { scroll: true }));

  function calculateScores() {
    const scores = { d: 0, i: 0, s: 0, c: 0 };
    $$(".rank-list").forEach((list) => {
      const items = Array.from(list.children).filter((el) => el.classList.contains("option"));
      if (items.length !== 4) return;
      const most = items[0].dataset.type;
      const least = items[items.length - 1].dataset.type;
      if (Object.prototype.hasOwnProperty.call(scores, most)) scores[most] += 1;
      if (Object.prototype.hasOwnProperty.call(scores, least)) scores[least] -= 1;
    });
    return scores;
  }

  function renderScores(scores) {
    const scoreText = "D:" + scores.d + ", I:" + scores.i + ", S:" + scores.s + ", C:" + scores.c;
    if (scoreLineText) scoreLineText.textContent = scoreText;
    else scoreLine.textContent = scoreText;
    Object.keys(scoreIds).forEach((key) => {
      const valueEl = $(scoreIds[key]);
      if (valueEl) valueEl.textContent = String(scores[key]);
      const marker = $(markerIds[key]);
      if (marker) {
        const pct = ((scores[key] + 6) / 12) * 100;
        marker.style.left = Math.max(0, Math.min(100, pct)) + "%";
      }
    });
  }

  function finishTest() {
    if (dragState && dragState.active) endDrag({ pointerId: dragState.pointerId });
    const scores = calculateScores();
    renderScores(scores);
    testView.hidden = true;
    testView.classList.remove("is-open");
    resultView.hidden = false;
    announce("Тест завершён. Ваши баллы: D" + scores.d + ", I" + scores.i + ", S" + scores.s + ", C" + scores.c + ".");
    window.requestAnimationFrame(() => {
      const top = resultView.getBoundingClientRect().top + window.scrollY - 14;
      window.scrollTo({ top: Math.max(0, top), behavior: motion() });
      resultTitle.focus({ preventScroll: true });
    });
  }

  function restartTest() {
    if (dragState && dragState.active) endDrag({ pointerId: dragState.pointerId });
    $$(".rank-list").forEach((list) => {
      const items = Array.from(list.children).filter((el) => el.classList.contains("option"));
      items.sort((a, b) => Number(a.dataset.orig) - Number(b.dataset.orig));
      items.forEach((item) => list.appendChild(item));
      updateList(list);
    });
    resultView.hidden = true;
    testView.hidden = false;
    testView.classList.add("is-open");
    setStep(0);
    announce("Тест начат заново. Все варианты возвращены в исходный порядок.");
    window.requestAnimationFrame(() => {
      const top = testView.getBoundingClientRect().top + window.scrollY - 14;
      window.scrollTo({ top: Math.max(0, top), behavior: motion() });
      testTitle.focus({ preventScroll: true });
    });
  }

  finishBtn.addEventListener("click", finishTest);
  restartBtn.addEventListener("click", restartTest);

  /* ---------- reorder: pointer, touch and keyboard ---------- */
  const DRAG_THRESHOLD = 7;
  let dragState = null;

  function optionRow(target) {
    return target instanceof Element ? target.closest(".option") : null;
  }

  function optionText(row) {
    const text = row && row.querySelector(".option-text");
    return text ? text.textContent.trim() : "";
  }

  function onPointerDown(event) {
    if (dragState && dragState.active) return;
    const row = optionRow(event.target);
    if (!row || !row.closest(".rank-list")) return;
    if (event.pointerType === "mouse" && event.button !== 0) return;
    // On touch and pen, only the handle starts dragging, so the page can still scroll.
    if (event.pointerType !== "mouse" && !event.target.closest(".option-handle")) return;
    const list = row.parentElement;
    if (!list || !list.classList.contains("rank-list")) return;
    const rect = row.getBoundingClientRect();
    dragState = {
      row,
      list,
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      rect,
      active: false,
      ghost: null
    };
  }

  function startDrag(event) {
    const state = dragState;
    if (!state) return;
    state.active = true;
    state.row.classList.add("is-dragging");
    state.row.setAttribute("aria-grabbed", "true");
    state.list.classList.add("is-sorting");
    document.body.classList.add("is-drag-active");

    const ghost = doc.createElement("div");
    ghost.className = "option disc-item drag-ghost";
    ghost.innerHTML = state.row.innerHTML;
    ghost.style.left = state.rect.left + "px";
    ghost.style.top = state.rect.top + "px";
    ghost.style.width = state.rect.width + "px";
    ghost.style.height = state.rect.height + "px";
    ghost.setAttribute("aria-hidden", "true");
    doc.body.appendChild(ghost);
    state.ghost = ghost;

    try { state.row.setPointerCapture(event.pointerId); } catch (_) {}
  }

  function onPointerMove(event) {
    if (!dragState || event.pointerId !== dragState.pointerId) return;
    const state = dragState;
    if (!state.active) {
      const distance = Math.hypot(event.clientX - state.startX, event.clientY - state.startY);
      if (distance < DRAG_THRESHOLD) return;
      startDrag(event);
    }
    if (!state.active) return;
    event.preventDefault();

    const dx = event.clientX - state.startX;
    const dy = event.clientY - state.startY;
    const tilt = Math.max(-1.4, Math.min(1.4, dx / 130));
    state.ghost.style.transform = "translate3d(" + dx + "px," + dy + "px,0) rotate(" + tilt + "deg) scale(1.015)";

    const listRect = state.list.getBoundingClientRect();
    const insideX = event.clientX >= listRect.left - 32 && event.clientX <= listRect.right + 32;
    if (!insideX) return;

    const items = Array.from(state.list.children).filter((el) => el !== state.row && el.classList.contains("option"));
    let before = null;
    for (const item of items) {
      const rect = item.getBoundingClientRect();
      if (event.clientY < rect.top + rect.height / 2) {
        before = item;
        break;
      }
    }
    if (before) {
      if (state.row.nextElementSibling !== before) {
        state.list.insertBefore(state.row, before);
        updateList(state.list);
      }
    } else if (state.list.lastElementChild !== state.row) {
      state.list.appendChild(state.row);
      updateList(state.list);
    }
  }

  function endDrag(event) {
    if (!dragState) return;
    if (event && typeof event.pointerId === "number" && event.pointerId !== dragState.pointerId) return;
    const state = dragState;
    dragState = null;
    if (!state.active) return;

    if (state.ghost) state.ghost.remove();
    state.row.classList.remove("is-dragging");
    state.row.removeAttribute("aria-grabbed");
    state.list.classList.remove("is-sorting");
    doc.body.classList.remove("is-drag-active");
    try { state.row.releasePointerCapture(state.pointerId); } catch (_) {}
    updateList(state.list);

    const position = Array.from(state.list.children).indexOf(state.row) + 1;
    announce("«" + optionText(state.row) + "» теперь на позиции " + position + " из 4.");
    state.row.focus({ preventScroll: true });
  }

  doc.addEventListener("pointerdown", onPointerDown);
  doc.addEventListener("pointermove", onPointerMove, { passive: false });
  doc.addEventListener("pointerup", endDrag);
  doc.addEventListener("pointercancel", endDrag);
  window.addEventListener("blur", () => {
    if (dragState && dragState.active) endDrag({ pointerId: dragState.pointerId });
  });

  doc.addEventListener("click", (event) => {
    const row = optionRow(event.target);
    if (row) row.focus({ preventScroll: true });
  });

  doc.addEventListener("keydown", (event) => {
    const row = optionRow(event.target);
    if (!row) return;
    const list = row.parentElement;
    if (!list || !list.classList.contains("rank-list")) return;

    let sibling = null;
    let direction = 0;
    if (event.key === "ArrowUp") {
      sibling = row.previousElementSibling;
      direction = -1;
    } else if (event.key === "ArrowDown") {
      sibling = row.nextElementSibling;
      direction = 1;
    } else {
      return;
    }
    event.preventDefault();
    if (!sibling || !sibling.classList.contains("option")) {
      announce("Вариант уже " + (direction < 0 ? "первый" : "последний") + " в списке.");
      return;
    }
    if (direction < 0) list.insertBefore(row, sibling);
    else list.insertBefore(sibling, row);
    updateList(list);
    row.focus({ preventScroll: true });
    const position = Array.from(list.children).indexOf(row) + 1;
    announce("«" + optionText(row) + "» теперь на позиции " + position + " из 4.");
  });

  /* ---------- init ---------- */
  updateAllLists();
  setStep(0);

  // Guard against accidental form submits if the file is embedded in a wrapper.
  doc.addEventListener("submit", (event) => event.preventDefault());
})();
</script>
</body>
</html>
'''

HTML = HTML.replace('__TABS__', '\n'.join(tabs))
HTML = HTML.replace('__PANES__', '\n'.join(step_panes))
open('index.html', 'w', encoding='utf-8').write(HTML)
print('index.html', len(HTML), 'bytes;', question_no - 1, 'questions;', len(tabs), 'tabs')
