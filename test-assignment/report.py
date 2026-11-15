#!/usr/bin/env python3
"""Агрегация прогонов и отчёты.

- report.py --run <dir>     — свод одного прогона: <run>/summary.md
                              + строка в scorecard модели;
- report.py --all           — кросс-модельный reports/RUNS.md;
- report.py --html          — reports/RUNS.html (скриншоты инлайном, 1:1);
- report.py --report        — сводный reports/REPORT.html.
"""
from __future__ import annotations

import argparse
import html as html_mod
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(run, name):
    p = Path(run) / name
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else {}


def fmt_dur(s):
    if s is None:
        return "—"
    m, sec = divmod(int(s), 60)
    return f"{m}:{sec:02d}"


def run_row(run):
    run = Path(run)
    meta = load(run, "run.json")
    chk = load(run, "check.json")
    st = load(run, "session-stats.json")
    pt = load(run, "playthrough.json")
    jd = load(run, "judge-tier1.json").get("verdict") or {}
    uxjf = run / "judge-ux.json"
    uxj = json.loads(uxjf.read_text(encoding="utf-8")).get("verdict") or {} if uxjf.is_file() else {}
    model = meta.get("model") or run.parts[-3]
    return {
        "model": model, "run": run.name,
        "thinking": meta.get("thinking"),
        "duration_s": meta.get("duration_s"),
        "exit_code": meta.get("exit_code"),
        "killed": meta.get("killed"),
        "tokens_in": st.get("tokens_in") or 0,
        "tokens_out": st.get("tokens_out") or 0,
        "tool_calls": st.get("tool_calls") or 0,
        "curl_source": st.get("curl_to_source") or 0,
        "files": len(meta.get("files", [])),
        "index_html": (run / "index.html").is_file(),
        "external_pass": (chk.get("external") or {}).get("pass"),
        "data_found": (chk.get("data") or {}).get("adjectives_found"),
        "data_total": (chk.get("data") or {}).get("adjectives_total"),
        "types_correct": (chk.get("types") or {}).get("correct"),
        "types_total": (chk.get("types") or {}).get("total"),
        "smoke_ok": (chk.get("smoke") or {}).get("ok"),
        "check_passed": chk.get("passed"),
        "flow_ok": pt.get("flow_ok"),
        "questions_processed": pt.get("questions_processed"),
        "displayed_match": pt.get("displayed_match"),
        "ux_score": pt.get("ux_score"),
        "judge": {"data": jd.get("data"), "logic": jd.get("logic"),
                  "ux": jd.get("ux"), "impl": jd.get("impl"),
                  "total": jd.get("total")} if jd else None,
        "ux_judge": uxj.get("score") if isinstance(uxj, dict) else None,
        "ux_judge_notes": (uxj.get("notes") or "")[:300] if isinstance(uxj, dict) else "",
    }


def one_run_summary(run):
    r = run_row(run)
    meta = load(Path(run), "run.json")
    lines = [
        f"# Прогон: {r['model']} — {r['run']} (thinking {r['thinking']})",
        "",
        f"- запущен: {meta.get('started_at', '—')}, длительность: {fmt_dur(r['duration_s'])}, "
        f"exit: {r['exit_code']}, убит: {'да' if r['killed'] else 'нет'}",
        f"- контекст/бюджет выхода: {meta.get('context')} / {meta.get('max_tokens')}; "
        f"промпт: v{meta.get('prompt_version')} (sha {meta.get('prompt_sha256')})",
    ]
    if st := load(Path(run), "session-stats.json"):
        lines.append(f"- сессия: {st.get('turns', '—')} ходов, {r['tool_calls']} вызовов инструментов; "
                     f"токены: вх {r['tokens_in']:,} / вых {r['tokens_out']:,}")
        lines.append(f"- сеть в bash: {r['curl_source']} обращений к источнику "
                     f"(curl/wget всего {st.get('bash_with_network', '—')})")
    lines += [
        f"- масштаб параллельной нагрузки (VRAM): "
        f"{', '.join(meta.get('ollama_foreign_models', [])) or 'чисто'}",
        "",
        "## Машинные проверки (check.json)",
        "",
        f"- файлы агента: {r['files']}; index.html: {'есть' if r['index_html'] else 'НЕТ'}",
        f"- самодостаточность (внешние запросы): {'OK' if r['external_pass'] else 'ПРОВАЛ'}",
        f"- данные: прилагательных {r['data_found']}/{r['data_total']}; "
        f"пар текст+тип верно {r['types_correct']}/{r['types_total']}",
        f"- рендер-смоук (headless Chrome): {'OK' if r['smoke_ok'] else 'ПРОВАЛ/не выполнялся'}",
        f"- автопрохождение (поток): {'OK, вопросов ' + str(pt.get('questions_processed')) if (pt := load(Path(run), 'playthrough.json')).get('flow_ok') else '—'}; "
        f"совпадение баллов с планом: {pt.get('displayed_match')}",
        f"- судья яруса 1: " + (f"data {r['judge']['data']}, logic {r['judge']['logic']}, "
                                f"ux {r['judge']['ux']}, impl {r['judge']['impl']} — "
                                f"**{r['judge']['total']}/16**" if r.get('judge') else "не выполнялся"),
        f"- **итог чека: {'PASSED' if r['check_passed'] else 'FAILED'}**",
        "",
    ]
    return "\n".join(lines)


