#!/usr/bin/env python3
"""Агрегация прогонов и отчёты.

- report.py --run <dir>     — свод одного прогона: <run>/summary.md
                              + строка в scorecard модели;
- report.py --all           — кросс-модельный reports/RUNS.md;
- report.py --html          — reports/RUNS.html (скриншоты инлайном, 1:1 по клику);
- report.py --report        — сводный reports/REPORT.html
                              (методика + промпт + прогноз + галерея + прогоны).

Источники: run.json, check.json, session-stats.json, playthrough.json,
judge-tier1.json, judge-ux.json.
"""
from __future__ import annotations

import argparse
import html as html_mod
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(run: Path, name: str) -> dict:
    p = run / name
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else {}


def fmt_dur(s: float | None) -> str:
    if s is None:
        return "—"
    m, sec = divmod(int(s), 60)
    return f"{m}:{sec:02d}"


def run_row(run: Path) -> dict:
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


def one_run_summary(run: Path) -> str:
    r = run_row(run)
    meta = load(run, "run.json")
    pt = load(run, "playthrough.json")
    st = load(run, "session-stats.json")
    lines = [
        f"# Прогон: {r['model']} — {r['run']} (thinking {r['thinking']})",
        "",
        f"- запущен: {meta.get('started_at', '—')}, длительность: {fmt_dur(r['duration_s'])}, "
        f"exit: {r['exit_code']}, убит: {'да' if r['killed'] else 'нет'}",
        f"- контекст/бюджет выхода: {meta.get('context')} / {meta.get('max_tokens')}; "
        f"промпт: v{meta.get('prompt_version')} (sha {meta.get('prompt_sha256')})",
    ]
    if st:
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
        f"- автопрохождение (поток): {'OK, вопросов ' + str(pt.get('questions_processed')) if pt.get('flow_ok') else '—'}; "
        f"совпадение баллов с планом: {pt.get('displayed_match')}",
        f"- судья яруса 1: " + (f"data {r['judge']['data']}, logic {r['judge']['logic']}, "
                                f"ux {r['judge']['ux']}, impl {r['judge']['impl']} — "
                                f"**{r['judge']['total']}/16**" if r.get('judge') else "не выполнялся"),
        f"- **итог чека: {'PASSED' if r['check_passed'] else 'FAILED'}**",
        "",
    ]
    return "\n".join(lines)


def scorecard_append(model_dir: Path, r: dict) -> None:
    sc = model_dir / "test-assignment" / "scorecard.md"
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


def cross_report() -> str:
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


