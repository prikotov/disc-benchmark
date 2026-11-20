#!/usr/bin/env python3
"""Сводный отчёт по анкете DISC (ru + en): reports/QUIZ.md + reports/QUIZ.html.

Читает models/*/quiz/run-*/run.json (ru) и models/*/quiz-en/run-*/run.json
(en), агрегирует по (модель × язык × уровень): баллы, стабильность, json_ok,
токены, время, p_correct для decision-моделей; матрицы по вопросам на каждый
язык, сложность вопросов, точность по цветам и сравнение ru vs en.

Запуск:
    python3 quiz/report.py            # QUIZ.md + QUIZ.html
    python3 quiz/report.py --print    # ещё и таблицу в stdout
"""
from __future__ import annotations

import argparse
import html as _html
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
REPORTS = ROOT / "reports"
RUNS_GLOBS = {"ru": "models/*/quiz/run-*/run.json",
              "en": "models/*/quiz-en/run-*/run.json"}

PROMPT_RU = json.loads((HERE / "prompts" / "prompt.json").read_text(encoding="utf-8"))["prompt"]
PROMPT_EN = json.loads((HERE.parent / "quiz-en" / "prompts" / "prompt.json").read_text(
    encoding="utf-8"))["prompt"]
REQ_JSON = json.dumps({
    "model": "<тег модели>",
    "messages": [{"role": "user", "content": "<пользовательский промпт — см. ниже>"}],
    "stream": False,
    "keep_alive": "10m",
    "options": {"num_ctx": 65536, "num_predict": 32768},
    "think": "<off | low | medium | high | xhigh — по модели>",
}, ensure_ascii=False, indent=2)
PROMPT_RU_H = _html.escape(PROMPT_RU)
PROMPT_EN_H = _html.escape(PROMPT_EN)
REQ_JSON_H = _html.escape(REQ_JSON)
KEYS = {lang: json.loads((HERE.parent / f"quiz{'' if lang == 'ru' else '-en'}"
                          / "reference" / f"key{'' if lang == 'ru' else '-en'}.json")
                         .read_text(encoding="utf-8")) for lang in ("ru", "en")}
LEVEL_ORDER = {m["folder"]: m.get("doc_levels") or [None]
               for m in json.loads((HERE / "models.json").read_text(encoding="utf-8"))["models"]}
# сопоставление вопросов ru <-> en (проверено по текстам 2026-11-17):
# en 1..11 = ru 1..11; ru 12 (болезненная реакция на критику) не имеет
# en-аналога; en 12..23 = ru 13..24
RU_TO_EN = {n: (n if n <= 11 else n - 1 if n >= 13 else None) for n in range(1, 25)}
COLOR_OF = {"Красный": "D", "Желтый": "I", "Зеленый": "S", "Синий": "C",
            "Red": "D", "Yellow": "I", "Green": "S", "Blue": "C"}
COLOR_TITLE = {"D": "красный (D)", "I": "жёлтый (I)", "S": "зелёный (S)", "C": "синий (C)"}
LANG_TOTAL = {"ru": 24, "en": 23}


def load_runs() -> list[dict]:
    runs = []
    for lang, pattern in RUNS_GLOBS.items():
        for p in sorted(ROOT.glob(pattern)):
            try:
                r = json.loads(p.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                print(f"  ! битый run.json: {p}", file=sys.stderr)
                continue
            for x in r["verdict"]["per_question"]:
                if not isinstance(x.get("correct"), bool):
                    x["correct"] = x.get("verdict") == "correct"
            r["_lang"] = r.get("lang") or lang
            r["_dir"] = str(p.parent)
            runs.append(r)
    return runs


def group_key(r: dict) -> tuple[str, str, str]:
    lvl = r["thinking"]["requested"]
    return r["folder"], r["_lang"], ("decision" if lvl is None else str(lvl))


def sort_key(g: tuple[str, str, str]):
    """Сортировка по имени модели (алфавит), затем язык (ru раньше en),
    затем уровень — в порядке документированной лестницы."""
    folder, lang, lvl = g
    dl = LEVEL_ORDER.get(folder) or [None]
    li = dl.index(None if lvl == "decision" else lvl) if lvl in dl or lvl == "decision" else 99
    return folder.lower(), 0 if lang == "ru" else 1, li


def folders_sorted(groups: dict) -> list[str]:
    return sorted({g[0] for g in groups}, key=lambda f: f.lower())


def agg_group(runs: list[dict]) -> dict:
    n = len(runs)
    scores = [r["verdict"]["score"] for r in runs]
    provider = runs[0]["provider"]
    total = LANG_TOTAL[runs[0]["_lang"]]
    vectors = []
    for r in runs:
        pq = r["verdict"]["per_question"]
        if provider == "decision":
            vec = tuple(x.get("chosen") for x in pq)
        else:
            vec = tuple(str(x.get("answer", "")).strip().lower() for x in pq)
        vectors.append(vec)
    distinct = len(set(vectors))
    pairs = [vectors[i] == vectors[j]
             for i in range(n) for j in range(i + 1, n)]
    identical = (sum(pairs) / len(pairs)) if pairs else None
    flags = defaultdict(int)
    for r in runs:
        st = r["verdict"].get("stats") or {}
        for k, v in st.items():
            flags[k] += v
    toks = defaultdict(list)
    for r in runs:
        u = r.get("usage") or {}
        for k in ("prompt_eval_count", "eval_count", "input_tokens", "output_tokens",
                  "prompt_tokens", "completion_tokens"):
            if u.get(k):
                toks[k].append(u[k])
    mean = lambda k: round(sum(toks[k]) / len(toks[k])) if toks.get(k) else None
    pc = [r["verdict"].get("p_correct_mean") for r in runs
          if r["verdict"].get("p_correct_mean") is not None]
    jok = (sum(1 for r in runs if (r.get("parsed") or {}).get("json_ok")) / n) \
        if n and provider in ("chat", "cloud") else None
    return {
        "n": n, "provider": provider,
        "mean": sum(scores) / n if n else 0,
        "min": min(scores) if scores else 0, "max": max(scores) if scores else 0,
        "distinct": distinct, "identical": identical,
        "unparsed": flags["unparsed"], "skipped": flags["skipped"],
        "ambiguous": flags["ambiguous"], "near": flags["near"],
        "json_ok": jok,
        "tok_in": mean("prompt_eval_count") or mean("input_tokens") or mean("prompt_tokens"),
        "tok_out": mean("eval_count") or mean("output_tokens") or mean("completion_tokens"),
        "dur": round(sum(r.get("duration_s") or 0 for r in runs) / n, 1) if n else None,
        "p_correct": round(sum(pc) / len(pc), 3) if pc else None,
        "contention": any(r.get("ollama_contention") for r in runs),
        "runs": runs, "total": total,
    }


def pct_lang(a: dict) -> str:
    return f"{a['mean'] / a['total'] * 100:.0f}%"


def heat_color(rate: float) -> str:
    h = int(8 + 116 * max(0.0, min(1.0, rate)))
    return f"background:hsl({h},72%,86%)"


def matrix_rows(groups: dict, lang: str) -> dict:
    out = {}
    for g, a in groups.items():
        if g[1] != lang:
            continue
        per_q = defaultdict(lambda: [0, 0])
        for r in a["runs"]:
            for x in r["verdict"]["per_question"]:
                per_q[x["n"]][0] += 1 if x.get("correct") else 0
                per_q[x["n"]][1] += 1
        out[g] = [((okc / tot) if tot else None) for okc, tot in
                  (per_q[q["n"]] for q in KEYS[lang]["questions"])]
    return out


def lang_best(groups: dict, folder: str, lang: str) -> dict | None:
    gs = [g for g in groups if g[0] == folder and g[1] == lang]
    if not gs:
        return None
    return max((groups[g] for g in gs), key=lambda a: a["mean"])


def lang_level(groups: dict, folder: str, lang: str, best: dict) -> str:
    for g, a in groups.items():
        if g[0] == folder and g[1] == lang and a is best:
            return g[2]
    return "?"


def norm_answer(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^0-9a-zа-яё ]+", " ",
                  str(s).lower().replace("ё", "е"))).strip()[:48]