def scorecard_append(model_dir, r):
    sc = Path(model_dir) / "test-assignment" / "scorecard.md"
    row = (f"| {r['run']} | {r['thinking']} | {fmt_dur(r['duration_s'])} "
           f"| {r['tokens_in']:,} | {r['tokens_out']:,} | {r['tool_calls']} "
           f"| {r['curl_source']} | {r['data_found']}/{r['data_total']} "
           f"| {r['types_correct']}/{r['types_total']} "
           f"| {'OK' if r['smoke_ok'] else '—'} "
           f"| {'PASSED' if r['check_passed'] else 'FAILED'} |\n")
    if not sc.is_file():
        sc.write_text(
            "# Scorecard: агентные прогоны копирования DISC-теста\n\n"
            "| прогон | think | длит. | ток. вх | ток. вых | tool | curl→источник | данные | типы | смоук | чек |\n"
            "|---|---|---|---|---|---|---|---|---|---|---|\n",
            encoding="utf-8")
    lines = sc.read_text(encoding="utf-8").splitlines()
    lines = [l for l in lines if not l.startswith(f"| {r['run']} | {r['thinking']} |")]
    lines.append(row.rstrip("\n"))
    sc.write_text("\n".join(lines) + "\n", encoding="utf-8")


def cross_report():
    rows = []
    for mf in sorted(ROOT.glob("models/*/test-assignment/run-*")):
        if (mf / "run.json").is_file():
            rows.append(run_row(mf))
    out = ["# Все прогоны: копирование DISC-теста\n",
           "| модель | прогон | think | длит. | ток. вх | ток. вых | tool | curl→источник | данные | типы | смоук | чек |",
           "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        out.append(
            f"| {r['model']} | {r['run']} | {r['thinking']} | {fmt_dur(r['duration_s'])} "
            f"| {r['tokens_in']:,} | {r['tokens_out']:,} | {r['tool_calls']} "
            f"| {r['curl_source']} | {r['data_found']}/{r['data_total']} "
            f"| {r['types_correct']}/{r['types_total']} "
            f"| {'OK' if r['smoke_ok'] else '—'} "
            f"| {'PASSED' if r['check_passed'] else 'FAILED'} |")
    out.append("\nСравнение с прогнозом (reports/FORECAST.md) — после серии прогонов.")
    return "\n".join(out) + "\n"