def html_report(runs: list[Path]) -> str:
    """Визуальный отчёт RUNS.html: скриншоты инлайном, чеки, судья — 1:1 по клику."""
    import base64
    cards = []
    for run in runs:
        r = run_row(run)
        meta = load(run, "run.json")
        jd = load(run, "judge-tier1.json").get("verdict") or {}
        esc = html_mod.escape
        jhtml = (f'<b>судья ярус 1:</b> data {jd.get("data")} · logic {jd.get("logic")} · '
                 f'ux {jd.get("ux")} · impl {jd.get("impl")} — <b>{jd.get("total")}/16</b>'
                 f'<div class="notes">{esc((jd.get("notes") or ""))[:700]}</div>'
                 f'<div class="notes">{esc((jd.get("examples") or ""))[:700]}</div>' if jd else "судья: не выполнялся")
        shots = []
        for name, cap in (("start.png", "старт"), ("step.png", "вопрос"), ("result.png", "результат")):
            p = run / "screenshots" / name
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
.pass{{color:#0a7d32}} .fail{{color:#b3261e}} .st.done{{color:#0a7d32;font-weight:bold}} .st.todo{{color:#8a6d1a}}
img.shot{{max-width:340px;border:1px solid #ccc;border-radius:6px}}
.shots{{display:flex;gap:10px;flex-wrap:wrap;margin-top:8px}}
</style>
<div id="lb"><div class="hint">масштаб 1:1 · прокрутка — панорама · Esc или клик — закрыть</div><img alt=""></div>
<script>
const lb = document.getElementById('lb'); const lbImg = lb.querySelector('img');
const openLb = (src) => {{ lbImg.src = src; lb.style.display = 'block'; document.body.style.overflow = 'hidden'; }};
const closeLb = () => {{ lb.style.display = 'none'; lbImg.src = ''; document.body.style.overflow = ''; }};
document.addEventListener('click', (e) => {{
  const im = e.target.closest('img.shot');
  if (im) {{ openLb(im.src); return; }}
  if (e.target.closest('#lb')) closeLb();
}});
document.addEventListener('keydown', (e) => {{ if (e.key === 'Escape') closeLb(); }});
</script>
<h1>disc: прогоны копирования DISC-теста</h1>
{''.join(cards)}
"""


def build_report_html() -> str:
    """Сводный REPORT.html: методика + прогноз + все прогоны со скриншотами."""
    prompt_data = json.loads((ROOT / "test-assignment" / "prompts" / "prompt.json").read_text(encoding="utf-8"))
    prompt_text = prompt_data["prompt"]

    by_model: dict[str, list] = {}
    for mf in sorted(ROOT.glob("models/*/test-assignment/run-*")):
        if (mf / "run.json").is_file():
            r = run_row(mf)
            by_model.setdefault(r["model"], []).append((mf, r))

    cards = []
    for model, items in by_model.items():
        for run, r in items:
            meta = load(run, "run.json")
            chk = load(run, "check.json")
            jd = load(run, "judge-tier1.json").get("verdict") or {}
            esc = html_mod.escape
            jhtml = (f'<b>судья ярус 1:</b> data {jd.get("data")} · logic {jd.get("logic")} · '
                     f'ux {jd.get("ux")} · impl {jd.get("impl")} — <b>{jd.get("total")}/16</b>'
                     f'<div class="notes">{esc((jd.get("notes") or ""))[:700]}</div>'
                     f'<div class="notes">{esc((jd.get("examples") or ""))[:700]}</div>' if jd else "судья: не выполнялся")
            shots = []
            for name, cap in (("start.png", "старт"), ("step.png", "вопрос"), ("result.png", "результат")):
                p = run / "screenshots" / name
                if p.is_file():
                    b64 = base64.b64encode(p.read_bytes()).decode()
                    shots.append(f"<figure><img class=\"shot\" src=\"data:image/png;base64,{b64}\" alt=\"{cap}\"><figcaption>{cap} (клик — 1:1)</figcaption></figure>")
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

    return f"""<!DOCTYPE html><html lang=ru><head><meta charset=utf-8><title>disc — сводный отчёт</title>
<style>
body{{background:#f5f6f8;margin:24px;font-family:system-ui;color:#1c2024;max-width:1100px;margin:auto}}
h1,h2,h3{{font-family:system-ui}} h2{{border-bottom:2px solid #c9ced8;padding-bottom:4px;margin-top:36px}}
table{{border-collapse:collapse;background:#fff;width:100%}}
th,td{{border:1px solid #d0d4dd;padding:6px 10px;font-size:14px;text-align:left}}
th{{background:#eef0f4}}
code,pre{{font-family:ui-monospace,Consolas,monospace;font-size:13px}}
pre{{background:#101418;color:#d6e2f0;padding:12px;border-radius:8px;overflow:auto;white-space:pre-wrap}}
.card{{border:1px solid #d0d4dd;border-radius:10px;padding:14px;margin:14px 0;background:#fff}}
.card h3{{margin:0 0 6px}} .meta{{color:#555;font-size:13px}} .checks{{margin:8px 0;font-size:14px}}
.pass{{color:#0a7d32}} .fail{{color:#b3261e}} .st.done{{color:#0a7d32;font-weight:bold}} .st.todo{{color:#8a6d1a}}
.shots{{display:flex;gap:10px;flex-wrap:wrap;margin-top:8px}}
img.shot{{max-width:340px;border:1px solid #ccc;border-radius:6px;cursor:zoom-in}}
figure{{margin:0}} figcaption{{font-size:12px;color:#666}}
.judge{{margin-top:8px;font-size:13px;background:#f2f6ff;border-radius:8px;padding:8px}}
.notes{{color:#333;margin-top:4px}}
.toc a{{margin-right:14px}}
#lb{{display:none;position:fixed;inset:0;background:rgba(10,12,16,.92);overflow:auto;z-index:99;cursor:zoom-out}}
#lb img{{max-width:none;display:block;margin:16px auto;cursor:zoom-out}}
#lb .hint{{position:fixed;top:10px;right:16px;color:#cfd3da;font-family:system-ui;font-size:13px}}
.small{{font-size:13px;color:#555}}
</style>
<div id="lb"><div class="hint">масштаб 1:1 · прокрутка — панорама · Esc или клик — закрыть</div><img alt=""></div>
<script>
const lb = document.getElementById('lb'); const lbImg = lb.querySelector('img');
const openLb = (src) => {{ lbImg.src = src; lb.style.display = 'block'; document.body.style.overflow = 'hidden'; }};
const closeLb = () => {{ lb.style.display = 'none'; lbImg.src = ''; document.body.style.overflow = ''; }};
document.addEventListener('click', (e) => {{
  const im = e.target.closest('img.shot');
  if (im) {{ openLb(im.src); return; }}
  if (e.target.closest('#lb')) closeLb();
}});
document.addEventListener('keydown', (e) => {{ if (e.key === 'Escape') closeLb(); }});
</script>
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
<pre>pi -p \\
  --session-dir &lt;run-XX&gt;/pi-session \\\\
  --model &lt;тег&gt; \\\\
  --thinking &lt;off|low|medium&gt; \\\\
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
<h3>Сводка всех прогонов</h3>
<table style="font-size:13px"><tr><th>модель</th><th>прогон</th><th>think</th><th>время</th><th>ток. вх/вых</th><th>чек</th><th>данные</th><th>типы</th><th>поток</th><th>судья</th><th></th></tr>
{''.join(sum_rows)}
</table>
<h3>Лестницы по моделям (средний балл судьи на уровень)</h3>
<table><tr><th>модель</th><th>уровень</th><th>средний /16</th><th>прогоны</th></tr>
{''.join(ladder_rows)}
</table>
<p class="small">Карточки ниже свёрнуты — клик по строке открывает детали, скриншоты (клик — 1:1) и вердикт судьи. Ссылки «открыть ▸» ведут на живое приложение прогона.</p>
{''.join(cards) if cards else '<p>прогонов пока нет</p>'}

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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", help="каталог прогона: summary + scorecard")
    ap.add_argument("--all", action="store_true", help="кросс-модельный reports/RUNS.md по всем найденным прогонам models/*/test-assignment/run-*")
    ap.add_argument("--html", action="store_true", help="визуальный reports/RUNS.html (скриншоты инлайном)")
    ap.add_argument("--report", action="store_true", help="сводный reports/REPORT.html (методика+прогноз+прогоны)")
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
    if not args.run and not args.all and not args.html:
        print("укажите --run <dir> и/или --all и/или --html")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