def compute_problems(groups: dict) -> list:
    """Вопросы с суммарной долей верных <50% (ru + en) + статистика по группам."""
    stats = {}  # (n_ru, lang) -> статистика вопроса на языке
    for q in KEYS["ru"]["questions"]:
        n_ru = q["n"]
        for lang, lookup in (("ru", n_ru), ("en", RU_TO_EN[n_ru])):
            if lookup is None:
                continue
            ok = tot = 0
            perfect = []
            dist = Counter()
            raw = {}
            for g, rs in groups.items():
                if g[1] != lang:
                    continue
                g_ok = g_tot = 0
                for r in rs:
                    x = r["verdict"]["per_question"][lookup - 1]
                    g_tot += 1
                    g_ok += bool(x.get("correct"))
                    ans = (x.get("chosen") if r["provider"] == "decision"
                           else x.get("answer")) or "∅"
                    k = norm_answer(ans)
                    dist[k] += 1
                    raw[k] = str(ans).strip()[:60]
                tot += g_tot
                ok += g_ok
                if g_tot and g_ok == g_tot:
                    perfect.append(f"{g[0]} {g[1]}@{g[2]}")
            stats[(n_ru, lang)] = {"ok": ok, "tot": tot,
                                   "rate": ok / tot if tot else None,
                                   "perfect": perfect, "dist": dist, "raw": raw}
    problems = []
    for q in KEYS["ru"]["questions"]:
        s_ru = stats.get((q["n"], "ru"))
        s_en = stats.get((q["n"], "en"))
        ok = (s_ru["ok"] if s_ru else 0) + (s_en["ok"] if s_en else 0)
        tot = (s_ru["tot"] if s_ru else 0) + (s_en["tot"] if s_en else 0)
        if tot and ok / tot < 0.5:
            problems.append((q, s_ru, s_en, ok / tot))
    problems.sort(key=lambda x: x[3])
    return problems


