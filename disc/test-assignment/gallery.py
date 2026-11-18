#!/usr/bin/env python3
"""Галерея прогонов: скриншоты тройками, рейтинг 0–100, чек PASS/FAIL,
ссылка на приложение. Без технических деталей — для быстрого визуального
просмотра владельцем.

Запуск: python3 test-assignment/gallery.py
Выход:  reports/GALLERY.html
"""
import base64
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REF = ROOT / "test-assignment" / "reference" / "questions.json"


def collect():
    runs = []
    for mf in sorted(ROOT.glob("models/*/test-assignment/run-*")):
        if not (mf / "run.json").is_file():
            continue
        meta = json.loads((mf / "run.json").read_text(encoding="utf-8"))
        chk = json.loads((mf / "check.json").read_text(encoding="utf-8")) if (mf / "check.json").is_file() else {}
        jf = mf / "judge-tier1.json"
        j = json.loads(jf.read_text(encoding="utf-8")).get("verdict") or {} if jf.is_file() else {}
        ux = (json.loads((mf / "judge-ux.json").read_text(encoding="utf-8")).get("verdict") or {}).get("score") if (mf / "judge-ux.json").is_file() else None
        model = meta.get("model", "?")
        thinking = meta.get("thinking", "?")
        # judge total 0-16 → 0-100
        jt = j.get("total", 0) if j else 0
        try:
            score100 = round(float(jt) / 16 * 100)
        except (TypeError, ValueError):
            score100 = 0
        runs.append({
            "model": model, "dir": str(mf), "run": mf.name,
            "thinking": thinking, "score100": score100,
            "judge_data": j.get("data"), "judge_logic": j.get("logic"),
            "judge_ux": j.get("ux"), "judge_impl": j.get("impl"),
            "ux_vision": ux,
            "check_pass": chk.get("passed", False),
            "data_ok": (chk.get("data") or {}).get("adjectives_found") == 84,
            "types_ok": (chk.get("types") or {}).get("correct") == 96,
            "flow_ok": json.loads((mf / "playthrough.json").read_text(encoding="utf-8")).get("flow_ok", False) if (mf / "playthrough.json").is_file() else False,
            "has_solution": (mf / "index.html").is_file(),
        })
    return runs


