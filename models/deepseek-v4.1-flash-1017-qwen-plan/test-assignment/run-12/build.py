import re, html, json

src = open('page.html', encoding='utf-8').read()
s = src.index('<div class="disc-modal" id="wizardmodal"')
e = src.index('<!-- APRUVE POPUP', s)
w = src[s:e]
lists = re.findall(r'<ul class="disc-list" id="draggable-list(\d+)">(.*?)</ul>', w, re.S)
assert len(lists) == 24
groups = []
for num, body in lists:
    items = re.findall(r'<li class="disc-item" data-type="([disc])">(.*?)</li>', body, re.S)
    assert len(items) == 4, (num, items)
    groups.append([(t, html.unescape(text.strip())) for t, text in items])

step_names = ['Первый', 'Второй', 'Третий', 'Четвертый', 'Пятый', 'Шестой', 'Седьмой', 'Восьмой']

grip_svg = '''<svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><circle cx="6" cy="4" r="1.15" fill="currentColor"/><circle cx="10" cy="4" r="1.15" fill="currentColor"/><circle cx="6" cy="8" r="1.15" fill="currentColor"/><circle cx="10" cy="8" r="1.15" fill="currentColor"/><circle cx="6" cy="12" r="1.15" fill="currentColor"/><circle cx="10" cy="12" r="1.15" fill="currentColor"/></svg>'''

def card_html(gidx):
    items = groups[gidx]
    lis = []
    for i, (typ, text) in enumerate(items):
        lis.append(f'''              <li class="rank-item disc-item" data-type="{typ}" data-orig="{i}" data-rank="{i+1}" draggable="true" tabindex="0" aria-label="Место {i+1} из 4: {html.escape(text)}">
                <span class="rank-item__text">{html.escape(text)}</span>
                <span class="rank-item__grip disc-handle" draggable="true" aria-hidden="true" title="Перетащить">{grip_svg}</span>
              </li>''')
    return f'''          <article class="q-card disc-card" data-group="{gidx+1}">
            <div class="q-card__edge disc-card__title" data-mark="01">
              <span>Я наиболее</span>
            </div>
            <ul class="rank-list disc-list" id="draggable-list{gidx+1}" data-group="{gidx+1}" aria-label="Порядок качеств, блок {gidx+1}">
{chr(10).join(lis)}
            </ul>
            <div class="q-card__edge q-card__edge--bottom disc-card__foot" data-mark="04">
              <span>Я наименее</span>
            </div>
          </article>'''

panes = []
tabs = []
for step in range(8):
    ids = range(step*3, step*3+3)
    cards = '\n'.join(card_html(i) for i in ids)
    first, last = step*3+1, step*3+3
    panes.append(f'''      <section class="pane disc-pane{' is-active' if step == 0 else ''}" id="panel-{step}" role="tabpanel" aria-labelledby="tab-{step}" data-step-pane="{step}"{' hidden' if step else ''}>
        <div class="pane-meta">
          <span>Блоки {first:02d}–{last:02d} из 24</span>
          <span>Сверху — наиболее похожее, снизу — наименее</span>
        </div>
        <div class="question-grid">
{cards}
        </div>
      </section>''')
    tabs.append(f'''          <button class="step-tab disc-tab{' is-active' if step == 0 else ''}" id="tab-{step}" type="button" role="tab" aria-selected="{'true' if step == 0 else 'false'}" aria-controls="panel-{step}" data-step="{step}" data-step-btn="{step}">{step_names[step]}</button>''')

questions_html = '\n'.join(panes)
tabs_html = '\n'.join(tabs)