def build_html(groups: dict, runs: list[dict], out: Path, failed_counts: dict | None = None,
               problems: list | None = None) -> None:
    total_runs = len(runs)
    parts = []
    parts.append("""<!doctype html><html lang="ru"><head><meta charset="utf-8">
<title>disc quiz: анкета DISC — своды (ru + en)</title><style>
body{font:14px/1.45 -apple-system,'Segoe UI',Roboto,sans-serif;margin:24px;color:#1c2733;background:#fafbfc}
h1{font-size:22px;margin:0 0 4px}h2{font-size:17px;margin:28px 0 8px}
.sub{color:#5a6b7b;margin-bottom:18px}
table{border-collapse:collapse;margin:10px 0;background:#fff}
th,td{border:1px solid #d5dde5;padding:4px 9px;text-align:left;vertical-align:top}
th{background:#eef2f6;font-weight:600}
td.num,th.num{text-align:right}
.bar{height:9px;background:#dfe7ee;border-radius:5px;overflow:hidden;width:120px;display:inline-block;vertical-align:middle}
.bar>div{height:100%;background:#2e7d32}
.model{background:#fff;border:1px solid #d5dde5;border-radius:8px;padding:10px 14px;margin:12px 0;max-width:920px}
.model h3{margin:2px 0 6px;font-size:15px}
.muted{color:#5a6b7b;font-size:12px}
.warn{background:#fff4e5;border:1px solid #f0c987;border-radius:6px;padding:6px 12px;margin:10px 0;max-width:920px}
a{color:#0b62a4;text-decoration:none}a:hover{text-decoration:underline}
code{background:#eef2f6;border-radius:3px;padding:0 4px}
table.matrix{font-size:12px}
table.matrix td,table.matrix th{padding:3px 7px;text-align:center}
table.matrix td.model{text-align:left;position:sticky;left:0;background:#fff;z-index:1}
table.matrix th.model{text-align:left;position:sticky;left:0;background:#eef2f6;z-index:2}
table.matrix td.na{color:#9aa7b3}
.delta-up{color:#2e7d32;font-weight:600}.delta-down{color:#c62828;font-weight:600}
</style></head><body>""")

    gen = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    pv = runs[0]["prompt_version"] if runs else 1
    parts.append(
        f"<h1>Анкета DISC (блиц-тест): своды по прогонам — ru + en</h1>"
        f"<div class='sub'>24 вопроса (ru) / 23 вопроса (en) по методологии DISC/"
        f" {total_runs} прогонов. Сформировано: {gen}.</div>")
    parts.append(
        "<div class='warn'><b>Оговорки.</b> (1) Межформатная — тонкость для LLM: "
        "в книге каждый вопрос дан <b>с вариантами ответа</b>. Decision-модели (clef) "
        "получают анкету как в книге — варианты видны (утверждения-пробы «правильный "
        "ответ — „X“, argmax): задача — <b>выбор</b> из видимых кандидатов. Chat-LLM получают только "
        "вопросы, без вариантов: задача — <b>воспроизведение</b> (вывести/вспомнить "
        "профиль самому) — условия строже. Баллы между форматами сравнивать с этой "
        "разницей; чистые сравнения — внутри формата. (2) Межъязыковая: "
        "ru — 24 вопроса, en — 23 (вопроса про болезненную реакцию на критику в "
        "английском оригинале нет), поэтому сравниваем проценты, а не сырые баллы.</div>")
    parts.append("<h2>Методика</h2>")
    parts.append("""<div class='model' style="max-width:1000px">
<ol style="margin:0; padding-left:24px">
<li style="margin-bottom:10px"><b>Материал.</b> Анкета по методологии DISC — 24 вопроса (ru) /
23 (en); вопросы задаются <b>без вариантов</b> — модель называет профиль, сочетание или
«нет однозначного ответа». Источник — блиц-тест из книги Томаса Эриксона: ru — «Кругом одни
идиоты. Если вам так кажется, возможно, вам не кажется» (Эксмо, 2014); en —
«Surrounded by Idiots» (английское издание, Macmillan/Ebury, 2019). Эталонные ответы сверены
с разделом ответов книги (гл. 20) — снимки с правильными ответами:
ru — <a href='../quiz/reference/quiz-with-key.md'>quiz/reference/quiz-with-key.md</a> ·
en — <a href='../quiz-en/reference/quiz-with-key.md'>quiz-en/reference/quiz-with-key.md</a>.
Источник анкеты и эталонных ответов в промпте не упоминается.</li>
<li style="margin-bottom:10px"><b>Прогон и запрос.</b> Модель отвечает на все вопросы одним
ответом (JSON «номер → ответ»), по 5 прогонов на модель×уровень (часть флагманов-облаков —
по 2); сбойные прогоны не участвуют в метриках (колонка «сбои»).<br>
Запрос: <b>системный промпт отсутствует</b> — один user-месседж с полным текстом задания
(интро + правила формата + вопросы, дословно из <code>prompts/prompt.json</code>).
Параметры: <code>stream false</code>, <code>num_ctx 65536</code>,
<code>num_predict 32768</code>, ручка мышления уровня (<code>think</code> /
<code>reasoning_effort</code> / <code>enable_thinking false</code> — по API провайдера),
<code>seed</code> не задаётся; остальное — дефолты модели.
Для kimi (подписка Kimi coding) — тот же user-промпт без системного.
Для clef — decision-протокол <code>/v1/systemone</code> (см. оговорку выше).
<pre style="background:#f4f6f8; padding:8px; font-size:12px; overflow:auto">POST /api/chat
{
  &quot;model&quot;: &quot;&lt;тег модели&gt;&quot;,
  &quot;messages&quot;: [
    {
      &quot;role&quot;: &quot;user&quot;,
      &quot;content&quot;: &quot;&lt;пользовательский промпт — см. ниже&gt;&quot;
    }
  ],
  &quot;stream&quot;: false,
  &quot;keep_alive&quot;: &quot;10m&quot;,
  &quot;options&quot;: {
    &quot;num_ctx&quot;: 65536,
    &quot;num_predict&quot;: 32768
  },
  &quot;think&quot;: &quot;&lt;off | low | medium | high | xhigh — по модели&gt;&quot;
}</pre>
Пользовательские промпты (дословно):
<ul>
<li>ru — <code>quiz/prompts/prompt.json</code>:
<details><summary style='cursor:pointer'>показать текст</summary>
<pre style="background:#f4f6f8; padding:8px; font-size:12px; white-space:pre-wrap">
В модели DISC четыре поведенческих профиля, названных цветами: красный, жёлтый, зелёный и синий. Проверьте себя: насколько хорошо вы представляете, как действуют и поступают люди разных профилей.

Ниже 24 вопроса. На каждый ответьте, назвав профиль (цвет), который лучше всего подходит; если ответ — сочетание профилей, назовите сочетание; если однозначного ответа нет, так и напишите.

Ответьте строго JSON-ом — объект с ответами по номерам вопросов, без текста вне JSON:
{&quot;1&quot;: &quot;&lt;ответ на вопрос 1&gt;&quot;, &quot;2&quot;: &quot;&lt;ответ на вопрос 2&gt;&quot;, &quot;3&quot;: &quot;&lt;ответ на вопрос 3&gt;&quot;, …, &quot;24&quot;: &quot;&lt;ответ на вопрос 24&gt;&quot;}

Вопросы:
1. Какие профили совместимы в социальном плане?
2. Какие профили совместимы в совместной работе?
3. Какой профиль всегда хотел бы возглавить проект?
4. Какой профиль окажется лучшим хирургом?
5. Какой профиль больше всех упивается ролью оратора?
6. Какой профиль чаще всего знает, где он сохранил электронное письмо от шефа?
7. Какой профиль стремится провести побольше тестов или собрать побольше информации перед тем, как принять решение?
8. Какой профиль всегда приходит вовремя и в этом плане на него можно положиться?
9. Какой профиль раз за разом не следует правилам только ради того, чтобы работа была сделана?
10. Какой профиль охотнее всех апробирует новые технологии или приемы, если это ускорит работу?
11. Какой профиль дольше всех помнит критику в свой адрес?
12. Какой профиль болезненнее всего реагирует на личную критику?
13. Какой профиль менее всех организован, но знает, где может получить нужную информацию?
14. Какой профиль хочет всегда принимать решения?
15. Какой профиль охотнее всего следует последней моде?
16. Какой профиль охотнее берется за сложные задачи?
17. Какой профиль легко судит других?
18. Комбинация каких профилей образует самую успешную команду?
19. Какой профиль вероятнее всего окажется самым разговорчивым?
20. Какой профиль быстрее всех воспримет новую идею?
21. Какой профиль мог бы поручить задание другим, но все же выполнит его сам?
22. Какой профиль окажется лучшим слушателем?
23. Какой профиль не пропустит ни малейшего пункта в инструкции?
</pre></details></li>
<li>en — <code>quiz-en/prompts/prompt.json</code>:
<details><summary style='cursor:pointer'>показать текст</summary>
<pre style="background:#f4f6f8; padding:8px; font-size:12px; white-space:pre-wrap">EN (дословно):
A quick little quiz: how well have you learned the DISC model?

DISC describes four behavioral profiles named after colors: Red, Yellow, Green and Blue. Test yourself: how well do you understand how people of different profiles act and behave?

Below are 23 questions. For each question, name the profile (color) that fits best; if the answer is a combination of profiles, name the combination; if there is no single answer, say so.

Answer strictly in JSON — an object mapping question numbers to your answers, no text outside the JSON:
{&quot;1&quot;: &quot;&lt;your answer to question 1&gt;&quot;, &quot;2&quot;: &quot;&lt;your answer to question 2&gt;&quot;, &quot;3&quot;: &quot;&lt;your answer to question 3&gt;&quot;, ..., &quot;23&quot;: &quot;&lt;your answer to question 23&gt;&quot;}

Questions:
1. Which combination of profiles would naturally agree on a social level?
2. Which combination of profiles naturally work well together?
3. Which profile will always prefer to be the head of a project?
4. Which profile would make the best surgeon?
5. Which person would enjoy giving a speech the most?
6. Which person would know exactly where he saved that email from his boss?
7. Which person would want to do more tests or get more information before making a decision?
8. Which person can you always rely on to arrive on time?
9. Which person doesn’t follow the rulebook to get a job done?
10. Which person would be the most willing to try something new to get the job done?
11. Which person will remember personal criticism the longest?
12. Which person is the least organized but knows exactly where to go to get what he needs?
13. Which profile always wants to make decisions?
14. Which profile wears the latest fashions?
15. Which profile would enjoy new challenges the most?
16. Which profile would be the quickest to judge other people?
17. Which combination of profiles would form the best team?
18. Which profile will probably talk the most?
19. Which profile would assimilate new ideas the quickest?
20. Which profile would delegate a task but then still do it himself?
21. Which profile is the best listener?
22. Which profile wouldn’t miss the last step of the instructions?
23. Which profile is most common in your social circle?</pre>
</details></li>
</ul></li>
<li style="margin-bottom:10px"><b>Уровни мышления.</b> Каждый уровень, поддерживаемый
моделью.</li>
<li style="margin-bottom:10px"><b>Скоринг.</b> Машинный, без судей: сопоставление ответа
с эталоном через словарь синонимов и цветовых токенов. «Не распознано» ≠ «неверно»
(флаги unparsed/skipped — отдельно).</li>
<li><b>Языки.</b> ru и en анкеты — из оригинальных редакций (не перевод друг друга);
вопросы сопоставлены 1:1, сравнение по процентам. Decision-модели (clef) отвечают
argmax по вариантам — см. оговорку выше.</li>
</ol>
<div style="margin-top:10px"><b>Подробно:</b> <a href='../quiz/README.md'>quiz/README.md</a> ·
<a href='../quiz-en/README.md'>quiz-en/README.md</a></div>
</div>""")

    # сводная таблица
    parts.append("<h2>Сводная таблица</h2><table><tr>"
                 "<th>модель</th><th>язык</th><th>уровень</th><th>прогонов</th>"
                 "<th class='num'>балл (ср)</th><th class='num'>min–max</th><th>%</th>"
                 "<th>стабильность</th><th class='num'>json_ok</th>"
                 "<th class='num'>unparsed/skipped</th><th class='num'>сбои</th>"
                 "<th class='num'>p_correct</th><th class='num'>токены вх/вых</th>"
                 "<th class='num'>время, с</th></tr>")
    for g in sorted(groups, key=sort_key):
        a = groups[g]
        stab = f"{a['distinct']} уник. из {a['n']}"
        if a["identical"] is not None:
            stab += f", попарно {a['identical'] * 100:.0f}%"
        tok = f"{a['tok_in'] or '—'}/{a['tok_out'] or '—'}"
        j = "—" if a["json_ok"] is None else f"{a['json_ok'] * 100:.0f}%"
        p = "—" if a["p_correct"] is None else str(a["p_correct"])
        href = f"../models/{g[0]}/{('quiz' if g[1] == 'ru' else 'quiz-en')}/"
        fails = (failed_counts or {}).get(g, 0)
        parts.append(
            f"<tr><td><a href='{href}'>{g[0]}</a></td><td>{g[1]}</td><td>{g[2]}</td>"
            f"<td class='num'>{a['n']}</td><td class='num'><b>{a['mean']:.1f}</b></td>"
            f"<td class='num'>{a['min']}–{a['max']}</td><td>{pct_lang(a)}"
            f"<div class='bar'><div style='width:{a['mean'] / a['total'] * 100:.0f}%'></div></div></td>"
            f"<td>{stab}</td><td class='num'>{j}</td>"
            f"<td class='num'>{a['unparsed']}/{a['skipped']}</td>"
            f"<td class='num'>{fails}</td>"
            f"<td class='num'>{p}</td><td class='num'>{tok}</td>"
            f"<td class='num'>{a['dur']}</td></tr>")
    parts.append("</table>")
    parts.append("<div class='muted'>Сбои — прогоны с транспортными ошибками (run.json "
                 "error), в метриках не участвуют; сырой результат сохранён рядом.</div>")
    if any(a["contention"] for a in groups.values()):
        parts.append("<div class='warn'>У части прогонов в VRAM была чужая модель "
                     "(факт в run.json ollama_contention) — на баллы это не влияет, "
                     "но время может быть завышено.</div>")

    # Язык: ru vs en — главный вопрос исследования
    parts.append("<h2>Язык: ru vs en (влияние языка на точность и устойчивость)</h2>"
                 "<div class='muted'>лучший уровень модели на каждом языке; "
                 "Δ = en% − ru% (в п.п.; множества вопросов разные: 24/23)</div>"
                 "<table><tr><th>модель</th><th>ru: лучший балл</th><th>%</th>"
                 "<th>en: лучший балл</th><th>%</th><th class='num'>Δ п.п.</th>"
                 "<th>стабильность ru</th><th>стабильность en</th></tr>")
    deltas = []
    folders = folders_sorted(groups)
    for folder in folders:
        br = lang_best(groups, folder, "ru")
        be = lang_best(groups, folder, "en")
        if not br and not be:
            continue
        rtxt = etxt = r_pct = e_pct = "—"
        rst = est = "—"
        rp = ep = None
        if br:
            r_pct = f"{br['mean'] / br['total'] * 100:.0f}%"
            rtxt = f"{br['mean']:.1f} ({br['min']}–{br['max']}) @ {lang_level(groups, folder, 'ru', br)}"
            rp = br["mean"] / br["total"] * 100
            rst = f"{br['distinct']} уник." + (f", попарно {br['identical'] * 100:.0f}%" if br["identical"] is not None else "")
        if be:
            e_pct = f"{be['mean'] / be['total'] * 100:.0f}%"
            etxt = f"{be['mean']:.1f} ({be['min']}–{be['max']}) @ {lang_level(groups, folder, 'en', be)}"
            ep = be["mean"] / be["total"] * 100
            est = f"{be['distinct']} уник." + (f", попарно {be['identical'] * 100:.0f}%" if be["identical"] is not None else "")
        dtxt = "—"
        if rp is not None and ep is not None:
            d = ep - rp
            deltas.append(d)
            cls = "delta-up" if d > 0 else ("delta-down" if d < 0 else "")
            dtxt = f"<span class='{cls}'>{d:+.1f}</span>"
        parts.append(f"<tr><td>{folder}</td><td>{rtxt}</td><td>{r_pct}</td>"
                     f"<td>{etxt}</td><td>{e_pct}</td>"
                     f"<td class='num'>{dtxt}</td><td>{rst}</td><td>{est}</td></tr>")
    if deltas:
        avg = sum(deltas) / len(deltas)
        verdict = "en лучше" if avg > 0 else "ru лучше" if avg < 0 else "паритет"
        parts.append("</table>"
                     f"<div class='muted'>средняя Δ по моделям с обоими языками: "
                     f"<b>{avg:+.1f} п.п.</b> ({verdict})</div>")
    else:
        parts.append("</table>")

    # карточки моделей
    parts.append("<h2>Модели × языки × уровни</h2>")
    for folder in folders:
        gs = [g for g in groups if g[0] == folder]
        parts.append(f"<div class='model'><h3>{folder}</h3><table><tr>"
                     "<th>язык</th><th>уровень</th><th class='num'>балл</th><th>%</th>"
                     "<th>Δ к первому уровню языка</th><th class='num'>прогонов</th>"
                     "<th>стабильность</th></tr>")
        base = {}
        for g in sorted(gs, key=sort_key):
            a = groups[g]
            first = g[1] not in base
            if first:
                base[g[1]] = a["mean"]
            dtxt = "—" if first else f"{a['mean'] - base[g[1]]:+.1f}"
            stab = f"{a['distinct']} уник." + (f", попарно {a['identical'] * 100:.0f}%" if a["identical"] is not None else "")
            parts.append(f"<tr><td>{g[1]}</td><td>{g[2]}</td>"
                         f"<td class='num'><b>{a['mean']:.1f}</b> ({a['min']}–{a['max']})</td>"
                         f"<td>{pct_lang(a)}<div class='bar'><div "
                         f"style='width:{a['mean'] / a['total'] * 100:.0f}%'></div></div></td>"
                         f"<td class='num'>{dtxt}</td><td class='num'>{a['n']}</td>"
                         f"<td>{stab}</td></tr>")
        parts.append("</table></div>")

    # единая матрица: столбцы по нумерации ru, en-вопросы сопоставлены
    gs_all = [g for g in sorted(groups, key=sort_key)]
    mx = {lang: matrix_rows(groups, lang) for lang in ("ru", "en")}
    parts.append("<h2>Матрица: модель × язык × уровень × вопрос</h2>"
                 "<div class='muted'>столбцы — нумерация ru (24 вопроса); вторая строка шапки — "
                 "номера сопоставленных en-вопросов (ru 12 не имеет en-аналога). Ячейка — доля "
                 "верных ответов на вопрос по прогонам группы, 0–100 (наведение — точные "
                 "«верных/всего»); 📘 — эталонный ответ не однозначный</div>")
    parts.append("<table class='matrix'><tr><th class='model'>модель @ уровень</th><th>язык</th>")
    for q in KEYS["ru"]["questions"]:
        mark = " <span class='bm'>📘</span>" if q["kind"] in ("book", "none") else ""
        parts.append(f"<th class='num'>{q['n']}{mark}</th>")
    en_head = "".join(
        f"<th class='num na'>{RU_TO_EN[q['n']] or '—'}"
        f"{' <span class=\'bm\'>📘</span>' if RU_TO_EN[q['n']] and KEYS['en']['questions'][RU_TO_EN[q['n']] - 1]['kind'] in ('book', 'none') else ''}</th>"
        for q in KEYS["ru"]["questions"])
    parts.append("<tr><th class='model'></th><th>№ en →</th>" + en_head + "</tr>")
    for g in gs_all:
        lang = g[1]
        rates = mx[lang][g]
        cells = []
        for q in KEYS["ru"]["questions"]:
            if lang == "ru":
                rate = rates[q["n"] - 1]
            else:
                en_n = RU_TO_EN[q["n"]]
                rate = rates[en_n - 1] if en_n else None
            if rate is None:
                cells.append("<td class='num na'>—</td>")
            else:
                okc = round(rate * groups[g]["n"])
                cells.append(f"<td class='num' style='{heat_color(rate)}' "
                             f"title='{okc} из {groups[g]['n']} прогонов'>{rate * 100:.0f}</td>")
        parts.append(f"<tr><td class='model'>{g[0]} "
                     f"@ {g[2]}</td><td>{g[1]}</td>" + "".join(cells) + "</tr>")
    parts.append("</table>")

    parts.append("<h2>Проблемные вопросы (модели массово не отвечают)</h2>")
    parts.append("<div class='muted'>включены вопросы с суммарной долей верных &lt;50% "
                 "(ru + en вместе); «решили все» — группы, ответившие верно во всех своих "
                 "прогонах; распределение — по всем прогонам языка</div>")
    for q, s_ru, s_en, rate in problems or []:
        en_n = RU_TO_EN[q["n"]]
        head = f"Q{q['n']} (en {en_n})" if en_n else f"Q{q['n']} (en —)"
        et = f"Эталон: ru «{q['key']}»"
        if s_en:
            et += f" · en «{KEYS['en']['questions'][en_n - 1]['key']}»"
        lines_h = [f"<div class='model'><b>{head}.</b> {q['question']}",
                   f"{et}",
                   "Верных: "]
        vc = []
        if s_ru:
            vc.append(f"ru {s_ru['ok']}/{s_ru['tot']} ({s_ru['rate'] * 100:.0f}%)")
        if s_en:
            vc.append(f"en {s_en['ok']}/{s_en['tot']} ({s_en['rate'] * 100:.0f}%)")
        lines_h.append(" · ".join(vc))

        def perfect_str(s):
            if s is None:
                return "нет прогонов"
            return "; ".join(s["perfect"]) if s["perfect"] else "никто"
        lines_h.append("Решили все свои прогоны: ru — " + perfect_str(s_ru)
                       + " · en — " + perfect_str(s_en))

        def dist_str(s):
            if not s or not s["tot"]:
                return "нет прогонов"
            items = s["dist"].most_common()
            out = [f"{c * 100 // s['tot']}% «{s['raw'][k]}»" for k, c in items[:4]]
            rest = s["tot"] - sum(c for _, c in items[:4])
            if rest:
                out.append(f"прочее {rest * 100 // s['tot']}%")
            return ", ".join(out)
        if s_ru:
            lines_h.append("Ответы ru: " + dist_str(s_ru))
        if s_en:
            lines_h.append("Ответы en: " + dist_str(s_en))
        parts.append("<br>".join(lines_h) + "</div>")
    parts.append("</table>")

    # точность по цветам, по языкам
    for lang in ("ru", "en"):
        rs_lang = [r for r in runs if r["_lang"] == lang]
        if not rs_lang:
            continue
        color_stats = defaultdict(lambda: [0, 0])
        for r in rs_lang:
            for x, q in zip(r["verdict"]["per_question"], KEYS[lang]["questions"]):
                if q["kind"] == "color":
                    c = COLOR_OF[q["key"]]
                    color_stats[c][0] += 1 if x.get("correct") else 0
                    color_stats[c][1] += 1
        parts.append(f"<h2>Точность по профилям — {lang} (single-цветные вопросы)</h2>"
                     "<table><tr><th>профиль</th><th class='num'>верных</th><th>%</th></tr>")
        for c in ("D", "I", "S", "C"):
            okc, tot = color_stats[c]
            rate = okc / tot if tot else 0
            parts.append(f"<tr><td>{COLOR_TITLE[c]}</td><td class='num'>{okc}/{tot}</td>"
                         f"<td>{rate * 100:.0f}%<div class='bar'><div "
                         f"style='width:{rate * 100:.0f}%'></div></div></td></tr>")
        parts.append("</table>")

    parts.append("<div class='muted' style='margin-top:20px'>Флаги: unparsed — ответ не "
                 "распознан (это не «неверный ответ»); skipped — вопроса нет в JSON; "
                 "ambiguous — распознано 2+ профиля; near — верный профиль без нужного "
                 "уточнения. Стабильность — уникальные наборы ответов и попарное совпадение "
                 "прогонов группы. Ссылки — папки прогонов "
                 "<code>models/&lt;модель&gt;/quiz[-en]/</code>.</div>")
    parts.append("</body></html>")
    out.write_text("".join(parts), encoding="utf-8")