def generate(runs):
    by_model = {}
    for r in runs:
        by_model.setdefault(r["model"], []).append(r)
    sorted_models = sorted(by_model.keys(), key=lambda m: -max(x["score100"] for x in by_model[m]))

    cards = []
    for m in sorted_models:
        rs = by_model[m]
        best = max(x["score100"] for x in rs)
        avg = sum(x["score100"] for x in rs) / len(rs)
        model_esc = m.replace("<", "&lt;")
        cards.append(f'<h2>{model_esc} <span class="avg">средний {avg:.0f}/100 · лучший {best:.0f}</span></h2>')
        for r in sorted(rs, key=lambda x: x["run"]):
            status = "pass" if r["check_pass"] else "fail"
            badge = "✓ PASSED" if r["check_pass"] else "✗ FAILED"
            app = Path(r["dir"]) / "index.html"
            app_link = f'<a class="try" href="{app.name}/index.html" target="_blank">▶ открыть</a>' if r["has_solution"] else ""
            score_cls = "hi" if r["score100"] >= 75 else ("mid" if r["score100"] >= 40 else "lo")
            shots = []
            for name in ("start.png", "step.png", "result.png"):
                p = Path(r["dir"]) / "screenshots" / name
                if p.is_file():
                    b64 = base64.b64encode(p.read_bytes()).decode()
                    shots.append(f'<figure><img class="shot" src="data:image/png;base64,{b64}" alt="{name}"><figcaption>{name}</figcaption></figure>')
            cards.append(f"""
<div class="card {score_cls}">
  <div class="head">
    <span class="model">{r["model"]}</span>
    <span class="run">{r["run"]}</span>
    <span class="lvl">{r["thinking"]}</span>
    <span class="score {score_cls}">{r["score100"]}/100</span>
    <span class="badge {status}">{badge}</span>
    {app_link}
  </div>
  <div class="shots">{''.join(shots)}</div>
</div>""")

    return f"""<!DOCTYPE html><html lang="ru"><head><meta charset="utf-8">
<title>DISC — галерея прогонов</title><style>
body{{background:#f0f2f5;margin:0;font-family:system-ui,sans-serif;color:#1a1a2e}}
.container{{max-width:1400px;margin:0 auto;padding:24px}}
h1{{font-size:28px;margin:24px 0 8px}} h2{{font-size:20px;margin:28px 0 10px;border-bottom:2px solid #ddd;padding-bottom:6px}}
.avg{{font-size:13px;font-weight:normal;color:#666;background:#e8eaed;padding:2px 10px;border-radius:12px;vertical-align:middle}}
.card{{background:#fff;border:1px solid #d5d8de;border-radius:12px;padding:16px 20px;margin:14px 0;box-shadow:0 1px 3px rgba(0,0,0,.08)}}
.card.hi{{border-left:4px solid #22c55e}} .card.mid{{border-left:4px solid #f59e0b}} .card.lo{{border-left:4px solid #ef4444}}
.head{{display:flex;align-items:center;gap:12px;margin-bottom:10px;flex-wrap:wrap}}
.model{{font-weight:700;font-size:15px}} .run{{color:#888;font-size:13px}}
.lvl{{color:#555;font-size:12px;background:#eef0f4;padding:2px 8px;border-radius:6px}}
.score{{font-size:22px;font-weight:800;margin-left:auto}}
.score.hi{{color:#16a34a}} .score.mid{{color:#f59e0b}} .score.lo{{color:#dc2626}}
.badge{{font-size:12px;font-weight:700;padding:3px 10px;border-radius:6px}}
.badge.pass{{background:#d4edda;color:#155724}} .badge.fail{{background:#f8d7da;color:#721c24}}
.shots{{display:flex;gap:8px;flex-wrap:wrap;margin:10px 0}}
.shot{{max-width:440px;border:1px solid #ccc;border-radius:8px;cursor:zoom-in;transition:transform .15s}}
.shot:hover{{transform:scale(1.02)}} figure{{margin:0}} figcaption{{font-size:11px;color:#888;text-align:center}}
.try{{display:inline-block;background:#123f8c;color:#fff;padding:8px 18px;border-radius:8px;text-decoration:none;font-weight:600;margin:8px 0;font-size:14px}}
.try:hover{{background:#0e3270}}
#lb{{display:none;position:fixed;inset:0;background:rgba(0,0,0,.92);overflow:auto;z-index:99;cursor:zoom-out}}
#lb img{{max-width:none;display:block;margin:20px auto}}
#lb .hint{{position:fixed;top:12px;right:16px;color:#ddd;font-size:14px}}
</style></head><body><div class="container">
<h1>DISC — галерея прогонов</h1>
{''.join(cards)}
</div>
<div id="lb"><div class="hint">1:1 · Esc — закрыть</div><img alt=""></div>
<script>
document.querySelectorAll('.shot').forEach(im => {{
  im.addEventListener('click', () => {{
    const lb = document.getElementById('lb');
    lb.querySelector('img').src = im.src;
    lb.style.display = 'block'; document.body.style.overflow = 'hidden';
  }});
}});
document.getElementById('lb').addEventListener('click', () => {{
  document.getElementById('lb').style.display = 'none';
  document.body.style.overflow = '';
}});
document.addEventListener('keydown', e => {{
  if (e.key === 'Escape') {{ document.getElementById('lb').style.display = 'none'; document.body.style.overflow = ''; }}
}});
</script></body></html>"""


if __name__ == "__main__":
    runs = collect()
    html = generate(runs)
    out = ROOT / "reports" / "GALLERY.html"
    out.parent.mkdir(exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(f"reports/GALLERY.html: {len(runs)} прогонов, {len(html) // 1024} КБ")