def build_report_html():
    """Сводный REPORT.html: методика + прогноз + все прогоны со скриншотами."""
    import base64
    prompt_data = json.loads((ROOT / "test-assignment" / "prompts" / "prompt.json").read_text(encoding="utf-8"))
    prompt_text = prompt_data["prompt"]

    by_model: dict[str, list] = {}
    for mf in sorted(ROOT.glob("models/*/test-assignment/run-*")):
        if (mf / "run.json").is_file():
            r = run_row(mf)
            by_model.setdefault(r["model"], []).append((mf, r))

    # --- галерея: группировка по моделям, балл 0–100, чек, «открыть» ---
    gallery = {}   # model -> list of dicts
    for model, items in by_model.items():
        for run, r in items:
            jd = load(run, "judge-tier1.json").get("verdict") or {}
            score100 = round((jd.get("total") or 0) / 16 * 100)
            has_app = (run / "index.html").is_file()
            shots = []
            for name, cap in (("start.png", "старт"), ("step.png", "вопрос"), ("result.png", "результат")):
                p = run / "screenshots" / name
                if p.is_file():
                    b64 = base64.b64encode(p.read_bytes()).decode()
                    shots.append(f'<figure><img class="shot" src="data:image/png;base64,{b64}" alt="{cap}"><figcaption>{cap}</figcaption></figure>')
            gallery.setdefault(model, []).append({
                "run": r["run"], "thinking": r["thinking"], "score100": score100,
                "check_passed": r["check_passed"], "shots": shots,
                "rel_app": f"../models/{run.parent.parent.name}/test-assignment/{run.name}/index.html" if has_app else None,
            })
    # модели по убыванию лучшего балла, прогоны по имени
    sorted_models = sorted(gallery.keys(), key=lambda m: -max(x["score100"] for x in gallery[m]))
    gallery_html = []
    for m in sorted_models:
        rs = sorted(gallery[m], key=lambda x: x["run"])
        avg = sum(x["score100"] for x in rs) / len(rs)
        best = max(x["score100"] for x in rs)
        gallery_html.append(f'<h2 class="gmodel">{html_mod.escape(m)} <span class="avg">средний {avg:.0f}/100 · лучший {best:.0f}</span></h2>')
        for x in rs:
            cls = "hi" if x["score100"] >= 75 else ("mid" if x["score100"] >= 40 else "lo")
            badge = '<span class="badge pass">✓ PASSED</span>' if x["check_passed"] else '<span class="badge fail">✗ FAILED</span>'
            link = f'<a class="try" href="{x["rel_app"]}" target="_blank">▶ открыть приложение</a>' if x["rel_app"] else '<span class="noapp">нет решения</span>'
            gallery_html.append(f"""
<div class="gcard {cls}">
  <div class="ghead">
    <span class="grun">{html_mod.escape(x["run"])}</span>
    <span class="glvl">think: {html_mod.escape(x["thinking"])}</span>
    <span class="gscore {cls}">{x["score100"]}/100</span>
    {badge}
    {link}
  </div>
  <div class="shots">{''.join(x["shots"])}</div>
</div>""")

    matrix_rows = "".join(f"<tr><td>{m}</td><td>{lvl}</td><td class='st {cls}'>{st}</td></tr>"
                          for m, lvl, st, cls in [
        ("huihui-ai:pi-100k", "off / low / medium (+xhigh проба)", "готово: 9+1 прогонов", "done"),
        ("qwen3.8:27b-pi-100k", "off / low / medium", "готово: 9 прогонов", "done"),
        ("ornith-1.5:35b-ctx100k", "off / on", "готово: 3 прогонов", "done"),
        ("gemma4:26b-pi-100k", "off / on", "готово: 6 прогонов", "done"),
        ("bonsai-2:ctx100k", "off / low / medium", "готово: 9 прогонов", "done"),
        ("muse-glimmer:ctx100k", "off / low / high", "готово: 9 прогонов", "done"),
        ("orcarouter/…:ctx100k", "off / on", "готово: 6 прогонов", "done"),
        ("gemma4:31b-it-qat-pi-100k", "off / on", "готово: 6 прогонов", "done"),
        ("gemma4:e2b-ctx100k", "off / on", "готово: 6 прогонов", "done"),
        ("ornith-1.5:9b", "off / on", "готово: 3 прогонов", "done"),
        ("волна 2 (остальные вариаты) и волна 3 (облака)", "см. AGENTS.md", "по решению", "todo"),
    ])

    return f"""<!DOCTYPE html><html lang=ru><head><meta charset=utf-8><title>disc — сводный отчёт</title>
<style>
body{{background:#f5f6f8;margin:24px;font-family:system-ui;color:#1c2024;max-width:1100px;margin:auto}}
h1,h2,h3{{font-family:system-ui}} h2{{border-bottom:2px solid #c9ced8;padding-bottom:4px;margin-top:36px}}
table{{border-collapse:collapse;background:#fff;width:100%}}
th,td{{border:1px solid #d0d4dd;padding:6px 10px;font-size:14px;text-align:left}}
th{{background:#eef0f4}}
.pass{{color:#0a7d32}} .fail{{color:#b3261e}}
/* --- галерея --- */
.gmodel{{border-bottom:2px solid #c9ced8;padding-bottom:6px;margin-top:40px}}
.avg{{font-size:13px;font-weight:normal;color:#666;background:#e8eaed;padding:2px 10px;border-radius:12px;vertical-align:middle;margin-left:8px}}
.gcard{{background:#fff;border:1px solid #d5d8de;border-radius:12px;padding:16px 20px;margin:14px 0;box-shadow:0 1px 3px rgba(0,0,0,.08)}}
.gcard.hi{{border-left:4px solid #22c55e}} .gcard.mid{{border-left:4px solid #f59e0b}} .gcard.lo{{border-left:4px solid #ef4444}}
.ghead{{display:flex;align-items:center;gap:12px;flex-wrap:wrap}}
.grun{{font-weight:700;font-size:15px}} .glvl{{color:#555;font-size:12px;background:#eef0f4;padding:2px 8px;border-radius:6px}}
.gscore{{font-size:22px;font-weight:800;margin-left:auto}}
.gscore.hi{{color:#16a34a}} .gscore.mid{{color:#f59e0b}} .gscore.lo{{color:#dc2626}}
.badge{{font-size:12px;font-weight:700;padding:3px 10px;border-radius:6px}}
.badge.pass{{background:#d4edda;color:#155724}} .badge.fail{{background:#f8d7da;color:#721c24}}
.try{{display:inline-block;background:#123f8c;color:#fff;padding:8px 18px;border-radius:8px;text-decoration:none;font-weight:600;font-size:14px}}
.try:hover{{background:#0e3270}} .noapp{{color:#999;font-size:13px}}
figure{{margin:0}} figcaption{{font-size:11px;color:#888;text-align:center}}
.shot{{max-width:440px;border:1px solid #ccc;border-radius:8px;cursor:zoom-in;transition:transform .15s}}
.shot:hover{{transform:scale(1.02)}}
#lb{{display:none;position:fixed;inset:0;background:rgba(0,0,0,.92);overflow:auto;z-index:99;cursor:zoom-out}}
#lb img{{max-width:none;display:block;margin:20px auto}}
#lb .hint{{position:fixed;top:12px;right:16px;color:#ddd;font-size:14px}}
</style>
<h1>disc: сводный отчёт — тестирование копирования DISC-теста</h1>
<p class="small">Обновлено 2026-11-15. Полная методика: reports/METHOD.md · конвенции: AGENTS.md ·
сестринский workspace: ~/MyProjects/Models. Все скриншоты кликабельны (1:1).</p>
<div class="toc"><a href="#method">Методика</a><a href="#prompt">Промпт дословно</a><a href="#matrix">Матрица моделей</a><a href="#forecast">Прогноз</a><a href="#runs">Прогоны и результаты</a><a href="#limits">Ограничения</a></div>

<h2 id="method">1. Методика</h2>
<h3>1.1. Задание и протокол</h3>
<p>Модель работает <b>агентом в pi</b> с инструментами по умолчанию (bash с сетью, файлы).
Она получает <b>только текст задания и ссылку на источник</b> — и сама изучает страницу,
сама скачивает исходники, сама извлекает данные и алгоритм подсчёта, сама строит решение.
Эталон (снятый с оригинала) и методология агенту недоступны.</p>
<p>Серия: <b>3 прогона на (модель × уровень мышления)</b>, уровни off/low/default (булевы шкалы — off/on),
облака — reasoning_effort low. Прогоны изолированы, seed не фиксируется. Стандарт — минимум 3.</p>

<h3>1.2. Запуск pi (дословно)</h3>
<pre>pi -p \
  --session-dir &lt;run-XX&gt;/pi-session \\
  --model &lt;тег&gt; \\
  --thinking &lt;off|low|medium&gt; \\
  "&lt;текст задания&gt;"</pre>
<p>env: <code>PI_CODING_AGENT_DIR=&lt;tmp&gt;/pi-home</code> (изолированный конфиг),
<code>PI_OFFLINE=1</code> (сам pi в сеть не ходит — сеть использует только инструмент bash агента, например <code>curl</code> к источнику).
<code>models.json</code> собирается на лету из фактической шкалы модели (<code>/api/show</code> →
<code>thinkingLevelMap</code>); maxTokens 8192 → 32768 для моделей с энергичным максимумом
(xhigh/max в шкале); контекст 102400 (теги -pi-100k/-ctx100k). Рабочая директория —
временный каталог <b>вне репозитория</b>. pi — лидер process group, таймаут 3600 с;
фоновый наблюдатель /api/ps фиксирует конкуренцию за VRAM.</p>

<h2 id="prompt">2. Промпт дословно (v3)</h2>
<pre>{prompt_text}</pre>
<p class="small">История версий: v1 (готовые эталонные данные) и v2 (встроенные исходники) — deprecated.
Файл: test-assignment/prompts/prompt.json.</p>

<h2 id="matrix">3. Матрица моделей (волна 1)</h2>
<table><tr><th>модель</th><th>уровни</th><th>статус</th></tr>{matrix_rows}</table>

<h2 id="forecast">4. Прогноз (предрегистрация 2026-11-14, reports/FORECAST.md)</h2>
<p>Вопрос: переносится ли рейтинг карты знаний (Всего ru, вопросник PHP) на агентную задачу?</p>
<table><tr><th>место</th><th>прогноз A «слепой перенос рейтинга»</th><th>прогноз B «карта + агентные поправки» (основной)</th></tr>
<tr><td>1</td><td>huihui (low/medium)</td><td><b>huihui (low)</b></td></tr>
<tr><td>2</td><td>orca (on)</td><td><b>qwen3.8 (low)</b></td></tr>
<tr><td>3</td><td>qwen3.8 (low/medium)</td><td><b>orca (on)</b></td></tr>
<tr><td>4</td><td>ornith (on)</td><td><b>muse-glimmer (high)</b> — вне карты</td></tr>
<tr><td>5</td><td>ornith (on)</td><td><b>ornith (on)</b> — карта 88.6, агентный трек провальный</td></tr>
<tr><td>6</td><td>—</td><td><b>gemma4-26b (on)</b> — вне карты, бимодальность</td></tr>
<tr><td>7</td><td>—</td><td><b>bonsai (low/off)</b> — карта 87.0, агентный трек — дно (ключевой кейс)</td></tr>
</table>
<p class="small">Проверка после серии: Spearman рейтинга «Всего»/«Глубины» с фактическим итогом,
совпадение топ-1, кейс bonsai.</p>

<h2 id="runs">5. Прогоны и результаты</h2>
<p>Каждая карточка — прогон: скриншоты (клик — 1:1), итоговый балл 0–100, статус чека, ссылка на приложение.
Модели отсортированы по убыванию лучшего балла.</p>
{''.join(gallery_html) if gallery_html else '<p>прогонов пока нет</p>'}
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
</script>

<h2 id="limits">6. Ограничения и политика</h2>
<ul>
<li>симуляция drag&drop невоспроизводима на произвольных реализациях (Pointer Events,
откат SortableJS, скролл-контейнеры) — автопрохождение проверяет поток и рендер,
логику подсчёта проверяет судья по коду; показанные баллы — справочно;</li>
<li>рабочие файлы агента (скачанные исходники, тест-скрипты) — не недостаток и не удаляются;</li>
<li>известные опечатки оригинала (латинская «c») — их исправление плюс модели,
чекер фиксирует факт (known_quirk_normalized);</li>
<li>судья яруса 1 — LLM (glm-5.3-flash, не кандидат); ярус 2 — владелец/сильный судья;</li>
<li>нестандартные события (таймаут, конкуренция VRAM, эскалация thinking) видны в run.json.</li>
</ul>
</html>"""


    import base64
    cards = []
    for run in runs:
        r = run_row(run)
        meta = load(Path(run), "run.json")
        chk = load(Path(run), "check.json")
        jd = load(Path(run), "judge-tier1.json").get("verdict") or {}
        esc = html_mod.escape
        jhtml = (f'<b>судья ярус 1:</b> data {jd.get("data")} · logic {jd.get("logic")} · '
                 f'ux {jd.get("ux")} · impl {jd.get("impl")} — <b>{jd.get("total")}/16</b>'
                 f'<div class="notes">{esc((jd.get("notes") or ""))[:700]}</div>'
                 f'<div class="notes">{esc((jd.get("examples") or ""))[:700]}</div>' if jd else "судья: не выполнялся")
        shots = []
        for name, cap in (("start.png", "старт"), ("step.png", "вопрос"), ("result.png", "результат")):
            p = Path(run) / "screenshots" / name
            if p.is_file():
                b64 = base64.b64encode(p.read_bytes()).decode()
                shots.append(f'<figure><img class="shot" src="data:image/png;base64,{b64}" alt="{cap}"><figcaption>{cap} (клик — 1:1)</figcaption></figure>')
        cards.append(f"""
<div class="card">
  <h3>{r['model']} · think {r['thinking']} · <span class="run">{r['run']}</span></h3>
  <div class="meta">время {fmt_dur(r['duration_s'])} · exit {r['exit_code']} · токены вх {r['tokens_in']:,}/вых {r['tokens_out']:,} ·
  инструментов {r['tool_calls']} · curl к источнику {r['curl_source']} · контекст {meta.get('context')}/выход {meta.get('max_tokens')}</div>
  <div class="checks">чек: <b class="{'pass' if r['check_passed'] else 'fail'}">{'PASSED' if r['check_passed'] else 'FAILED'}</b> ·
  данные {r['data_found']}/{r['data_total']} · пары текст+тип {r['types_correct']}/{r['types_total']} ·
  внешние запросы: {'нет' if r['external_pass'] else 'ЕСТЬ'} · рендер: {'OK' if r['smoke_ok'] else '—'} ·
  автопрохождение: {'OK' if r['flow_ok'] else '—'} · совпадение баллов: {r['displayed_match']}</div>
  <div class="shots">{''.join(shots)}</div>
  <div class="judge">{jhtml}</div>
</div>""")

    matrix_rows = "".join(f"<tr><td>{m}</td><td>{lvl}</td><td class='st {cls}'>{st}</td></tr>"
                          for m, lvl, st, cls in [
        ("huihui-ai:pi-100k", "off / low / medium (+xhigh проба)", "готово: 9+1 прогонов", "done"),
        ("qwen3.8:27b-pi-100k", "off / low / medium", "готово: 9 прогонов", "done"),
        ("ornith-1.5:35b-ctx100k", "off / on", "готово: 3 прогонов", "done"),
        ("gemma4:26b-pi-100k", "off / on", "готово: 6 прогонов", "done"),
        ("bonsai-2:ctx100k", "off / low / medium", "готово: 9 прогонов", "done"),
        ("muse-glimmer:ctx100k", "off / low / high", "готово: 9 прогонов", "done"),
        ("orcarouter/…:ctx100k", "off / on", "готово: 6 прогонов", "done"),
        ("gemma4:31b-it-qat-pi-100k", "off / on", "готово: 6 прогонов", "done"),
        ("gemma4:e2b-ctx100k", "off / on", "готово: 6 прогонов", "done"),
        ("ornith-1.5:9b", "off / on", "готово: 3 прогонов", "done"),
        ("волна 2 (остальные вариаты) и волна 3 (облака)", "см. AGENTS.md", "по решению", "todo"),
    ])

    return f"""<!DOCTYPE html><html lang=ru><head><meta charset=utf-8><title>disc — прогоны</title>
<style>
body{{background:#f5f6f8;margin:24px;font-family:system-ui;color:#1c2024;max-width:1100px;margin:auto}}
h1,h2,h3{{font-family:system-ui}} h2{{border-bottom:2px solid #c9ced8;padding-bottom:4px;margin-top:36px}}
table{{border-collapse:collapse;background:#fff;width:100%}}
th,td{{border:1px solid #d0d4dd;padding:6px 10px;font-size:14px;text-align:left}}
th{{background:#eef0f4}}
.pass{{color:#0a7d32}} .fail{{color:#b3261e}}
img.shot{{max-width:340px;border:1px solid #ccc;border-radius:6px}}
</style>
<h1>disc: прогоны копирования DISC-теста</h1>
{''.join(cards)}
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", help="каталог прогона: summary + scorecard")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--html", action="store_true")
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args()

    if args.run:
        run = Path(args.run).resolve()
        r = run_row(run)
        (run / "summary.md").write_text(one_run_summary(run), encoding="utf-8")
        model_dir = ROOT / "models" / r["model"].replace(":", "-").replace("/", "-")
        scorecard_append(model_dir, r)
        print(f"summary.md и scorecard обновлены ({run})")
    if args.all:
        p = ROOT / "reports" / "RUNS.md"
        p.write_text(cross_report(), encoding="utf-8")
        print(f"reports/RUNS.md обновлён ({p})")
    if args.html:
        runs = sorted(ROOT.glob("models/*/test-assignment/run-*"))
        runs = [r for r in runs if (r / "run.json").is_file()]
        p = ROOT / "reports" / "RUNS.html"
        p.write_text(html_report(runs), encoding="utf-8")
        print(f"reports/RUNS.html обновлён ({p})")
    if args.report:
        p = ROOT / "reports" / "REPORT.html"
        p.write_text(build_report_html(), encoding="utf-8")
        print(f"reports/REPORT.html обновлён ({p})")
    if not args.run and not args.all and not args.html:
        print("укажите --run <dir> и/или --all и/или --html")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