def dist_str_md(s):
    if not s or not s["tot"]:
        return "нет прогонов"
    items = s["dist"].most_common()
    out = [f"{c * 100 // s['tot']}% «{s['raw'][k]}»" for k, c in items[:4]]
    rest = s["tot"] - sum(c for _, c in items[:4])
    if rest:
        out.append(f"прочее {rest * 100 // s['tot']}%")
    return ", ".join(out)


def build_md(groups: dict, runs: list[dict], out: Path, problems: list | None = None) -> None:
    lines = [
        "# Анкета DISC (блиц-тест): своды (ru + en)",
        "",
        f"{len(runs)} прогонов. ru — 24 вопроса, en — 23 (межъязыковое сравнение — "
        f"по процентам). Оговорка о форматах: в книге вопросы даны с вариантами; "
        f"chat-LLM получают их без вариантов (воспроизведение — строже), decision-модели "
        f"(clef) — с видимыми кандидатами (выбор). "
        f"Сформировано "
        f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}.",
        "",
        "## Методика",
        "",
        "1. **Материал** — анкета по методологии DISC, 24 вопроса (ru) / 23 (en); "
        "вопросы без вариантов — модель называет профиль, сочетание или «нет "
        "однозначного ответа». Источник — блиц-тест из книги Томаса Эриксона: "
        "ru — «Кругом одни идиоты. Если вам так кажется, возможно, вам не кажется» "
        "(Эксмо, 2014); en — «Surrounded by Idiots» (английское издание, "
        "Macmillan/Ebury, 2019). Эталонные ответы сверены с разделом ответов книги "
        "(гл. 20) — снимки с правильными ответами: quiz/reference/quiz-with-key.md, "
        "quiz-en/reference/quiz-with-key.md. Источник анкеты и эталонных ответов "
        "в промпте не упоминается.",
        "2. **Прогон и запрос** — модель отвечает на все вопросы одним ответом (JSON "
        "«номер → ответ»), по 5 прогонов на модель×уровень (часть флагманов-облаков — "
        "по 2); сбойные прогоны вне метрик. Для clef — decision-протокол (argmax "
        "по вариантам).",
        "",
        "Запрос (системный промпт отсутствует — один user-месседж с полным текстом "
        "задания; seed не задаётся, остальное — дефолты модели):",
        "",
        "```json",
        REQ_JSON,
        "```",
        "",
        "Пользовательские промпты (дословно):",
        "",
        "- ru — `quiz/prompts/prompt.json`:",
        "",
        "```text",
        PROMPT_RU,
        "```",
        "- en — `quiz-en/prompts/prompt.json`:",
        "",
        "```text",
        PROMPT_EN,
        "```",
        "3. **Уровни мышления** — каждый уровень, поддерживаемый моделью.",
        "4. **Скоринг** — машинный, без судей: сопоставление с эталоном через словарь "
        "синонимов; «не распознано» ≠ «неверно».",
        "5. **Языки** — ru и en из оригинальных редакций (не перевод), вопросы "
        "сопоставлены 1:1, сравнение по процентам. Decision-модели (clef) — argmax "
        "по вариантам.",
        "- **Подробно**: quiz/README.md · quiz-en/README.md",
        "",
        "| модель | язык | уровень | прогонов | балл (ср) | min–max | % | стабильность | json_ok | "
        "unparsed/skipped | p_correct | токены вх/вых | время, с |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for g in sorted(groups, key=sort_key):
        a = groups[g]
        stab = f"{a['distinct']} уник. из {a['n']}"
        if a["identical"] is not None:
            stab += f", попарно {a['identical'] * 100:.0f}%"
        j = "—" if a["json_ok"] is None else f"{a['json_ok'] * 100:.0f}%"
        p = "—" if a["p_correct"] is None else str(a["p_correct"])
        lines.append(
            f"| {g[0]} | {g[1]} | {g[2]} | {a['n']} | **{a['mean']:.1f}** | {a['min']}–{a['max']} | "
            f"{pct_lang(a)} | {stab} | {j} | {a['unparsed']}/{a['skipped']} | {p} | "
            f"{a['tok_in'] or '—'}/{a['tok_out'] or '—'} | {a['dur']} |")
    lines += ["", "## Язык: ru vs en", "",
              "Лучший уровень модели на каждом языке; Δ = en% − ru% "
              "(множества вопросов разные: 24/23).",
              "",
              "| модель | ru лучший | ru % | en лучший | en % | Δ п.п. |",
              "|---|---|---|---|---|---|"]
    deltas = []
    folders = folders_sorted(groups)
    for folder in folders:
        br = lang_best(groups, folder, "ru")
        be = lang_best(groups, folder, "en")
        rp = f"{br['mean']:.1f} @ {lang_level(groups, folder, 'ru', br)}" if br else "—"
        ep = f"{be['mean']:.1f} @ {lang_level(groups, folder, 'en', be)}" if be else "—"
        r_pct = f"{br['mean'] / br['total'] * 100:.0f}%" if br else "—"
        e_pct = f"{be['mean'] / be['total'] * 100:.0f}%" if be else "—"
        d = "—"
        if br and be:
            dd = be["mean"] / be["total"] * 100 - br["mean"] / br["total"] * 100
            deltas.append(dd)
            d = f"{dd:+.1f}"
        lines.append(f"| {folder} | {rp} | {r_pct} | {ep} | {e_pct} | {d} |")
    if deltas:
        lines += ["", f"Средняя Δ: **{sum(deltas) / len(deltas):+.1f} п.п.**"]

    # единая матрица + сложность (столбцы по нумерации ru, en сопоставлен)
    mx = {lang: matrix_rows(groups, lang) for lang in ("ru", "en")}
    en_head = " | ".join(
        f"{RU_TO_EN[q['n']] or '—'}"
        f"{'📘' if RU_TO_EN[q['n']] and KEYS['en']['questions'][RU_TO_EN[q['n']] - 1]['kind'] in ('book', 'none') else ''}"
        for q in KEYS["ru"]["questions"])
    lines += ["", "## Матрица: модель × язык × уровень × вопрос", "",
              "Столбцы — нумерация ru; строка «№ en» — сопоставленные en-вопросы "
              "(ru 12 не имеет en-аналога). Ячейка — доля верных, 0–100.",
              "",
              "| модель @ уровень | язык | " + " | ".join(
                  f"{q['n']}{'' if q['kind'] == 'color' else '📘'}"
                  for q in KEYS["ru"]["questions"]) + " |",
              "|---|---|" + "---|" * len(KEYS["ru"]["questions"]),
              "|  | **№ en →** | " + en_head + " |"]
    for g in sorted(groups, key=sort_key):
        lang = g[1]
        rates = mx[lang][g]
        cells = []
        for q in KEYS["ru"]["questions"]:
            if lang == "ru":
                rate = rates[q["n"] - 1]
            else:
                en = RU_TO_EN[q["n"]]
                rate = rates[en - 1] if en else None
            cells.append(f"{rate * 100:.0f}" if rate is not None else "—")
        lines.append(f"| **{g[0]}** @ {g[2]} | {lang} | " + " | ".join(cells) + " |")

    q_stat = {lang: defaultdict(lambda: [0, 0]) for lang in ("ru", "en")}
    for r in runs:
        for x in r["verdict"]["per_question"]:
            q_stat[r["_lang"]][x["n"]][0] += 1 if x.get("correct") else 0
            q_stat[r["_lang"]][x["n"]][1] += 1
    lines += ["", "## Проблемные вопросы (модели массово не отвечают)", "",
              "Включены вопросы с суммарной долей верных <50% (ru + en вместе)."]
    for q, s_ru, s_en, rate in problems or []:
        en_n = RU_TO_EN[q["n"]]
        lines.append("")
        head_md = f"Q{q['n']} (en {en_n})" if en_n else f"Q{q['n']} (en —)"
        lines.append(f"**{head_md}** {q['question']}")
        et = f"Эталон: ru «{q['key']}»"
        if s_en:
            et += f" · en «{KEYS['en']['questions'][en_n - 1]['key']}»"
        lines.append(et)
        vc = []
        if s_ru:
            vc.append(f"ru {s_ru['ok']}/{s_ru['tot']} ({s_ru['rate'] * 100:.0f}%)")
        if s_en:
            vc.append(f"en {s_en['ok']}/{s_en['tot']} ({s_en['rate'] * 100:.0f}%)")
        lines.append("Верных: " + " · ".join(vc))

        def perfect_str_md(s):
            if s is None:
                return "нет прогонов"
            return "; ".join(s["perfect"]) if s["perfect"] else "никто"
        lines.append("Решили все свои прогоны: ru — " + perfect_str_md(s_ru)
                     + " · en — " + perfect_str_md(s_en))
        if s_ru:
            lines.append("Ответы ru: " + dist_str_md(s_ru))
        if s_en:
            lines.append("Ответы en: " + dist_str_md(s_en))
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--print", action="store_true", help="показать сводную таблицу в stdout")
    args = ap.parse_args()

    runs = load_runs()
    if not runs:
        print("нет прогонов (models/*/quiz[-en]/run-*/run.json)")
        return 1
    groups = defaultdict(list)
    for r in runs:
        groups[group_key(r)].append(r)
    # сбойные прогоны (транспортная ошибка) — вне метрик, факт в отчёте
    failed = defaultdict(int)
    clean = defaultdict(list)
    for r in runs:
        g = group_key(r)
        if r.get("error"):
            failed[g] += 1
        else:
            clean[g].append(r)
    groups = defaultdict(list)
    for g, rs in clean.items():
        groups[g] = rs
    agg = {g: agg_group(rs) for g, rs in groups.items()}
    FAILED_COUNTS = dict(failed)

    problems = compute_problems(groups)
    REPORTS.mkdir(exist_ok=True)
    build_md(agg, runs, REPORTS / "QUIZ.md", problems)
    build_html(agg, runs, REPORTS / "QUIZ.html", dict(failed), problems)
    print(f"отчёты: reports/QUIZ.md, reports/QUIZ.html ({len(runs)} прогонов)")

    if args.print:
        for g in sorted(agg, key=sort_key):
            a = agg[g]
            print(f"{g[0]:<45} {g[1]} {g[2]:<9} n={a['n']} балл={a['mean']:.1f} "
                  f"({a['min']}–{a['max']}) {pct_lang(a)} уник={a['distinct']} "
                  f"json_ok={a['json_ok']} unparsed={a['unparsed']} skipped={a['skipped']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