html_doc = r'''<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Тест DISC — узнайте свой профиль</title>
<meta name="description" content="Пройдите тест DISC: 24 блока, 8 шагов и результат сразу на экране. Без регистрации и отправки данных.">
<meta name="color-scheme" content="light">
<link rel="icon" href="data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCA2NCA2NCI+PHJlY3Qgd2lkdGg9IjY0IiBoZWlnaHQ9IjY0IiByeD0iMTYiIGZpbGw9IiMxMzFhMTciLz48cGF0aCBkPSJNMzIgOGEyNCAyNCAwIDAgMSAyNCAyNEgzMnoiIGZpbGw9IiNlODVkM2YiLz48cGF0aCBkPSJNNTYgMzJhMjQgMjQgMCAwIDEtMjQgMjRWMzJ6IiBmaWxsPSIjZjViODNkIi8+PHBhdGggZD0iTTMyIDU2QTI0IDI0IDAgMCAxIDggMzJoMjR6IiBmaWxsPSIjMmY5ZDc4Ii8+PHBhdGggZD0iTTggMzJBMjQgMjQgMCAwIDEgMzIgOHYyNHoiIGZpbGw9IiM0YzZmYTgiLz48Y2lyY2xlIGN4PSIzMiIgY3k9IjMyIiByPSI3IiBmaWxsPSIjZjRmMmVjIi8+PC9zdmc+">
<style>
:root{
  --ink:#131a17;
  --ink-soft:#34403a;
  --muted:#626d66;
  --paper:#f4f2ec;
  --paper-deep:#ebe8df;
  --card:#fffefa;
  --line:rgba(19,26,23,.13);
  --line-strong:rgba(19,26,23,.24);
  --lime:#c9f05a;
  --lime-deep:#a9d432;
  --d:#e85d3f;
  --i:#f0b43f;
  --s:#2f9d78;
  --c:#4c6fa8;
  --radius-xl:32px;
  --radius-lg:24px;
  --radius-md:16px;
  --shadow:0 24px 70px rgba(19,26,23,.08);
  --font:ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{
  margin:0;
  min-width:320px;
  min-height:100vh;
  background:var(--paper);
  color:var(--ink);
  font-family:var(--font);
  font-size:16px;
  line-height:1.5;
  -webkit-font-smoothing:antialiased;
  text-rendering:optimizeLegibility;
}
body.is-dragging{cursor:grabbing}
button{font:inherit;color:inherit}
button:focus-visible,a:focus-visible,[tabindex]:focus-visible{outline:3px solid rgba(76,111,168,.55);outline-offset:3px}
::selection{background:var(--lime);color:var(--ink)}
.page-bg{
  position:fixed;
  inset:0;
  z-index:-1;
  pointer-events:none;
  background:
    radial-gradient(46rem 34rem at 4% -8%,rgba(201,240,90,.30),transparent 62%),
    radial-gradient(34rem 30rem at 97% 12%,rgba(76,111,168,.09),transparent 68%),
    radial-gradient(30rem 26rem at 54% 106%,rgba(232,93,63,.055),transparent 70%),
    var(--paper);
}
.page-bg::after{
  content:"";
  position:absolute;
  inset:0;
  opacity:.30;
  background-image:radial-gradient(rgba(19,26,23,.13) .65px,transparent .65px);
  background-size:22px 22px;
  mask-image:linear-gradient(to bottom,rgba(0,0,0,.55),transparent 75%);
  -webkit-mask-image:linear-gradient(to bottom,rgba(0,0,0,.55),transparent 75%);
}
.app{min-height:100vh;display:flex;flex-direction:column}
.wrap{width:min(1200px,calc(100% - 48px));margin-inline:auto}
.site-head{
  display:flex;
  align-items:center;
  justify-content:space-between;
  gap:24px;
  padding:24px 0 10px;
}
.brand{display:flex;align-items:center;gap:12px;user-select:none}
.brand__mark{
  position:relative;
  width:38px;height:38px;flex:0 0 38px;
  border-radius:12px;
  background:conic-gradient(from -45deg,var(--d) 0 25%,var(--i) 0 50%,var(--s) 0 75%,var(--c) 0);
  box-shadow:0 8px 18px rgba(19,26,23,.15),inset 0 0 0 1px rgba(255,255,255,.25);
}
.brand__mark::after{content:"";position:absolute;inset:10px;border-radius:50%;background:var(--paper)}
.brand__text{display:flex;flex-direction:column;line-height:1.05}
.brand__text strong{font-size:16px;letter-spacing:.13em}
.brand__text span{font-size:10px;letter-spacing:.10em;text-transform:uppercase;color:var(--muted);margin-top:5px}
.site-head__right{display:flex;align-items:center;gap:11px;color:var(--muted);font-size:12px;letter-spacing:.015em}
.site-head__dot{width:4px;height:4px;border-radius:50%;background:var(--line-strong)}
main{flex:1}
.site-foot{
  margin-top:60px;
  border-top:1px solid var(--line);
  padding:22px 0 30px;
  color:var(--muted);
  font-size:12px;
}
.site-foot__inner{display:flex;justify-content:space-between;gap:18px;flex-wrap:wrap}

.screen{display:none}
.screen.is-active{display:block;animation:screenIn .42s cubic-bezier(.2,.75,.25,1) both}
@keyframes screenIn{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}

.eyebrow{
  display:inline-flex;align-items:center;gap:9px;
  color:var(--ink-soft);
  font-size:11px;font-weight:700;letter-spacing:.16em;text-transform:uppercase;
}
.eyebrow__dot{width:8px;height:8px;border-radius:50%;background:var(--lime-deep);box-shadow:0 0 0 4px rgba(201,240,90,.24)}
.eyebrow__line{width:28px;height:1px;background:var(--ink);opacity:.45}
.eyebrow--small{font-size:10px;letter-spacing:.14em}

.intro{padding:58px 0 34px}
.intro__grid{display:grid;grid-template-columns:minmax(0,1.2fr) minmax(360px,.8fr);align-items:center;gap:56px}
.intro__grid > *{min-width:0}
.intro__copy{max-width:720px;min-width:0}
.intro h1{
  margin:20px 0 24px;
  font-size:clamp(48px,5.4vw,74px);
  line-height:.96;
  letter-spacing:-.062em;
  font-weight:800;
}
.intro h1 em{font-style:normal;position:relative;white-space:nowrap;z-index:0}
.intro h1 em::after{
  content:"";
  position:absolute;left:-.035em;right:-.04em;bottom:.055em;height:.26em;
  border-radius:3px;
  background:var(--lime);
  z-index:-1;
  transform:rotate(-.45deg);
}
.intro__lead{max-width:590px;margin:0;color:var(--ink-soft);font-size:18px;line-height:1.62}
.intro__facts{display:flex;align-items:stretch;gap:0;margin:34px 0 32px;border-top:1px solid var(--line);border-bottom:1px solid var(--line);width:max-content;max-width:100%}
.intro__fact{padding:16px 26px 16px 0;display:flex;flex-direction:column;min-width:130px}
.intro__fact + .intro__fact{border-left:1px solid var(--line);padding-left:26px}
.intro__fact b{font-size:25px;line-height:1;letter-spacing:-.03em;font-weight:800}
.intro__fact span{font-size:11px;color:var(--muted);margin-top:7px;letter-spacing:.02em}
.intro__cta{display:flex;align-items:center;gap:18px;flex-wrap:wrap}
.intro__cta-note{font-size:12px;color:var(--muted)}
.intro__privacy{display:flex;align-items:center;gap:7px;margin:22px 0 0;color:var(--muted);font-size:12px}
.intro__privacy svg{flex:0 0 auto;opacity:.75}

.btn{
  --btn-bg:var(--ink);
  --btn-fg:#f8f8f2;
  display:inline-flex;align-items:center;justify-content:center;gap:12px;
  min-height:52px;
  padding:0 13px 0 24px;
  border:1px solid transparent;
  border-radius:999px;
  background:var(--btn-bg);
  color:var(--btn-fg);
  font-size:14px;font-weight:700;letter-spacing:.005em;
  white-space:nowrap;
  cursor:pointer;
  text-decoration:none;
  transition:transform .18s ease,box-shadow .18s ease,background .18s ease,color .18s ease;
}
.btn:hover{transform:translateY(-2px);box-shadow:0 12px 25px rgba(19,26,23,.18)}
.btn:active{transform:translateY(0)}
.btn__icon{
  width:32px;height:32px;flex:0 0 32px;border-radius:50%;
  display:grid;place-items:center;
  background:var(--lime);color:var(--ink);
}
.btn__icon svg{width:16px;height:16px}
.btn--primary{background:var(--ink);color:#fbfbf5}
.btn--ghost{background:transparent;color:var(--ink);border-color:var(--line-strong);padding:0 22px;box-shadow:none}
.btn--ghost:hover{background:rgba(255,255,255,.55);box-shadow:none}
.btn--ghost:disabled{opacity:.33;cursor:default;transform:none;box-shadow:none}
.btn--wide{width:100%;justify-content:space-between;padding-left:20px}
.btn--small{min-height:44px;font-size:13px}

.dimension-board{display:grid;grid-template-columns:1fr 1fr;gap:14px;position:relative;padding-bottom:20px}
.dimension{
  position:relative;
  min-height:172px;
  padding:19px;
  border:1px solid rgba(19,26,23,.12);
  border-radius:26px;
  background:linear-gradient(145deg,rgba(255,255,255,.88),rgba(255,254,250,.67));
  box-shadow:0 20px 45px rgba(19,26,23,.07),inset 0 1px 0 rgba(255,255,255,.9);
  overflow:hidden;
  display:flex;flex-direction:column;justify-content:space-between;
}
.dimension:nth-child(2),.dimension:nth-child(4){transform:translateY(20px)}
.dimension::before{
  content:"";position:absolute;left:0;top:0;width:100%;height:4px;background:var(--accent);
}
.dimension::after{
  content:"";position:absolute;width:110px;height:110px;border-radius:50%;
  right:-46px;bottom:-54px;background:var(--accent);opacity:.11;filter:blur(1px);
}
.dimension--d{--accent:var(--d)}
.dimension--i{--accent:var(--i)}
.dimension--s{--accent:var(--s)}
.dimension--c{--accent:var(--c)}
.dimension__letter{font-size:54px;line-height:.8;font-weight:800;letter-spacing:-.06em;color:var(--accent)}
.dimension__text{display:flex;flex-direction:column;gap:3px}
.dimension__text strong{font-size:15px;letter-spacing:-.01em}
.dimension__text span{font-size:11px;color:var(--muted)}
.board-caption{display:flex;align-items:center;justify-content:center;gap:8px;margin-top:20px;color:var(--muted);font-size:11px;letter-spacing:.1em;text-transform:uppercase}
.board-caption span{width:18px;height:1px;background:var(--line-strong)}

.intro__strip{display:grid;grid-template-columns:repeat(3,1fr);gap:0;margin-top:26px;border-top:1px solid var(--line)}
.strip-item{display:flex;gap:16px;padding:24px 30px 6px 0}
.strip-item + .strip-item{border-left:1px solid var(--line);padding-left:30px}
.strip-num{font-size:11px;color:var(--muted);font-weight:700;padding-top:3px}
.strip-item p{margin:0;color:var(--muted);font-size:13px;line-height:1.5;max-width:260px}
.strip-item strong{display:block;color:var(--ink);font-size:14px;margin-bottom:3px}

.test{padding:32px 0 20px}
.test-shell{width:min(1180px,calc(100% - 48px));margin-inline:auto}
.test-top{display:flex;align-items:flex-start;justify-content:space-between;gap:24px}
.test-title{margin:7px 0 0;font-size:clamp(30px,4vw,48px);line-height:1.04;letter-spacing:-.045em;font-weight:800}
.test-title:focus,.result-head h1:focus{outline:none}
.test-lead{max-width:720px;margin:14px 0 25px;color:var(--ink-soft);font-size:15px;line-height:1.55}
.test-lead strong{color:var(--ink);font-weight:650}
.icon-btn{
  width:42px;height:42px;flex:0 0 42px;border-radius:50%;
  display:grid;place-items:center;
  border:1px solid var(--line);background:rgba(255,255,255,.55);color:var(--ink);
  cursor:pointer;transition:background .18s,border-color .18s,transform .18s;
}
.icon-btn:hover{background:#fff;border-color:var(--line-strong);transform:rotate(4deg)}
.icon-btn svg{width:17px;height:17px}

.step-tabs-wrap{position:relative;margin:0 0 15px;border-bottom:1px solid var(--line)}
.step-tabs{display:flex;gap:4px;overflow-x:auto;scrollbar-width:none;-ms-overflow-style:none;padding:0 0 10px}
.step-tabs::-webkit-scrollbar{display:none}
.step-tab{
  appearance:none;border:1px solid transparent;background:transparent;
  border-radius:999px;padding:7px 13px;color:var(--muted);
  font-size:12px;line-height:1;white-space:nowrap;cursor:pointer;
  transition:color .18s,background .18s,border-color .18s;
}
.step-tab:hover{color:var(--ink);background:rgba(19,26,23,.055)}
.step-tab.is-active{background:var(--ink);border-color:var(--ink);color:#fff}
.test-status{display:flex;align-items:center;justify-content:space-between;gap:16px;color:var(--muted);font-size:11px;letter-spacing:.055em;text-transform:uppercase}
.test-status b{color:var(--ink)}
.progress-track{height:5px;margin-top:9px;border-radius:99px;background:rgba(19,26,23,.10);overflow:hidden}
.progress-fill{display:block;height:100%;width:12.5%;border-radius:inherit;background:linear-gradient(90deg,var(--ink),#57664d 65%,var(--lime-deep));transition:width .38s cubic-bezier(.2,.8,.2,1)}

.panes{margin-top:30px}
.pane[hidden]{display:none}
.pane-meta{display:flex;justify-content:space-between;gap:18px;margin:0 0 12px;color:var(--muted);font-size:10px;letter-spacing:.10em;text-transform:uppercase}
.question-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}
.q-card{
  display:flex;flex-direction:column;
  padding:15px;
  min-width:0;
  background:rgba(255,254,250,.82);
  border:1px solid var(--line);
  border-radius:var(--radius-lg);
  box-shadow:0 16px 45px rgba(19,26,23,.055),inset 0 1px 0 rgba(255,255,255,.9);
}
.q-card__edge{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:1px 3px 9px;color:var(--muted);font-size:9px;font-weight:700;letter-spacing:.15em;text-transform:uppercase}
.q-card__edge--bottom{padding:9px 3px 1px}
.q-card__edge::after{content:attr(data-mark);font-variant-numeric:tabular-nums;color:rgba(19,26,23,.30);font-weight:600;letter-spacing:.06em}
.rank-list{list-style:none;display:flex;flex-direction:column;gap:7px;margin:0;padding:0;flex:1}
.rank-item{
  display:flex;align-items:center;gap:10px;
  min-height:48px;
  padding:9px 8px 9px 10px;
  border:1px solid rgba(19,26,23,.10);
  border-radius:13px;
  background:var(--card);
  cursor:grab;
  user-select:none;-webkit-user-select:none;
  touch-action:pan-y;
  -webkit-touch-callout:none;
  transition:border-color .16s,box-shadow .16s,background .16s,transform .16s,opacity .16s;
}
.rank-item:hover{border-color:rgba(19,26,23,.22);box-shadow:0 6px 18px rgba(19,26,23,.07)}
.rank-item.is-dragging{opacity:.48;border-color:rgba(19,26,23,.36);background:#f7fbe9;box-shadow:0 12px 25px rgba(19,26,23,.12);transform:scale(1.012);cursor:grabbing}
.rank-item::before{
  content:attr(data-rank);
  width:24px;height:24px;flex:0 0 24px;border-radius:50%;
  display:grid;place-items:center;
  background:#eef0e8;color:#5f6b64;
  font-size:10px;font-weight:800;font-variant-numeric:tabular-nums;
  transition:background .18s,color .18s;
}
.rank-item:first-child::before{background:var(--ink);color:#fff}
.rank-item:last-child::before{background:var(--paper-deep);color:#6d7871}
.rank-item__text{flex:1;min-width:0;font-size:13.5px;line-height:1.27;letter-spacing:-.005em;color:var(--ink)}
.rank-item__grip{
  width:28px;height:32px;flex:0 0 28px;margin:-6px -2px -6px 0;
  display:flex;align-items:center;justify-content:center;
  border-radius:8px;color:#a7aea8;cursor:grab;touch-action:none;
}
.rank-item__grip:hover{background:rgba(19,26,23,.05);color:#5c665f}
.rank-item:active .rank-item__grip{cursor:grabbing}

.test-actions{display:flex;align-items:center;justify-content:space-between;gap:20px;margin-top:24px;padding-top:20px;border-top:1px solid var(--line)}
.test-actions__right{display:flex;align-items:center;gap:14px;flex-wrap:wrap;justify-content:flex-end}
.test-actions__hint{color:var(--muted);font-size:11px}
[hidden]{display:none!important}

.result{padding:48px 0 12px}
.result-shell{width:min(1080px,calc(100% - 48px));margin-inline:auto}
.result-head{max-width:760px}
.result-head h1{margin:14px 0 12px;font-size:clamp(42px,5.5vw,70px);line-height:.98;letter-spacing:-.055em;font-weight:800}
.result-head p{margin:0;color:var(--ink-soft);font-size:16px;line-height:1.6;max-width:670px}
.result-layout{display:grid;grid-template-columns:minmax(0,1.45fr) minmax(300px,.72fr);gap:18px;margin-top:34px;align-items:start}
.result-panel{padding:24px 26px 22px;background:rgba(255,254,250,.88);border:1px solid var(--line);border-radius:var(--radius-xl);box-shadow:var(--shadow)}
.result-panel__top{display:flex;align-items:center;justify-content:space-between;gap:20px;padding-bottom:20px;border-bottom:1px solid var(--line)}
.result-panel__top > span:first-child{font-size:11px;font-weight:700;letter-spacing:.13em;text-transform:uppercase;color:var(--muted)}
.score-line{font-size:14px;font-weight:750;font-variant-numeric:tabular-nums;letter-spacing:.01em;color:var(--ink);white-space:nowrap}
.score-rows{padding:9px 0 4px}
.score-row{display:grid;grid-template-columns:minmax(150px,1.02fr) minmax(110px,1.5fr) 48px;align-items:center;gap:18px;padding:12px 0;border-bottom:1px solid rgba(19,26,23,.07)}
.score-row:last-child{border-bottom:0}
.score-row__label{display:flex;align-items:center;gap:10px;min-width:0}
.score-letter{width:32px;height:32px;flex:0 0 32px;border-radius:10px;display:grid;place-items:center;background:var(--score-color);color:#fff;font-size:14px;font-weight:800;box-shadow:inset 0 1px 0 rgba(255,255,255,.28)}
.score-name{font-size:13px;font-weight:600;line-height:1.2;min-width:0}
.score-name small{display:block;font-size:10px;font-weight:500;color:var(--muted);margin-top:2px;letter-spacing:.04em}
.meter{position:relative;height:8px;border-radius:99px;background:#ecebe3;overflow:visible}
.meter::before{content:"";position:absolute;left:50%;top:-3px;bottom:-3px;width:1px;background:rgba(19,26,23,.20);z-index:1}
.meter__fill{position:absolute;top:0;bottom:0;border-radius:99px;background:var(--score-color);width:0;transition:width .75s cubic-bezier(.2,.8,.2,1)}
.meter__fill.is-positive{left:50%}
.meter__fill.is-negative{right:50%}
.score-value{font-size:14px;font-weight:750;font-variant-numeric:tabular-nums;text-align:right;color:var(--score-color)}
.score-scale{display:grid;grid-template-columns:minmax(150px,1.02fr) minmax(110px,1.5fr) 48px;gap:18px;margin-top:4px;color:var(--muted);font-size:9px;letter-spacing:.04em;font-variant-numeric:tabular-nums}
.score-scale__track{grid-column:2;display:flex;justify-content:space-between}
.score-caption{margin:18px 0 0;color:var(--muted);font-size:11px;line-height:1.55}

.result-aside{position:relative;overflow:hidden;padding:25px;border-radius:var(--radius-xl);background:var(--ink);color:#f6f7f0;box-shadow:0 22px 48px rgba(19,26,23,.16)}
.result-aside::after{content:"";position:absolute;right:-55px;bottom:-65px;width:190px;height:190px;border-radius:50%;background:conic-gradient(from -45deg,var(--d) 0 25%,var(--i) 0 50%,var(--s) 0 75%,var(--c) 0);opacity:.18;filter:blur(1px);pointer-events:none}
.result-aside__label{display:block;font-size:10px;font-weight:700;letter-spacing:.15em;text-transform:uppercase;color:rgba(255,255,255,.54)}
.result-lead{position:relative;z-index:1;margin:13px 0 24px;font-size:26px;line-height:1.12;letter-spacing:-.035em;font-weight:750;min-height:59px}
.result-lead b{color:var(--lime);font-weight:800}
.formula{position:relative;z-index:1;display:flex;flex-direction:column;gap:8px;padding:15px 0 17px;border-top:1px solid rgba(255,255,255,.15);border-bottom:1px solid rgba(255,255,255,.15)}
.formula__row{display:flex;align-items:center;gap:10px;color:rgba(255,255,255,.67);font-size:11px}
.formula__mark{min-width:34px;height:22px;padding:0 7px;display:inline-flex;align-items:center;justify-content:center;border-radius:6px;background:rgba(255,255,255,.09);color:#fff;font-size:11px;font-weight:700;font-variant-numeric:tabular-nums}
.result-aside .btn{margin-top:21px;background:var(--lime);color:var(--ink);position:relative;z-index:1;padding-left:20px}
.result-aside .btn:hover{box-shadow:0 14px 26px rgba(0,0,0,.23)}
.result-aside .btn__icon{background:var(--ink);color:var(--lime)}
.result-note{position:relative;z-index:1;margin:18px 0 0;color:rgba(255,255,255,.50);font-size:10.5px;line-height:1.55}
.result-bottom{display:flex;justify-content:space-between;gap:18px;flex-wrap:wrap;margin-top:22px;padding-top:16px;border-top:1px solid var(--line);color:var(--muted);font-size:11px}

.sr-only{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}

@media (max-width:1050px){
  .intro__grid{grid-template-columns:minmax(0,1.03fr) minmax(330px,.97fr);gap:40px}
  .intro h1{font-size:clamp(42px,5.2vw,56px)}
  .dimension{min-height:150px;padding:16px}
  .dimension__letter{font-size:46px}
  .question-grid{gap:11px}
  .q-card{padding:12px}
  .rank-item{padding-left:8px;gap:8px}
  .rank-item__text{font-size:12.5px}
  .result-layout{grid-template-columns:1fr}
  .result-aside{display:grid;grid-template-columns:1fr auto;column-gap:30px;align-items:start}
  .result-aside__label,.result-lead{grid-column:1}
  .result-aside .formula{grid-column:1;grid-row:3}
  .result-aside .btn{grid-column:2;grid-row:1 / span 3;align-self:center;width:auto;min-width:210px}
  .result-aside .result-note{grid-column:1 / -1}
}
@media (max-width:820px){
  .wrap,.test-shell,.result-shell{width:min(100% - 34px,700px)}
  .site-head{padding-top:18px}
  .site-head__right .site-head__meta:first-child,.site-head__dot{display:none}
  .intro{padding-top:38px}
  .intro__grid{grid-template-columns:1fr;gap:48px}
  .intro__copy{max-width:none}
  .intro h1{font-size:clamp(46px,10vw,72px)}
  .intro__copy{max-width:none}
  .intro__aside{max-width:520px;width:100%;margin-inline:auto}
  .dimension{min-height:148px}
  .intro__strip{grid-template-columns:1fr}
  .strip-item{padding:17px 0}
  .strip-item + .strip-item{border-left:0;border-top:1px solid var(--line);padding-left:0}
  .strip-item p{max-width:none}
  .test{padding-top:20px}
  .question-grid{grid-template-columns:1fr;gap:12px}
  .q-card{padding:14px}
  .rank-item{min-height:50px;padding-top:10px;padding-bottom:10px}
  .rank-item__text{font-size:14px}
  .test-actions__hint{display:none}
  .result-layout{margin-top:26px}
}
@media (max-width:600px){
  .intro h1{font-size:clamp(34px,10.2vw,46px)}
  .site-head__right .site-head__meta:last-child{display:none}
  .intro__facts{width:100%}
  .intro__fact{flex:1;min-width:0;padding-right:12px}
  .intro__fact + .intro__fact{padding-left:14px}
  .intro__fact b{font-size:22px}
  .intro__fact span{font-size:10px}
  .intro__cta .btn{width:100%;justify-content:space-between}
  .intro__cta-note{width:100%;text-align:center}
  .dimension{min-height:132px;padding:14px;border-radius:20px}
  .dimension__letter{font-size:40px}
  .dimension__text strong{font-size:13px}
  .dimension__text span{font-size:10px}
  .pane-meta span:last-child{display:none}
  .test-actions{align-items:stretch}
  .test-actions .btn--ghost{min-width:94px}
  .test-actions__right{flex:1;justify-content:flex-end}
  .test-actions__right .btn--primary{flex:1;justify-content:space-between}
  .result{padding-top:34px}
  .result-panel{padding:19px 16px 18px;border-radius:24px}
  .result-panel__top{align-items:flex-start;flex-direction:column;gap:7px;padding-bottom:16px}
  .score-row{grid-template-columns:1fr 42px;gap:8px 12px;padding:12px 0}
  .score-row__label{grid-column:1}
  .meter{grid-column:1;grid-row:2}
  .score-value{grid-column:2;grid-row:1 / span 2;font-size:16px}
  .score-scale{display:none}
  .result-aside{display:block;padding:21px}
  .result-aside .btn{width:100%;margin-top:22px}
  .result-lead{min-height:0}
  .site-foot{margin-top:34px}
  .site-foot__inner{flex-direction:column;gap:6px}
}
@media (max-width:380px){
  .test-actions{gap:10px}
  #finishBtn{padding-left:14px;padding-right:10px;gap:6px;font-size:12px}
  #finishBtn .btn__icon{width:26px;height:26px;flex-basis:26px}
}
@media (prefers-reduced-motion:reduce){
  html{scroll-behavior:auto}
  *,*::before,*::after{animation-duration:.001ms!important;animation-iteration-count:1!important;transition-duration:.001ms!important}
}
</style>
</head>
<body>
<div class="page-bg" aria-hidden="true"></div>
<div class="app">
  <header class="site-head wrap">
    <div class="brand" aria-label="DISC — поведенческий профиль">
      <span class="brand__mark" aria-hidden="true"></span>
      <span class="brand__text"><strong>DISC</strong><span>поведенческий профиль</span></span>
    </div>
    <div class="site-head__right">
      <span class="site-head__meta">Школа менеджмента</span>
      <span class="site-head__dot" aria-hidden="true"></span>
      <span class="site-head__meta">24 блока · 5 минут</span>
    </div>
  </header>

  <main>
    <section class="screen screen--intro is-active" id="introScreen" aria-labelledby="introTitle" aria-hidden="false">
      <div class="wrap">
        <div class="intro">
          <div class="intro__grid">
            <div class="intro__copy">
              <div class="eyebrow"><span class="eyebrow__dot" aria-hidden="true"></span> Поведенческий тест · DISC</div>
              <h1 id="introTitle">Узнайте,<br><em>как вы действуете</em></h1>
              <p class="intro__lead">DISC — простой язык для описания привычных моделей поведения: как вы принимаете решения, общаетесь, работаете с правилами и реагируете на изменения.</p>
              <div class="intro__facts" role="list" aria-label="Параметры теста">
                <div class="intro__fact" role="listitem"><b>24</b><span>блока с качествами</span></div>
                <div class="intro__fact" role="listitem"><b>8</b><span>коротких шагов</span></div>
                <div class="intro__fact" role="listitem"><b>5</b><span>минут</span></div>
              </div>
              <div class="intro__cta">
                <button class="btn btn--primary" id="startBtn" type="button" data-disc-open data-modal-open="wizardmodal" aria-controls="wizardmodal">
                  <span id="startLabel">Начать тест</span>
                  <span class="btn__icon" aria-hidden="true"><svg viewBox="0 0 16 16" fill="none"><path d="M2.5 8h10M8.5 4l4 4-4 4" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg></span>
                </button>
                <span class="intro__cta-note">Без регистрации и почты</span>
              </div>
              <p class="intro__privacy"><svg width="13" height="13" viewBox="0 0 16 16" fill="none" aria-hidden="true"><rect x="3" y="7" width="10" height="7" rx="2" stroke="currentColor" stroke-width="1.2"/><path d="M5.5 7V5.5a2.5 2.5 0 0 1 5 0V7" stroke="currentColor" stroke-width="1.2"/></svg> Ответы остаются в браузере: приложение не отправляет данные.</p>
            </div>
            <div class="intro__aside" aria-hidden="true">
              <div class="dimension-board">
                <article class="dimension dimension--d">
                  <span class="dimension__letter">D</span>
                  <div class="dimension__text"><strong>Доминирование</strong><span>решительность · результат</span></div>
                </article>
                <article class="dimension dimension--i">
                  <span class="dimension__letter">I</span>
                  <div class="dimension__text"><strong>Влияние</strong><span>коммуникация · энергия</span></div>
                </article>
                <article class="dimension dimension--s">
                  <span class="dimension__letter">S</span>
                  <div class="dimension__text"><strong>Стабильность</strong><span>поддержка · постоянство</span></div>
                </article>
                <article class="dimension dimension--c">
                  <span class="dimension__letter">C</span>
                  <div class="dimension__text"><strong>Соответствие</strong><span>точность · порядок</span></div>
                </article>
              </div>
              <div class="board-caption"><span></span> Четыре шкалы поведения <span></span></div>
            </div>
          </div>
          <div class="intro__strip">
            <div class="strip-item"><span class="strip-num">01</span><p><strong>Сравните качества</strong>В каждом блоке расставьте четыре слова по порядку.</p></div>
            <div class="strip-item"><span class="strip-num">02</span><p><strong>Пройдите 8 шагов</strong>Перетаскивайте карточки или используйте клавиши ↑ и ↓.</p></div>
            <div class="strip-item"><span class="strip-num">03</span><p><strong>Получите баллы</strong>Результат по четырём шкалам появится сразу на экране.</p></div>
          </div>
        </div>
      </div>
    </section>

    <section class="screen screen--test disc-modal" id="wizardmodal" aria-labelledby="stepTitle" aria-hidden="true">
      <div class="test-shell">
        <div class="test-top">
          <div>
            <div class="eyebrow eyebrow--small"><span class="eyebrow__line" aria-hidden="true"></span> Тестирование DISC</div>
            <h2 class="test-title" id="stepTitle" tabindex="-1">Расставьте качества</h2>
          </div>
          <button class="icon-btn" id="exitTest" type="button" data-disc-close aria-label="Закрыть тест и вернуться на главную">
            <svg viewBox="0 0 18 18" fill="none" aria-hidden="true"><path d="M4 4l10 10M14 4L4 14" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
          </button>
        </div>
        <p class="test-lead">В каждом блоке расположите слова <strong>от наиболее похожего на вас до наименее похожего</strong>. Верхняя строка — «я наиболее», нижняя — «я наименее».</p>

        <div class="step-tabs-wrap">
          <div class="step-tabs disc-modal__tabs" id="stepTabs" role="tablist" aria-label="Шаги теста">
__TABS__
          </div>
        </div>
        <div class="test-status">
          <span>Шаг <b id="stepCounter">1</b> из 8</span>
          <span id="blockCounter">Блоки 01–03 из 24</span>
        </div>
        <div class="progress-track disc-progress" id="progressTrack" role="progressbar" aria-label="Прогресс теста" aria-valuemin="1" aria-valuemax="8" aria-valuenow="1">
          <span class="progress-fill disc-progress__bar" id="discProgress"></span>
        </div>

        <div class="panes disc-modal__body" id="rootwizard" data-step="0">
__QUESTIONS__

        <div class="test-actions disc-actions">
          <button class="btn disc-btn disc-btn--ghost btn--ghost" id="prevBtn" type="button" data-disc-prev disabled>
            <svg width="15" height="15" viewBox="0 0 16 16" fill="none" aria-hidden="true"><path d="M13.5 8h-10M7.5 4l-4 4 4 4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
            Назад
          </button>
          <div class="test-actions__right">
            <span class="test-actions__hint">Ответы сохраняются при переходах</span>
            <button class="btn disc-btn disc-btn--primary btn--primary" id="nextBtn" type="button" data-disc-next>
              Далее
              <span class="btn__icon" aria-hidden="true"><svg viewBox="0 0 16 16" fill="none"><path d="M2.5 8h10M8.5 4l4 4-4 4" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg></span>
            </button>
            <button class="btn disc-btn disc-btn--primary btn--primary" id="finishBtn" type="button" data-disc-finish hidden>
              Завершить тест
              <span class="btn__icon" aria-hidden="true"><svg viewBox="0 0 16 16" fill="none"><path d="M3.5 8.5l3 3 6-7" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/></svg></span>
            </button>
          </div>
        </div>
        </div>
      </div>
    </section>

    <section class="screen screen--result" id="resultScreen" aria-labelledby="resultTitle" aria-hidden="true">
      <div class="result-shell">
        <div class="result-head">
          <div class="eyebrow"><span class="eyebrow__dot" aria-hidden="true"></span> Тест завершён</div>
          <h1 id="resultTitle" tabindex="-1">Ваш DISC-профиль</h1>
          <p>Баллы показывают, как часто вы выбирали качества каждой шкалы как наиболее и наименее похожие на себя.</p>
        </div>

        <div class="result-layout">
          <div class="result-panel">
            <div class="result-panel__top">
              <span>Итоговые баллы</span>
              <div class="result__score"><span class="score-line" id="scoreLine" role="status" aria-live="polite">D:0, I:0, S:0, C:0</span></div>
            </div>
            <div class="score-rows">
              <div class="score-row" style="--score-color:var(--d)">
                <div class="score-row__label"><span class="score-letter">D</span><span class="score-name">Доминирование<small>решительность · результат</small></span></div>
                <div class="meter" aria-hidden="true"><span class="meter__fill" data-bar="d"></span></div>
                <span class="score-value" data-value="d">0</span>
              </div>
              <div class="score-row" style="--score-color:var(--i)">
                <div class="score-row__label"><span class="score-letter">I</span><span class="score-name">Влияние<small>коммуникация · энергия</small></span></div>
                <div class="meter" aria-hidden="true"><span class="meter__fill" data-bar="i"></span></div>
                <span class="score-value" data-value="i">0</span>
              </div>
              <div class="score-row" style="--score-color:var(--s)">
                <div class="score-row__label"><span class="score-letter">S</span><span class="score-name">Стабильность<small>поддержка · постоянство</small></span></div>
                <div class="meter" aria-hidden="true"><span class="meter__fill" data-bar="s"></span></div>
                <span class="score-value" data-value="s">0</span>
              </div>
              <div class="score-row" style="--score-color:var(--c)">
                <div class="score-row__label"><span class="score-letter">C</span><span class="score-name">Соответствие<small>точность · порядок</small></span></div>
                <div class="meter" aria-hidden="true"><span class="meter__fill" data-bar="c"></span></div>
                <span class="score-value" data-value="c">0</span>
              </div>
            </div>
            <div class="score-scale" aria-hidden="true"><span class="score-scale__track"><span>−24</span><span>0</span><span>+24</span></span></div>
            <p class="score-caption">Шкала от −24 до +24. В каждом из 24 блоков учитываются только первая и последняя позиции.</p>
          </div>

          <aside class="result-aside">
            <span class="result-aside__label">Наибольший балл</span>
            <p class="result-lead" id="resultLead">—</p>
            <div class="formula" aria-label="Как считается результат">
              <div class="formula__row"><span class="formula__mark">+1</span><span>качество на первом месте</span></div>
              <div class="formula__row"><span class="formula__mark">−1</span><span>качество на последнем месте</span></div>
            </div>
            <button class="btn btn--primary btn--wide" id="restartBtn" type="button" data-disc-restart>
              Пройти заново
              <span class="btn__icon" aria-hidden="true"><svg viewBox="0 0 16 16" fill="none"><path d="M13 5.5A5.5 5.5 0 1 0 13.4 9" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><path d="M13.2 2.6v3.3H9.9" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg></span>
            </button>
            <p class="result-note">DISC описывает предпочтительные модели поведения, а не интеллект, опыт или профессиональные навыки. Это результат самотестирования.</p>
          </aside>
        </div>

        <div class="result-bottom">
          <span>Спасибо за прохождение теста</span>
          <span>Все вычисления выполнены локально · данные не отправлялись</span>
        </div>
      </div>
    </section>
  </main>

  <footer class="site-foot">
    <div class="wrap site-foot__inner">
      <span>DISC · поведенческий профиль</span>
      <span>Копия теста для локального прохождения</span>
    </div>
  </footer>
</div>

<div class="sr-only" id="liveStatus" aria-live="polite"></div>

<script>
(() => {
  'use strict';

  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));
  const clamp = (value, min, max) => Math.min(Math.max(value, min), max);

  const TOTAL_STEPS = 8;
  const BLOCKS_PER_STEP = 3;
  const screenIds = {
    intro: 'introScreen',
    test: 'wizardmodal',
    result: 'resultScreen'
  };

  const introScreen = $('#introScreen');
  const testScreen = $('#wizardmodal');
  const resultScreen = $('#resultScreen');
  const startBtn = $('#startBtn');
  const startLabel = $('#startLabel');
  const exitTestBtn = $('#exitTest');
  const stepTabs = $('#stepTabs');
  const tabs = $$('.step-tab', stepTabs);
  const panes = $$('.pane');
  const rootwizard = $('#rootwizard');
  const stepCounter = $('#stepCounter');
  const blockCounter = $('#blockCounter');
  const progressTrack = $('#progressTrack');
  const progressBar = $('#discProgress');
  const prevBtn = $('#prevBtn');
  const nextBtn = $('#nextBtn');
  const finishBtn = $('#finishBtn');
  const restartBtn = $('#restartBtn');
  const scoreLine = $('#scoreLine');
  const resultLead = $('#resultLead');
  const liveStatus = $('#liveStatus');
  const lists = $$('.rank-list');

  let currentStep = 0;
  let hasStarted = false;

  const formatNumber = (value) => {
    const n = Number(value) || 0;
    return n > 0 ? '+' + n : String(n);
  };

  const updateRanks = (list) => {
    const items = Array.from(list.children);
    items.forEach((item, index) => {
      item.dataset.rank = String(index + 1);
      const text = $('.rank-item__text', item)?.textContent.trim() || '';
      item.setAttribute('aria-label', `Место ${index + 1} из ${items.length}: ${text}`);
    });
  };

  const centerActiveTab = (behavior = 'smooth') => {
    const active = tabs[currentStep];
    if (!active) return;
    if (stepTabs.scrollWidth <= stepTabs.clientWidth + 2) return;
    const left = active.offsetLeft - (stepTabs.clientWidth - active.offsetWidth) / 2;
    stepTabs.scrollTo({ left: Math.max(0, left), behavior });
  };

  const updateStepUi = (options = {}) => {
    tabs.forEach((tab, index) => {
      const active = index === currentStep;
      tab.classList.toggle('is-active', active);
      tab.setAttribute('aria-selected', active ? 'true' : 'false');
      tab.tabIndex = active ? 0 : -1;
    });
    panes.forEach((pane, index) => {
      const active = index === currentStep;
      pane.classList.toggle('is-active', active);
      pane.hidden = !active;
    });

    if (rootwizard) rootwizard.dataset.step = String(currentStep);
    const firstBlock = currentStep * BLOCKS_PER_STEP + 1;
    const lastBlock = firstBlock + BLOCKS_PER_STEP - 1;
    stepCounter.textContent = String(currentStep + 1);
    blockCounter.textContent = `Блоки ${String(firstBlock).padStart(2, '0')}–${String(lastBlock).padStart(2, '0')} из 24`;
    progressBar.style.width = `${((currentStep + 1) / TOTAL_STEPS) * 100}%`;
    progressTrack.setAttribute('aria-valuenow', String(currentStep + 1));

    prevBtn.disabled = currentStep === 0;
    nextBtn.hidden = currentStep === TOTAL_STEPS - 1;
    finishBtn.hidden = currentStep !== TOTAL_STEPS - 1;

    requestAnimationFrame(() => centerActiveTab(options.instant ? 'auto' : 'smooth'));

    if (options.scroll !== false) {
      const top = testScreen.getBoundingClientRect().top + window.scrollY - 8;
      window.scrollTo({ top: Math.max(0, top), behavior: options.instant ? 'auto' : 'smooth' });
    }
  };

  const showScreen = (name) => {
    Object.entries(screenIds).forEach(([key, id]) => {
      const screen = document.getElementById(id);
      if (!screen) return;
      const active = key === name;
      screen.classList.toggle('is-active', active);
      screen.setAttribute('aria-hidden', active ? 'false' : 'true');
    });
    document.getElementById(screenIds.test)?.classList.toggle('is-open', name === 'test');
    document.body.dataset.screen = name;
    document.title = name === 'result' ? 'Ваш результат DISC' : 'Тест DISC — узнайте свой профиль';
    window.scrollTo({ top: 0, behavior: 'auto' });
  };

  const goToStep = (step, options = {}) => {
    currentStep = clamp(step, 0, TOTAL_STEPS - 1);
    updateStepUi(options);
  };

  const startTest = () => {
    hasStarted = true;
    startLabel.textContent = 'Продолжить тест';
    showScreen('test');
    updateStepUi({ instant: true, scroll: false });
    requestAnimationFrame(() => {
      const title = $('#stepTitle');
      if (title) title.focus({ preventScroll: true });
    });
  };

  const finishTest = () => {
    const score = { d: 0, i: 0, s: 0, c: 0 };
    lists.forEach((list) => {
      const items = Array.from(list.children);
      const most = items[0]?.dataset.type;
      const least = items[3]?.dataset.type;
      if (most && Object.prototype.hasOwnProperty.call(score, most)) score[most] += 1;
      if (least && Object.prototype.hasOwnProperty.call(score, least)) score[least] -= 1;
    });

    scoreLine.textContent = `D:${score.d}, I:${score.i}, S:${score.s}, C:${score.c}`;
    ['d', 'i', 's', 'c'].forEach((key) => { scoreLine.dataset[key] = String(score[key]); });

    ['d', 'i', 's', 'c'].forEach((key) => {
      const value = score[key];
      const valueEl = $(`[data-value="${key}"]`);
      const barEl = $(`[data-bar="${key}"]`);
      if (valueEl) valueEl.textContent = formatNumber(value);
      if (barEl) {
        barEl.classList.toggle('is-positive', value >= 0);
        barEl.classList.toggle('is-negative', value < 0);
        barEl.style.width = '0%';
        requestAnimationFrame(() => {
          requestAnimationFrame(() => {
            barEl.style.width = `${(Math.abs(value) / 24) * 50}%`;
          });
        });
      }
    });

    const maxScore = Math.max(score.d, score.i, score.s, score.c);
    const topKeys = ['d', 'i', 's', 'c'].filter((key) => score[key] === maxScore);
    const letters = topKeys.map((key) => key.toUpperCase());
    if (maxScore <= 0) {
      resultLead.textContent = 'Выраженной ведущей шкалы нет.';
    } else if (letters.length === 1) {
      resultLead.innerHTML = `<b>${letters[0]}</b> — ${formatNumber(maxScore)}`;
    } else {
      const joined = letters.length === 2 ? `${letters[0]} и ${letters[1]}` : `${letters.slice(0, -1).join(', ')} и ${letters[letters.length - 1]}`;
      resultLead.innerHTML = `<b>${joined}</b> — ${formatNumber(maxScore)}`;
    }

    showScreen('result');
    $('#resultTitle')?.focus({ preventScroll: true });
    window.__discScore = { ...score };
  };

  const resetTest = () => {
    lists.forEach((list) => {
      Array.from(list.children)
        .sort((a, b) => Number(a.dataset.orig) - Number(b.dataset.orig))
        .forEach((item) => list.appendChild(item));
      updateRanks(list);
    });
    ['d', 'i', 's', 'c'].forEach((key) => {
      const barEl = $(`[data-bar="${key}"]`);
      if (barEl) {
        barEl.style.width = '0%';
        barEl.classList.remove('is-positive', 'is-negative');
      }
      const valueEl = $(`[data-value="${key}"]`);
      if (valueEl) valueEl.textContent = '0';
    });
    scoreLine.textContent = 'D:0, I:0, S:0, C:0';
    ['d', 'i', 's', 'c'].forEach((key) => { scoreLine.dataset[key] = '0'; });
    resultLead.textContent = '—';
    currentStep = 0;
    hasStarted = false;
    startLabel.textContent = 'Начать тест';
    updateStepUi({ instant: true, scroll: false });
    showScreen('intro');
    startBtn.focus({ preventScroll: true });
    try { delete window.__discScore; } catch (_) { window.__discScore = undefined; }
  };

  startBtn.addEventListener('click', startTest);
  exitTestBtn.addEventListener('click', () => {
    showScreen('intro');
    startLabel.textContent = hasStarted ? 'Продолжить тест' : 'Начать тест';
    startBtn.focus({ preventScroll: true });
  });
  prevBtn.addEventListener('click', () => goToStep(currentStep - 1));
  nextBtn.addEventListener('click', () => goToStep(currentStep + 1));
  finishBtn.addEventListener('click', finishTest);
  restartBtn.addEventListener('click', resetTest);

  document.addEventListener('keydown', (event) => {
    if (event.key !== 'Escape' || document.body.dataset.screen !== 'test') return;
    if (pointerDrag) {
      endPointerDrag(null);
      return;
    }
    showScreen('intro');
    startLabel.textContent = hasStarted ? 'Продолжить тест' : 'Начать тест';
    startBtn.focus({ preventScroll: true });
  });

  tabs.forEach((tab) => {
    tab.addEventListener('click', () => goToStep(Number(tab.dataset.step)));
    tab.addEventListener('keydown', (event) => {
      if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
      event.preventDefault();
      let target = currentStep;
      if (event.key === 'ArrowLeft') target = currentStep - 1;
      if (event.key === 'ArrowRight') target = currentStep + 1;
      if (event.key === 'Home') target = 0;
      if (event.key === 'End') target = TOTAL_STEPS - 1;
      goToStep(target);
      tabs[currentStep]?.focus({ preventScroll: true });
    });
  });

  // Keyboard ranking for accessibility and as a drag alternative.
  const moveItem = (item, direction) => {
    const list = item.parentElement;
    if (!list) return;
    const items = Array.from(list.children);
    const index = items.indexOf(item);
    const targetIndex = index + direction;
    if (targetIndex < 0 || targetIndex >= items.length) return;
    const target = items[targetIndex];
    if (direction < 0) list.insertBefore(item, target);
    else list.insertBefore(item, target.nextSibling);
    updateRanks(list);
    item.focus({ preventScroll: true });
    const text = $('.rank-item__text', item)?.textContent.trim() || '';
    liveStatus.textContent = `${text}: место ${item.dataset.rank} из ${items.length}`;
  };

  document.addEventListener('keydown', (event) => {
    const item = event.target.closest?.('.rank-item');
    if (!item || event.target !== item) return;
    if (event.key !== 'ArrowUp' && event.key !== 'ArrowDown') return;
    event.preventDefault();
    moveItem(item, event.key === 'ArrowUp' ? -1 : 1);
  });

  // Pointer sorting is the primary interaction on every device; the native
  // HTML5 drag handlers below remain as a compatibility fallback for synthetic
  // or browser-initiated drag events.
  const coarsePointer = window.matchMedia && window.matchMedia('(pointer: coarse)').matches;
  if (coarsePointer) {
    $$('.rank-item').forEach((item) => { item.draggable = false; });
  }

  let draggedItem = null;

  const clearDragState = () => {
    if (draggedItem) draggedItem.classList.remove('is-dragging');
    $$('.rank-item.is-dragging').forEach((item) => item.classList.remove('is-dragging'));
    document.body.classList.remove('is-dragging');
    draggedItem = null;
  };

  document.addEventListener('dragstart', (event) => {
    if (pointerDrag) {
      event.preventDefault();
      return;
    }
    const item = event.target.closest?.('.rank-item');
    if (!item) return;
    if (item.draggable === false && !event.target.closest?.('.disc-handle')) return;
    draggedItem = item;
    item.classList.add('is-dragging');
    document.body.classList.add('is-dragging');
    if (event.dataTransfer) {
      event.dataTransfer.effectAllowed = 'move';
      try { event.dataTransfer.setData('text/plain', $('.rank-item__text', item)?.textContent || ''); } catch (_) {}
    }
  });

  document.addEventListener('dragover', (event) => {
    if (!draggedItem) return;
    const list = event.target.closest?.('.rank-list');
    if (!list || list !== draggedItem.parentElement) return;
    event.preventDefault();
    if (event.dataTransfer) event.dataTransfer.dropEffect = 'move';

    const over = event.target.closest?.('.rank-item');
    if (over && over !== draggedItem) {
      const rect = over.getBoundingClientRect();
      const before = event.clientY < rect.top + rect.height / 2;
      if (before && over.previousElementSibling !== draggedItem) {
        list.insertBefore(draggedItem, over);
        updateRanks(list);
      } else if (!before && over.nextElementSibling !== draggedItem) {
        list.insertBefore(draggedItem, over.nextSibling);
        updateRanks(list);
      }
    } else if (!over) {
      const items = Array.from(list.children).filter((item) => item !== draggedItem);
      if (!items.length) return;
      const firstRect = items[0].getBoundingClientRect();
      const lastRect = items[items.length - 1].getBoundingClientRect();
      if (event.clientY < firstRect.top && list.firstElementChild !== draggedItem) {
        list.insertBefore(draggedItem, list.firstElementChild);
        updateRanks(list);
      } else if (event.clientY > lastRect.bottom && list.lastElementChild !== draggedItem) {
        list.appendChild(draggedItem);
        updateRanks(list);
      }
    }
  });

  document.addEventListener('drop', (event) => {
    if (!draggedItem) return;
    event.preventDefault();
    clearDragState();
  });
  document.addEventListener('dragend', clearDragState);

  // Pointer sorting: desktop uses the whole row, touch/pen uses the grip so
  // the page can still scroll normally.
  let pointerDrag = null;

  const autoScroll = (clientY) => {
    const edge = 74;
    const speed = 15;
    if (clientY < edge) window.scrollBy(0, -speed);
    else if (clientY > window.innerHeight - edge) window.scrollBy(0, speed);
  };

  const beginPointerDrag = (event) => {
    if (event.button !== undefined && event.button !== 0) return;
    const item = event.target.closest?.('.rank-item');
    if (!item) return;
    if (event.pointerType !== 'mouse' && !event.target.closest?.('.rank-item__grip')) return;
    pointerDrag = {
      item,
      list: item.parentElement,
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      active: false
    };
    event.preventDefault();
    if (event.pointerType === 'mouse') item.focus({ preventScroll: true });
  };

  const movePointerDrag = (event) => {
    if (!pointerDrag || event.pointerId !== pointerDrag.pointerId) return;
    const dx = event.clientX - pointerDrag.startX;
    const dy = event.clientY - pointerDrag.startY;
    if (!pointerDrag.active) {
      if (Math.hypot(dx, dy) < 5) return;
      pointerDrag.active = true;
      pointerDrag.item.classList.add('is-dragging');
      document.body.classList.add('is-dragging');
      try { pointerDrag.item.setPointerCapture(event.pointerId); } catch (_) {}
    }
    event.preventDefault();
    autoScroll(event.clientY);

    const { item, list } = pointerDrag;
    const siblings = Array.from(list.children).filter((child) => child !== item);
    let before = null;
    for (const sibling of siblings) {
      const rect = sibling.getBoundingClientRect();
      if (event.clientY < rect.top + rect.height / 2) {
        before = sibling;
        break;
      }
    }
    if (before) {
      if (item.nextElementSibling !== before) {
        list.insertBefore(item, before);
        updateRanks(list);
      }
    } else if (list.lastElementChild !== item) {
      list.appendChild(item);
      updateRanks(list);
    }
  };

  const endPointerDrag = (event) => {
    if (!pointerDrag || (event && event.pointerId !== pointerDrag.pointerId)) return;
    const item = pointerDrag.item;
    const wasActive = pointerDrag.active;
    if (wasActive && event) event.preventDefault();
    try { item.releasePointerCapture(pointerDrag.pointerId); } catch (_) {}
    item.classList.remove('is-dragging');
    document.body.classList.remove('is-dragging');
    pointerDrag = null;
    if (wasActive) item.focus({ preventScroll: true });
  };

  document.addEventListener('pointerdown', beginPointerDrag, { passive: false });
  document.addEventListener('pointermove', movePointerDrag, { passive: false });
  document.addEventListener('pointerup', endPointerDrag, { passive: false });
  document.addEventListener('pointercancel', endPointerDrag, { passive: false });
  window.addEventListener('blur', () => {
    if (pointerDrag) endPointerDrag(null);
    clearDragState();
  });

  // Initial state
  lists.forEach(updateRanks);
  updateStepUi({ instant: true, scroll: false });
  document.body.dataset.screen = 'intro';
})();
</script>
</body>
</html>
'''

html_doc = html_doc.replace('__TABS__', tabs_html).replace('__QUESTIONS__', questions_html)
open('index.html', 'w', encoding='utf-8').write(html_doc)
print('written', len(html_doc))
