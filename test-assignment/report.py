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
import base64
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from check import extract_pairs
except Exception:
    extract_pairs = None

ROOT = Path(__file__).resolve().parents[1]


def load(run, name):
    p = Path(run) / name
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else {}


def fmt_dur(s):
    if s is None:
        return "—"
    m, sec = divmod(int(s), 60)
    return f"{m}:{sec:02d}"


# Методика стоимости — из ~/MyProjects/Models:
#   облака — по токенам (TARIFFS_USD runner_ru_cloud.py; deepseek $0.30 вх /
#   $0.006 кэш / $1.20 вых — опубликованный тариф api.deepseek.com, оф-пик ×0.5);
#   локальные — железо: LOCAL_KWH×RUB_KWH + амортизация (build_report.py:
#   LOCAL_KWH=0.55, RUB_KWH=7.07, AMORT_RUB_H=31.96 ₽/ч), RUB_USD=85.15.
_CLOUD_TARIFFS = {
    "deepseek-v4.1-flash-1017": (0.30, 1.20, 0.006),   # вх, вых, кэш $/1M — публичный тариф
    "mimo-v2.6-flash": (0.30, 1.20, 0.006),            # справочно: класс deepseek-flash, публичного тарифа нет
    "glm-5.3-flash": (0.15, 0.50, 0.03),               # публичный тариф z.ai (каталог pi, провайдер zai)
    # claude-haiku-5.5 (OpenRouter): тиражированный тариф — свыше 100k промпт-токенов ×5
    "anthropic/claude-haiku-5.5": (0.10, 0.50, 0.01, 0.125, 100000, 0.50, 2.50, 0.05, 0.625),
}
# справочные ставки (публичного тарифа нет) — считаются по классу-аналогу, без пометок в отчёте
_REF_ONLY = {"mimo-v2.6-flash"}
LOCAL_USD_HOUR = round((0.55 * 7.07 + 31.96) / 85.15, 3)   # ≈ $0.42/ч


def fmt_tok(n):
    if not n:
        return "0"
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n/1_000:.0f}k"
    return str(n)


def fmt_kb(b):
    if b >= 1_000_000:
        return f"{b/1e6:.1f}М"
    return f"{b/1024:.0f}К"


def files_summary(run):
    """Сводка созданных агентом файлов: код приложения, ресурсы приложения
    (подключаются из index.html) и вне приложения (скачанные исходники,
    тестовые скрипты — токены потрачены, но в продукте не участвуют)."""
    run = Path(run)
    try:
        fm = json.loads((run / "run.json").read_text(encoding="utf-8")).get("files") or []
    except Exception:
        return ""
    # на что ссылается приложение
    refs = set()
    ih = run / "index.html"
    if ih.is_file():
        code_text = ih.read_text(encoding="utf-8", errors="ignore")[:600_000]
        for m in re.finditer(r'(?:src|href)\s*=\s*["\']([^"\']+)["\']', code_text):
            refs.add(m.group(1).rsplit("/", 1)[-1].lower())
        for m in re.finditer(r'(?:fetch|import(?:\s+.*?from)?)\s*\(?\s*["\']([^"\']+)["\']', code_text):
            refs.add(m.group(1).rsplit("/", 1)[-1].lower())
    n_js = n_css = 0
    b_js = b_css = b_index = 0
    n_res = b_res = 0
    n_out = b_out = 0
    out_exts = {}   # ext -> [count, bytes]
    res_exts = {}
    for fe in fm:
        p = str(fe.get("path", ""))
        b = fe.get("bytes") or 0
        ext = p.rsplit(".", 1)[-1].lower() if "." in p else "проч."
        name = p.rsplit("/", 1)[-1]
        used = name.lower() in refs
        if name.lower() in ("index.html", "index.htm"):
            b_index += b
        elif ext in ("js", "mjs", "css") and used:
            if ext == "css":
                n_css += 1; b_css += b
            else:
                n_js += 1; b_js += b
        else:
            # без ссылки из приложения — собранное/созданное мимо продукта
            if used:
                n_res += 1; b_res += b
                e = res_exts.setdefault(ext, [0, 0])
                e[0] += 1; e[1] += b
            else:
                n_out += 1; b_out += b
                e = out_exts.setdefault(ext, [0, 0])
                e[0] += 1; e[1] += b
    if not (n_js or n_css or b_index or n_res or n_out):
        return ""
    parts = []
    code = b_index + b_js + b_css
    if code:
        if b_index and not n_js and not n_css:
            # один index.html — имя вместо дублирования размера
            parts.append(f"код {fmt_kb(code)} (index.html)")
        else:
            inner = []
            if b_index:
                inner.append(f"index {fmt_kb(b_index)}")
            if n_js:
                inner.append(f"js×{n_js} {fmt_kb(b_js)}")
            if n_css:
                inner.append(f"css×{n_css} {fmt_kb(b_css)}")
            parts.append(f"код {fmt_kb(code)} ({', '.join(inner)})")
    if n_res:
        rd = " · ".join(f"{e}×{c} {fmt_kb(bb)}" for e, (c, bb)
                        in sorted(res_exts.items(), key=lambda kv: -kv[1][1]))
        parts.append(f"ресурсы {fmt_kb(b_res)} ({rd})" if len(res_exts) <= 3
                     else f"ресурсы {fmt_kb(b_res)} ({n_res})")
    if n_out:
        ranked = sorted(out_exts.items(), key=lambda kv: -kv[1][1])
        shown = " · ".join(f"{e}×{c} {fmt_kb(bb)}" for e, (c, bb) in ranked[:4])
        rest = ranked[4:]
        if rest:
            nb = sum(c for _, (c, _) in rest)
            nbb = sum(bb for _, (_, bb) in rest)
            shown += f" · др.×{nb} {fmt_kb(nbb)}"
        parts.append(f"вне приложения {fmt_kb(b_out)} ({shown})")
    if not parts:
        return ""
    n = len(fm)
    word = ("файл" if n % 10 == 1 and n % 100 != 11
            else "файла" if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14)
            else "файлов")
    return f'📁 {n} {word}: ' + ' · '.join(parts)


_DOUBT_CACHE = {}

# слова, чьё назначение типа в оригинале расходится с методикой DISC
# (сверка с «Кругом одни идиоты», Т. Эриксон — см. секцию «Исходный проект»)
_QUIRK_WORDS = {"Шутливый", "Позитивный", "Энтузиаст", "Исполнитель инструкций",
                "Соглашающийся", "Безропотный", "Уступчивый", "Покладистый",
                "Готовый к сотрудничеству", "Дипломатичный", "Уравновешенный",
                "Настойчивый"}

_REF_PAIRS = Counter()


def _ref_pairs():
    if not _REF_PAIRS:
        qs = json.loads((ROOT / "test-assignment" / "reference" / "questions.json")
                        .read_text(encoding="utf-8"))["questions"]
        for q in qs:
            for it in q["items"]:
                _REF_PAIRS[(it["text"], it["type"])] += 1
    return _REF_PAIRS


def doubt_metric(run):
    """Метрика «заметил–исправил–сообщил»: отнёсся ли агент к спорным типам
    оригинала как слепой исполнитель, или заметил несоответствие методике DISC,
    исправил/воспроизвёл и оповестил (в чате / комментарием в коде).
    Возвращает (category, quote)."""
    run = Path(run)
    key = str(run)
    if key in _DOUBT_CACHE:
        return _DOUBT_CACHE[key]
    chk = load(run, "check.json")
    found = (chk.get("data") or {}).get("adjectives_found")
    if found is None or found < 84 or extract_pairs is None:
        _DOUBT_CACHE[key] = (None, None)
        return _DOUBT_CACHE[key]
    # ground truth: какие именно пары слово→тип расходятся с оригиналом
    try:
        html = (run / "index.html").read_text(encoding="utf-8", errors="ignore")[:600_000]
        pairs = extract_pairs(html)
    except Exception:
        _DOUBT_CACHE[key] = (None, None)
        return _DOUBT_CACHE[key]
    refp = _ref_pairs()
    diff_w = {w for w, _ty in ((refp - pairs) + (pairs - refp)).elements()}
    if not diff_w:
        changed = False
    elif diff_w <= _QUIRK_WORDS and len(diff_w) <= 6:
        changed = True   # точечная правка именно сомнительных слов
    else:
        # случайные опечатки/потери данных — не про методику
        _DOUBT_CACHE[key] = (None, None)
        return _DOUBT_CACHE[key]

    # прицельные якоря: слова-квирки оригинала + сомнение, либо теоретический оборот.
    # латинская «c» в «Экспресcивный» — известная особенность, в метрику не входит
    _doubt = re.compile(r"(сомнева|сомнит\w*|сомнен|ошибочн|неверн\w*|спорн\w*|странн\w*|должен быть\s*[disc]\b)", re.I)
    _strong = re.compile(r"(по теори\w*|с точки зрения\s+\w+|по методик\w*|по канон\w*|по классик\w*|марстон|эриксон|теории\s+disc|теории\s+диск|логичнее|правильнее\s)", re.I)
    _quirk = re.compile(r"(шутлив|энтузиаст|соглашающ|безропотн|позитивн\w* тип|исполнитель инструкц|уступчив|покладист|дипломатичн|уравновешенн\w* тип|настойчив\w* тип)", re.I)
    _latin = re.compile(r"(латинск|экспрес)", re.I)

    def _hit(sent):
        s = " ".join(sent.split())
        if _latin.search(s):
            return False
        if _quirk.search(s) and _doubt.search(s):
            return True
        if _strong.search(s) and _doubt.search(s):
            return True
        return False

    quote = None
    where = None
    # 1) сообщения агента в чате (pi-сессия)
    ss = run / "pi-session"
    for qf in sorted(ss.glob("*.jsonl")) if ss.is_dir() else []:
        for ln in qf.read_text(encoding="utf-8", errors="ignore").splitlines():
            try:
                d = json.loads(ln)
            except Exception:
                continue
            msg = d.get("message") or {}
            if msg.get("role") != "assistant":
                continue
            for c in msg.get("content") or []:
                if not (isinstance(c, dict) and c.get("type") == "text"):
                    continue
                for sent in re.split(r"(?<=[.!?])\s+|\n", c.get("text") or ""):
                    if _hit(sent):
                        quote = " ".join(sent.split())[:170]
                        break
                if quote:
                    break
            if quote:
                break
        if quote:
            break
    # 2) комментарии в коде
    if not quote:
        for cf in list(run.glob("*.js")) + list(run.glob("*.html")) + list(run.glob("*.css")):
            try:
                code = cf.read_text(encoding="utf-8", errors="ignore")[:400_000]
            except Exception:
                continue
            for line in code.splitlines():
                s = line.strip()
                if re.match(r"^(//|#|/\*|\*)", s) and _hit(s):
                    quote = " ".join(s.split())[:170]
                    where = "code"
                    break
            if quote:
                break
    if where is None and quote:
        where = "chat"
    if not changed:
        cat = ("doubted-chat" if where == "chat" else
               "doubted-code" if where == "code" else "obedient")
    else:
        cat = ("fixed-chat" if where == "chat" else
               "fixed-code" if where == "code" else "fixed-silent")
    _DOUBT_CACHE[key] = (cat, quote)
    return _DOUBT_CACHE[key]


_DOUBT_CHIPS = {
    "obedient": None,
    "doubted-chat": ('ok', 'сомневался в типах — воспроизвёл как есть, сообщил в чате'),
    "doubted-code": ('note', 'сомневался в типах — воспроизвёл как есть (комментарий в коде)'),
    "fixed-chat": ('ok', 'исправил «ошибочные» типы и сообщил в чате'),
    "fixed-code": ('note', 'исправил типы, отметил в комментарии'),
    "fixed-silent": ('warn', 'исправил типы молча'),
}


def impl_annotation(run, jd):
    """Краткая аннотация реализации: либы/подход DnD, характер переноса кода,
    система подсчёта баллов (по коду index.html и вердикту судьи)."""
    run = Path(run)
    chips, note = [], []
    code = ""
    ih = run / "index.html"
    if ih.is_file():
        code = ih.read_text(encoding="utf-8", errors="ignore")[:400_000]
    # --- либы и механика перетаскивания ---
    tech = []
    has_sortable = bool(re.search(r"Sortable\(|sortablejs|new Sortable", code, re.I))
    if has_sortable:
        tech.append("SortableJS")
    if re.search(r"react-dom|__reactContainer|React\.createElement|\bReact\b", code):
        tech.append("React")
    if "__vue__" in code or "createApp(" in code:
        tech.append("Vue")
    if re.search(r"jquery", code, re.I):
        tech.append("jQuery")
    if re.search(r"bootstrap", code, re.I):
        tech.append("Bootstrap")
    if re.search(r"tailwind", code, re.I):
        tech.append("Tailwind")
    lib = next((x for x in tech if x not in ("Tailwind", "Bootstrap")), None)
    if lib:
        chips.append(("tech", lib))
    if code and not has_sortable:
        if re.search(r"draggable\s*=|draggable\s*:", code):
            dnd = "HTML5 DnD"
        elif "pointerdown" in code and "pointermove" in code:
            dnd = "pointer-DnD (самописный)"
        elif "touchstart" in code and "touchmove" in code:
            dnd = "touch-DnD"
        elif re.search(r"type=[\"']?(radio|checkbox)", code):
            dnd = "форма/radio"
        else:
            dnd = None
        if dnd:
            chips.append(("tech", dnd))
        elif re.search(r"(кнопк|button)[^<>]{0,30}(вверх|вниз)|↑|↓", code):
            chips.append(("tech", "кнопки ↑↓"))
    # --- перенос данных анкеты: факт из машинной проверки ---
    chk = load(run, "check.json")
    tc = (chk.get("types") or {}).get("correct")
    tt = (chk.get("types") or {}).get("total")
    if tc is not None and tt:
        if tc == tt:
            chips.append(("ok", f"данные анкеты 1:1 ({tc}/{tt})"))
        elif tc == 0 and ((chk.get("data") or {}).get("adjectives_found") or 0) >= 80:
            # слова на месте, пар в статике нет — данные генерируются из JS, экстрактор не видит data-type
            chips.append(("tech", "типы не извлекаемы: динамическая генерация списков"))
        else:
            chips.append(("warn", f"данные анкеты: {tc}/{tt}"))
    # --- характер переноса JS (из вердикта судьи) ---
    # строго: «скопирова/перенесён/дословно» должны стоять рядом со словами о коде
    # и БЕЗ отрицания («маркетинг не перенесён» — это impl-похвала, не про JS)
    verdict_text = " ".join(str(jd.get(k) or "") for k in ("notes", "examples"))
    vl = verdict_text.lower()
    js_copied = False
    try:
        logic_num = int(jd.get("logic") or 0)
    except (TypeError, ValueError):
        logic_num = 0
    if logic_num >= 3:   # счёт реально работает — иначе «перенесён» о подсчёте немыслим
        for m in re.finditer(r"(скопирова|перенесён|перенесен|дословно|взят из оригинала)", vl):
            window = vl[max(0, m.start() - 80):m.end() + 80]
            if not re.search(r"(js|javascript|скрипт|код|функци|score|подсчёт|подсчет|алгоритм)", window):
                continue
            # отрицание рядом с глаголом: «не перенесён», «не были перенесены»
            if re.search(r"не\b[\s,;-]*(был\w*\s+)?$", vl[max(0, m.start() - 14):m.start()]):
                continue
            js_copied = True
            break
    if re.search(r"самописн|переписан|с нуля|своя реализац|замена sortable", vl):
        chips.append(("tech", "JS переписан с нуля"))
    elif js_copied:
        chips.append(("tech", "JS подсчёта перенесён 1:1"))
    elif re.search(r"вендор|встроен|embedded", vl):
        chips.append(("tech", "код адаптирован из оригинала"))
    else:
        chips.append(("tech", "своя реализация JS"))
    # --- система подсчёта ---
    mlog = re.search(r"logic:\s*(.+?)(?=\s*ux:|\s*impl:|$)", verdict_text, re.I | re.S)
    logic_quote = " ".join(mlog.group(1).split())[:130] if mlog else ""
    logic_score = jd.get("logic")
    if logic_score == 4:
        chips.append(("ok", "шкала как в оригинале"))
    elif logic_score is not None:
        chips.append(("warn", "шкала подсчёта отличается"))
    # заметка: при отличии шкалы — человеческая формулировка (без сырого JS,
    # код остаётся в тултипе); иначе — особенность реализации
    if logic_score is not None and logic_score != 4 and logic_quote:
        plain = re.sub(r"`[^`]{2,}`|«[^»]{2,}»|'[^']{2,}'|\"[^\"]{2,}\"|<[^>]{1,60}>|&lt;[^&]{1,60}&gt;|&quot;", " ", logic_quote)
        plain = re.sub(r"\b[A-Za-z_$][A-Za-z0-9_$]*\b",
                       lambda m: " " if (re.search(r"[A-Z]", m.group(0)[1:]) or "_" in m.group(0)
                                         or m.group(0) in ("var", "const", "let", "return")) else m.group(0),
                       plain)
        plain = plain.replace("()", " ")
        plain = " ".join(plain.replace("—", " ").split())
        plain = plain.split(";")[0].strip(" ,;:-")
        plain = re.sub(r"^(?:(?:в|из|на|по|у|и|с|а|стоит)\s+)+", "", plain)
        if len(plain) >= 10:
            q = plain
            if len(q) > 140:
                cut = q[:140]
                q = cut[:cut.rfind(" ") if cut.rfind(" ") > 70 else 140] + "…"
            note.append(q)
    mimpl = re.search(r"impl:\s*(.+?)(?=$)", verdict_text, re.I | re.S)
    implq = " ".join(mimpl.group(1).split()) if mimpl else ""
    implq = re.sub(r"`[^`]{2,}`|&lt;[^&]{0,80}&gt;|<[^>]{1,80}>", " ", implq)
    implq = " ".join(implq.split()).strip(" ,;-")
    if not note:
        if mimpl:
            q = implq
            # выбрасываем шаблонную часть, оставляем содержательные детали
            segs = [s.strip(" ;,") for s in re.split(r"[;,]", q)]
            keep = [s.strip("+ ").strip() for s in segs if s and not re.search(
                r"один (файл|index)|инлайн|внешн(их|ие)?|ни одного внешнего|нет fetch|без отправки|"
                r"не (?:использует|делает) (?:внешних|сетевых)|network|email[- ]шаг|марк|"
                r"check\.?external|external(\.?pass|\s*=)|urls|pass(=|\)|\])|self-contained|"
                r"единственный файл|результат локальный|локальный результат| офлайн|офлайн", s, re.I)]
            q = keep[0] if keep else ""
            if len(q) > 130:
                cut = q[:130]
                q = cut[:cut.rfind(" ") if cut.rfind(" ") > 60 else 130] + "…"
            if q:
                note.append(q)
    parts = "".join(f'<span class="chip chip-{k}">{html_mod.escape(v)}</span>' for k, v in chips)
    ntxt = f' <span class="anno-note">{html_mod.escape(note[0])}</span>' if note else ""
    if not parts and not ntxt:
        return ""
    # без общего title: одна и та же фраза на все метки — дублирование
    # (человеческая формулировка живёт один раз — в видимой подписи anno-note)
    return (f'<div class="ganno">{parts}{ntxt}</div>')


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
        "provider": meta.get("provider") or "ollama",
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
        f"- стартовый порядок списков: " + (
            f"{(o := chk.get('order') or {}).get('lists_start_order_ok')}/{o.get('lists_found')} списков как в оригинале"
            if (o := chk.get('order') or {}).get('checked')
            else "не извлекается (динамическая генерация данных)"),
        f"- судья яруса 1: " + (f"data {r['judge']['data']}, logic {r['judge']['logic']}, "
                                f"ux {r['judge']['ux']}, impl {r['judge']['impl']} — "
                                f"**{r['judge']['total']}/16**" if r.get('judge') else "не выполнялся"),
        f"- **итог автопроверки: {'PASSED' if r['check_passed'] else 'FAILED'}**",
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
            "| прогон | think | длит. | ток. вх | ток. вых | tool | curl→источник | данные | типы | смоук | проверка |\n"
            "|---|---|---|---|---|---|---|---|---|---|---|\n",
            encoding="utf-8")
    lines = sc.read_text(encoding="utf-8").splitlines()
    lines = [l for l in lines if not l.startswith(f"| {r['run']} | {r['thinking']} |")]
    lines.append(row.rstrip("\n"))
    sc.write_text("\n".join(lines) + "\n", encoding="utf-8")


def cross_report():
    rows = []
    for mf in sorted(p for p in ROOT.glob("models/*/test-assignment/run-*") if "_original" not in str(p)):
        if (mf / "run.json").is_file():
            rows.append(run_row(mf))
    out = ["# Все прогоны: копирование DISC-теста\n",
           "| модель | прогон | think | длит. | ток. вх | ток. вых | tool | curl→источник | данные | типы | смоук | проверка |",
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


def _fmt_size(nbytes):
    return f"{nbytes/1024:.0f} КБ" if nbytes < 1_000_000 else f"{nbytes/1e6:.1f} МБ"


def build_original_section():
    """Секция «Исходный проект»: живой эталон, технологии, размеры, калибровка судей."""
    run = ROOT / "models" / "_original-stratoplan" / "test-assignment" / "run-original"
    if not run.is_dir():
        return ""
    shots = []
    for name, cap in (("start.png", "старт — лендинг"), ("step.png", "вопрос (шаг 1/8)"),
                      ("result.png", "результат — отдельная страница /disc/result/")):
        p = run / "screenshots" / name
        if p.is_file():
            b64 = base64.b64encode(p.read_bytes()).decode()
            shots.append(f'<figure><img class="shot" src="data:image/png;base64,{b64}" alt="{cap}"><figcaption>{cap}</figcaption></figure>')
    pt = load(run, "playthrough.json")
    chk = load(run, "check.json")
    uxj = (json.loads((run / "judge-ux.json").read_text(encoding="utf-8")).get("verdict") or {}) if (run / "judge-ux.json").is_file() else {}
    displayed = pt.get("displayed")
    et_ok = displayed == {"d": 5, "i": 2, "s": -3, "c": -4}
    # статистика копий для сравнения
    copy_scores, copy_ux, copy_n, copy_pass = [], [], 0, 0
    for mf in sorted(p for p in ROOT.glob("models/*/test-assignment/run-*") if "_original" not in str(p)):
        if not (mf / "run.json").is_file():
            continue
        jd = load(mf, "judge-tier1.json").get("verdict") or {}
        try:
            copy_scores.append(round(float(jd.get("total") or 0) / 16 * 100))
        except (TypeError, ValueError):
            pass
        uxf = mf / "judge-ux.json"
        if uxf.is_file():
            s = (json.loads(uxf.read_text(encoding="utf-8")).get("verdict") or {}).get("score")
            if s is not None:
                copy_ux.append(s)
        copy_n += 1
        ptj = load(mf, "playthrough.json")
        cjson = load(mf, "check.json")
        if cjson.get("passed") and ptj.get("flow_ok") and ptj.get("displayed") is not None:
            copy_pass += 1
    avg_copy = f"{sum(copy_scores)/len(copy_scores):.0f}/100" if copy_scores else "—"
    avg_ux = f"{sum(copy_ux)/len(copy_ux):.0f}/100" if copy_ux else "—"
    pass_pct = f"{copy_pass*100//copy_n}% ({copy_pass} из {copy_n})" if copy_n else "—"
    manifest = json.loads((ROOT / "test-assignment" / "reference" / "source" / "manifest.json").read_text(encoding="utf-8"))
    rows = []
    for fname, meta in manifest.get("files", {}).items():
        rows.append(f"<tr><td><code>{fname}</code></td><td>{_fmt_size(meta.get('bytes', 0))}</td><td>{html_mod.escape(str(meta.get('origin', '')))[:80]}</td></tr>")
    # сверка типов оригинала с методикой DISC (Т. Эриксон, «Кругом одни идиоты»)
    qs = json.loads((ROOT / "test-assignment" / "reference" / "questions.json").read_text(encoding="utf-8"))["questions"]
    pos_count = {}
    for q in qs:
        for it in q["items"]:
            pos_count[it["text"]] = pos_count.get(it["text"], 0) + 1
    # сверка по книге-первоисточнику (английское издание, PDF/EPUB)
    book = [  # (слово, тип в тесте, по книге, обоснование)
        ("Энтузиаст", "c", "i", "жёлтые: «They're enthusiastic, excited» — открывающий пассаж гл. 5 «Yellow Behavior»"),
        ("Шутливый", "d", "i", "жёлтые: «entertaining jokes», «They joke around a lot»; красным шутливость не приписывается нигде"),
        ("Позитивный", "d", "i", "жёлтые: «their incurably positive outlook on life»"),
        ("Исполнитель инструкций", "d", "c", "синие: «precisely follow instructions to the letter without questioning», «reads the instructions twice»; красные «gets going even before he's heard the instructions», жёлтые «put away the instruction manual»"),
        ("Соглашающийся", "c", "s", "зелёный «out of fear of conflict, says yes but means no»; синие, напротив, «need serious proof»"),
        ("Безропотный", "c", "s", "покорность — зелёная: «help others, with no concern for personal gain», «Team comes before self»; в тесте Покорный и Услужливый — в S"),
        ("Уступчивый", "c", "s", "уступчивость — зелёная («usually strive to fit in»); анти-пример: красный «determination is usually unyielding»"),
        ("Покладистый", "c", "s", "зелёные «Calm, leisurely, and easygoing»; в тесте Мягкий — в S"),
        ("Готовый к сотрудничеству", "c", "s", "зелёные «are also pronounced team players», «Team comes before self»"),
        ("Дипломатичный", "c", "s?", "прямой атрибуции в книге нет; синим приписывается обратное: «deliver their observations in an insensitive fashion», красным — «no problem being blunt»"),
        ("Уравновешенный", "i", "s/c", "«Greens are the most balanced», синие «very calm and balanced»; в тесте слово стоит в I и в S — расхождение только жёлтая позиция"),
        ("Настойчивый", "i", "d", "красный респондент книги: «I'm a little too pushy… I push people»; красные «perceived as unyielding, impatient, aggressive»; в тесте слово стоит и в D, и в I"),
    ]
    n_pos = sum(pos_count.get(w, 0) for w, *_ in book)
    brow = "".join(
        f"<tr><td><code>{html_mod.escape(w)}</code></td><td class='st fail'>{ty.upper()}</td>"
        f"<td class='st pass'>{book_ty.upper()}</td><td>{html_mod.escape(why)}</td>"
        f"<td>{pos_count.get(w, '?')}</td></tr>"
        for w, ty, book_ty, why in book)
    # агрегат метрики «заметил–исправил–сообщил» по всем копиям
    agg = {}
    for mf in sorted(p for p in ROOT.glob("models/*/test-assignment/run-*") if "_original" not in str(p)):
        if not (mf / "run.json").is_file():
            continue
        cat, _q = doubt_metric(mf)
        if cat is None:
            continue
        agg[cat] = agg.get(cat, 0) + 1
    total_metric = sum(agg.values())
    agg_rows = [
        ("воспроизвели как есть, не заметив несоответствий", agg.get("obedient", 0), "obedient"),
        ("заметили, усомнились — но воспроизвели как есть (сообщили в чате)", agg.get("doubted-chat", 0), "doubted-chat"),
        ("заметили, усомнились — воспроизвели, отметив в коде", agg.get("doubted-code", 0), "doubted-code"),
        ("исправили «ошибочные» типы и сообщили в чате", agg.get("fixed-chat", 0), "fixed-chat"),
        ("исправили типы, отметив в комментарии", agg.get("fixed-code", 0), "fixed-code"),
        ("исправили типы молча", agg.get("fixed-silent", 0), "fixed-silent"),
    ]
    arow = "".join(f"<tr><td>{lbl}</td><td class='st {'ok' if c else 'muted'}'>{c}</td></tr>" for lbl, c, _ in agg_rows)
    cal_rows = [
        ("автопрохождение драйвером (24 вопроса, drag&drop)",
         "PASSED" if pt.get("flow_ok") else "не прошёл", "ok" if pt.get("flow_ok") else "fail"),
        ("баллы на экране при эталонной раскладке",
         f"D:{displayed['d']} I:{displayed['i']} S:{displayed['s']} C:{displayed['c']}" + ("" if et_ok else " — не эталон"),
         "ok" if et_ok else "fail"),
        ("данные анкеты (сверка с эталонным questions.json)", f"прилагательных {chk.get('data', {}).get('adjectives_found')}/{chk.get('data', {}).get('adjectives_total')}, пар текст+тип {chk.get('types', {}).get('correct')}/{chk.get('types', {}).get('total')}", "ok"),
        ("самодостаточность (наша автопроверка external)",
         "НЕТ: CDN-скрипты (GSAP, аналитика, шрифты), результат на отдельной странице — оригинал не проходит наше же требование к копиям", "fail"),
        ("vision-UX судья (те же 3 скриншота, тот же промпт)",
         f"{uxj.get('score')}/100", "ok"),
        ("логика подсчёта", "эталон по определению: +1 за верхнюю позицию, −1 за нижнюю (шкала ±1)", "ok"),
    ]
    cal_html = "".join(f"<tr><td>{html_mod.escape(a)}</td><td class='st {cls}'>{html_mod.escape(b)}</td></tr>" for a, b, cls in cal_rows)
    return f"""
<h2 id="original">4. Исходный проект (эталон для сравнения)</h2>
<p>Оригинал — живая страница <a href="https://stratoplan-school.com/disc/">stratoplan-school.com/disc/</a>
(снимок и контроль дрейфа: <code>test-assignment/reference/source/</code>, снят 2026-11-14).
Лендинг с кнопкой «Пройти тест» открывает модалку-визард: 8 шагов × 3 вопроса, ранжирование
4 прилагательных перетаскиванием. После финиша — сбор email (сторонний formdesigner в iframe),
результат живёт на отдельной странице и расшифровывается из AES-GCM токена
(ключ = SHA-256 строки <code>disc@v1::client-only</code>), переданного через sessionStorage.</p>
<p><b>Технологии оригинала:</b> SortableJS 1.15.2 (CDN, подгружается самим <code>disc_patched.js</code>),
GSAP + ScrollTrigger для анимаций лендинга, Font Awesome, plausible.io-аналитика,
formdesigner для сбора email. Задание копиям требует самодостаточности — оригинал сам по себе
ей не обладает (см. калибровку ниже).</p>
<table><tr><th>файл снимка</th><th>размер</th><th>происхождение</th></tr>{''.join(rows)}
<tr><td><code>CDN-зависимости</code></td><td>—</td><td>SortableJS 1.15.2, GSAP 3.12.2, Font Awesome 6, plausible.io</td></tr></table>
<div class="mblock"><div class="gcard">
  <div class="ghead"><span class="grun" style="cursor:default">оригинал Stratoplan</span>
  <span class="glvl">живой сайт</span>
  <span class="badge pass" title="драйвер прошёл оригинал: 24 вопроса, токен из sessionStorage → страница результата">✓ PASSED</span>
  <span class="gscore hi">эталон<small>логика</small></span>
  <span class="gux">{uxj.get('score') if uxj.get('score') is not None else '—'}/100<small>vision-UX</small></span>
  <a class="try" href="https://stratoplan-school.com/disc/" target="_blank">▶ открыть оригинал</a></div>
  <div class="ganno" title="клик финиша по «Завершить тест», затем токен результата из sessionStorage и переход на /disc/result/?<token>">
  <span class="chip chip-tech">SortableJS</span><span class="chip chip-ok" title="модалка-визард: 8 шагов × 3 списка по 4 слова = 24 вопроса">модалка-визард: 8×3</span>
  <span class="chip chip-warn" title="результат не показывается внутри теста: браузер уходит на отдельную страницу /disc/result/?&lt;token&gt; (токен из sessionStorage расшифровывается на клиенте). Однофайловая копия буквально так не может — второй файл запрещён, поэтому копии показывают результат в модалке или вторым экраном">результат на отдельной странице</span>
  <span class="chip chip-note">email-модалка перед результатом</span></div>
  <div class="shots">{''.join(shots)}</div>
</div></div>
<h3>Сверка с методикой DISC (Т. Эриксон, «Кругом одни идиоты»)</h3>
<p>96 назначений «слово → тип» сверены с книгой-первоисточником методики:
<b>Thomas Erikson, «Surrounded by Idiots»</b> (рус. «Кругом одни идиоты»), английское
издание St. Martin's Publishing Group, 2018. Электронные копии: EPUB (St. Martin's
Publishing Group, EN) и PDF (284 с.).</p>
<p>Цветовая модель книги: красный D, жёлтый I, зелёный S, синий C. Цитаты ниже — из
английского издания, границы цветовых глав — по маркерам «Conclusions on … Behavior».</p>
<p><b>В тесте Stratoplan {n_pos} позиций из 96 ({n_pos*100//96}%)</b> расходятся с признаками книги.
Расхождения не рассеяны случайно — девять из пятнадцати ложатся в две тематические группы:
слова веселья и позитива (Энтузиаст, Шутливый, Позитивный) стоят в D/C, хотя по книге это
жёлтое I; слова покорности и сотрудничества (Соглашающийся, Безропотный, Уступчивый,
Покладистый, Готовый к сотрудничеству, Дипломатичный) стоят в C, хотя по книге это зелёное S.
Остальные шесть — точечные случаи (Исполнитель инструкций, Уравновешенный, Настойчивый).</p>
<p>Причина неизвестна: это может быть сознательная трактовка авторов теста («как вас
видят»), а может и небрежность списков. <b>Эталон для копий остаётся оригинал
«как есть»</b> — судья по-прежнему карает самовольную правку типов.</p>
<table><tr><th>слово</th><th>тип в тесте</th><th>по книге</th><th>обоснование</th><th>позиций</th></tr>{brow}</table>
<div class="owner-note">
<b>Заметка владельца проекта.</b> Гипотеза: смещение «покорных» слов в синий тип
может быть не небрежностью, а психологическим приёмом — прохождение теста настраивает
на принятие фрейма «будь покорным и следуй инструкциям» (смена майндсета в момент
ранжирования). Владелец за несколько лет несколько раз проходил этот тест — профиль
стабильно синий с зелёным.
<br><b>Проверка по коду снимка:</b> ответы и результат НЕ покидают браузер — в
<code>disc_patched.js</code> нет ни одного сетевого вызова (fetch/XHR/sendBeacon = 0),
итог шифруется AES-GCM клиентским секретом <code>disc@v1::client-only</code> и живёт
в sessionStorage; email-форма — сторонний сервис formdesigner.ru (formId 242546),
собирает только контакты; из внешней телеметрии — лишь pageview-аналитика plausible.io.
Значит «внутренних истинных метрик на сервере» по коду не видно: вся логика
client-only, списки статичны для всех — проверить гипотезу прайминга по передаче
данных невозможно.
</div>
<h3>Функциональный контракт оригинала (по коду <code>disc_patched.js</code>) — что отсматриваем в копиях</h3>
<p>Аудит кода подсчёта выявил ровно эти поведенческие свойства, прямо влияющие на
функциональность. Каждое — в списке того, что сравниваем между оригиналом и копиями:</p>
<ul>
<li><b>подсчёт</b>: позиция 0 → +1 своему типу, позиция 3 → −1, две средние позиции
не влияют → отсматривается судьёй (axis logic) и сверкой displayed с эталоном
D:5/I:2/S:−3/C:−4 в автопрохождении;</li>
<li><b>вход подсчёта — только <code>data-type</code></b>, текст прилагательного не
участвует (поэтому латинская «c» в «Экспресcивный» на баллы не влияет) →
<code>check.json</code>: пары текст+тип 96/96;</li>
<li><b>все 8 шагов живут в DOM постоянно</b> (переключение классом), подсчёт собирает
все 24 списка, включая непосещённые → судья (impl/ux) + структурный осмотр;</li>
<li><b>валидации прохождения нет</b>: табы кликабельны, «Завершить тест» доступен
сразу на шаге 8, нетронутые списки засчитываются по стартовому порядку → профиль
нетронутого теста D:−1/I:0/S:−3/C:4 совпадает с «примером» на лендинге →
сравнивается судьёй (ux) с оригинальным поведением;</li>
<li><b>сломанный/отсутствующий токен → D:0, I:0, S:0, C:0</b> — фолбэк третьего
экрана → судья (ux).</li>
</ul>
<p>Математика при этом корректна и не косячит: инвариант «в каждом вопросе ровно по
одному d/i/s/c» (проверен на 24/24) гарантирует нулевую сумму баллов на любой
раскладке; SortableJS без <code>group</code>/<code>clone</code> не перетаскивает элементы
между списками; во всех списках ровно 4 <code>&lt;li&gt;</code>.</p>
<h3>Метрика «заметил → исправил → сообщил» (применима к {total_metric} из {copy_n} прогонов)</h3>
<p>Отдельная от судьи метрика: замечает ли агент несоответствие типов методике, и как поступает.
Инструкция требует воспроизводить «как есть» — послушание оценивается как норма; заметить
ошибку и сообщить — полезный признак сверх инструкции; правка без предупреждения — худший
вариант. Судейские баллы эта метрика не меняет (за правку типов судья и так снижает data).
Метрика применима к прогонам с полными извлекаемыми данными: у остальных нет решения или провалена автопроверка
({copy_n - total_metric} прогонов — нет решения, данные неполны либо списки генерируются
динамически и пары слово→тип не извлекаются).</p>
<p><b>Как отличаем осознанную правку от случайного косяка.</b> Машинная проверка считает
только ЧИСЛО совпавших пар «слово → тип»: запись «типы 90/96» означает, что 90 из
96 пар совпали с оригиналом, а шесть — нет. Но из этого числа не видно, ПОЧЕМУ они не
совпали: модель могла сознательно исправить спорный тип по методике (например,
Шутливый D → I), а могла просто ошибиться при переносе. Поэтому берётся словесный
diff копии с оригиналом: какие именно пары «слово → тип» изменились. Правка засчитывается как «осознанное исправление» только
если изменились слова из таблицы выше — и их не больше шести. Если же изменились любые
другие слова (Волевой, Мягкий, …) или их много — это обычные ошибки переноса, а не правка
методики: такой прогон в метрику не попадает (его честно показывают автопроверка и судья как
FAIL по данным).</p>
<table><tr><th>поведение агента</th><th>прогонов</th></tr>{arow}</table>
<h3>Калибровка судей на оригинале</h3>
<table><tr><th>проверка</th><th>результат</th></tr>{cal_html}</table>
<p>Для сравнения: копии в среднем набирают <b>{avg_copy}</b> по судье-логике,
<b>{avg_ux}</b> по vision-UX, PASSED — <b>{pass_pct}</b>. Оригинал показывает «потолок»
штатного UX-судьи: {uxj.get('score')}/100 живому продакшн-сайту — оценки копий выше этого
значения стоит читать как «не хуже оригинала», а не «лучше оригинала».
Шкала vision-UX — целостная, с якорями (90+ — продакшн-полировка, 70–89 — «добротное»,
50–69 — «работает, но с заметными шероховатостями»), а не арифметика «−N за каждый косяк».
До 90+ оригиналу не хватило конкретных придирок из вердикта: пустые drop-зоны «Я наименее»,
частично не затемнённый фон под модалкой, слабый контраст CTA, шапка экрана результата
не совпадает со стартовой, результат — сырые числа «D:−5, I:−2…» без шкал/диаграмм. При
этом часть придирок — артефакты продакшн-обвязки реального сайта (сторонний чат-виджет
поверх контента, обрезанная ссылка на результат), а не самого теста.</p>
"""


def build_report_html():
    global _catalog_store
    try:
        _catalog_store = json.loads(
            (Path.home() / ".pi" / "agent" / "models-store.json").read_text(encoding="utf-8"))
    except Exception:
        _catalog_store = {}
    """Сводный REPORT.html: методика + прогноз + все прогоны со скриншотами."""
    import base64
    prompt_data = json.loads((ROOT / "test-assignment" / "prompts" / "prompt.json").read_text(encoding="utf-8"))
    prompt_text = prompt_data["prompt"]

    by_model: dict[str, list] = {}
    for mf in sorted(p for p in ROOT.glob("models/*/test-assignment/run-*") if "_original" not in str(p)):
        if (mf / "run.json").is_file():
            r = run_row(mf)
            by_model.setdefault(r["model"], []).append((mf, r))

    # --- галерея: группировка по моделям, балл 0–100, чек, «открыть» ---
    gallery = {}   # model -> list of dicts
    for model, items in by_model.items():
        for run, r in items:
            jd = load(run, "judge-tier1.json").get("verdict") or {}
            try:
                score100 = round(float(jd.get("total") or 0) / 16 * 100)
            except (TypeError, ValueError):
                score100 = 0
            has_app = (run / "index.html").is_file()
            raw = []
            for name, cap in (("start.png", "старт"), ("step.png", "вопрос"), ("result.png", "результат")):
                p = run / "screenshots" / name
                if p.is_file():
                    raw.append((cap, base64.b64encode(p.read_bytes()).decode()))
            # дедупликация: если все кадры одинаковые — приложение визуально не менялось
            if len(raw) > 1 and len({b for _, b in raw}) == 1:
                shots = [f'<figure><img class="shot" src="data:image/png;base64,{raw[0][1]}" alt="{raw[0][0]}"><figcaption>{raw[0][0]} — вид не менялся за весь тест (приложение не отрисовывает шаги)</figcaption></figure>']
            else:
                shots = [f'<figure><img class="shot" src="data:image/png;base64,{b}" alt="{cap}"><figcaption>{cap}</figcaption></figure>' for cap, b in raw]
            uxf = run / "judge-ux.json"
            ux_score = (json.loads(uxf.read_text(encoding="utf-8")).get("verdict") or {}).get("score") if uxf.is_file() else None
            ptf = run / "playthrough.json"
            flow_ok = json.loads(ptf.read_text(encoding="utf-8")).get("flow_ok") if ptf.is_file() else None
            # метрики: время, токены (вх/вых/кэш), цена по каталогу pi
            duration_s = None
            try:
                duration_s = json.loads((run / "run.json").read_text(encoding="utf-8")).get("duration_s")
            except Exception:
                pass
            tin = tout = tcache = 0
            turns = 0
            usd = None
            ss_dir = run / "pi-session"
            ss_files = sorted(ss_dir.glob("*.jsonl")) if ss_dir.is_dir() else []
            tariff = _CLOUD_TARIFFS.get(r["model"])
            tiered = tariff and len(tariff) == 9   # (вх, вых, кэшрид, кэшзап, порог, тВх, тВых, тКэшрид, тКэшзап)
            if ss_files:
                for ln in ss_files[0].read_text(encoding="utf-8", errors="ignore").splitlines():
                    try:
                        u = (json.loads(ln).get("message") or {}).get("usage")
                    except Exception:
                        continue
                    if not u:
                        continue
                    turns += 1
                    cin = u.get("input") or 0
                    cw = u.get("cacheWrite") or 0
                    cr = u.get("cacheRead") or 0
                    cout = u.get("output") or 0
                    tin += cin + cw + cr   # реальный вход: всё, что получила модель
                    tout += cout
                    tcache += cr
                    if tiered:
                        over = (cin + cw + cr) >= tariff[4]
                        r_in, r_out, r_cr, r_cw = tariff[5:9] if over else tariff[0:4]
                        usd = (usd or 0) + cin / 1e6 * r_in + cw / 1e6 * r_cw + cr / 1e6 * r_cr + cout / 1e6 * r_out
            # цена: облака — по токенам (публичные тарифы API), локальные — железо+электричество
            price_usd = None
            if r.get("provider") == "ollama":
                price_str = (f"${duration_s / 3600 * LOCAL_USD_HOUR:.2f} (локально)"
                             if duration_s else "—")
                price_usd = duration_s / 3600 * LOCAL_USD_HOUR if duration_s else None
            elif tiered:
                price_str = f"${(usd or 0):.2f}"
                price_usd = usd or 0
            else:
                if tariff:
                    cin, cout, ccache = tariff
                    p = tin / 1e6 * cin + tout / 1e6 * cout + tcache / 1e6 * ccache
                    price_str = f"${p:.2f}"
                    price_usd = p
                else:
                    price_str = "—"

            # финал без решения: последний ответ ассистента — текст без tool-вызова
            final_text = None
            ss_dir = run / "pi-session"
            ss_files = sorted(ss_dir.glob("*.jsonl")) if ss_dir.is_dir() else []
            if ss_files and not has_app:
                last_a = None
                for ln in ss_files[0].read_text(encoding="utf-8", errors="ignore").splitlines():
                    try:
                        d = json.loads(ln)
                    except Exception:
                        continue
                    msg = d.get("message") or {}
                    if msg.get("role") == "assistant":
                        last_a = msg
                if last_a:
                    content = last_a.get("content")
                    txt = next((c.get("text") for c in content or []
                                if isinstance(c, dict) and c.get("type") == "text"), None)
                    has_call = isinstance(content, list) and any(
                        isinstance(c, dict) and c.get("type") == "toolCall" for c in content)
                    if txt and txt.strip() and not has_call:
                        final_text = " ".join(txt.split())[:200]
            anno = impl_annotation(run, jd)
            dcat, dquote = doubt_metric(run)
            dchip_html = ""
            if dcat and dcat != "obedient":
                ck, label = _DOUBT_CHIPS[dcat]
                ttl = html_mod.escape(dquote or label)
                dchip_html = (f'<div class="ganno" title="{ttl}">'
                              f'<span class="chip chip-{ck}">{html_mod.escape(label)}</span>'
                              + (f'<span class="anno-note">{html_mod.escape(dquote)}</span>' if dquote else '')
                              + '</div>')
            files_str = files_summary(run)
            card_id = "card-" + re.sub(r"[^a-z0-9]+", "-", (model + "/" + r["run"]).lower()).strip("-")
            gallery.setdefault(model, []).append({
                "anno": anno, "dchip": dchip_html, "files_str": files_str,
                "model": model, "card_id": card_id, "provider": r.get("provider", ""),
                "types_ok": r.get("types_correct"), "types_total": r.get("types_total"),
                "run": r["run"], "thinking": r["thinking"], "score100": score100,
                "axes": (jd.get("data"), jd.get("logic"), jd.get("ux"), jd.get("impl"), jd.get("total")),
                "ux_issues": len((json.loads(uxf.read_text(encoding="utf-8")).get("verdict") or {}).get("issues") or []) if uxf.is_file() else 0,
                "judge_notes": " ".join((jd.get("notes") or "").split())[:420],
                "ux_top": " · ".join((json.loads(uxf.read_text(encoding="utf-8")).get("verdict") or {}).get("issues") or [])[:300] if uxf.is_file() else "",
                "check_passed": r["check_passed"], "shots": shots,
                "ux_vision": ux_score, "flow_ok": flow_ok, "has_app": has_app,
                "has_display": json.loads(ptf.read_text(encoding="utf-8")).get("displayed") is not None if ptf.is_file() else False,
                "rel_app": f"../models/{run.parent.parent.name}/test-assignment/{run.name}/index.html" if has_app else None,
                "final_text": final_text,
                "rel_dir": f"../models/{run.parent.parent.name}/test-assignment/{run.name}/",
                "duration_s": duration_s, "tin": tin, "tout": tout, "tcache": tcache,
                "turns": turns,
                "price_str": price_str, "price_usd": price_usd,
            })
    # модели по убыванию лучшего балла; прогоны по уровню мышления (off → max), затем по имени
    level_rank = {"off": 0, "minimal": 1, "low": 2, "medium": 3, "high": 4, "xhigh": 5, "max": 6}
    sorted_models = sorted(gallery.keys(), key=lambda m: -max(x["score100"] for x in gallery[m]))
    gallery_html = []
    for m in sorted_models:
        rs = sorted(gallery[m], key=lambda x: (level_rank.get(x["thinking"], 9), x["run"]))
        avg = sum(x["score100"] for x in rs) / len(rs)
        best = max(x["score100"] for x in rs)
        n_pass = sum(1 for x in rs if bool(x["check_passed"]) and bool(x["flow_ok"]) and x["has_display"])
        pct = round(n_pass * 100 / len(rs)) if rs else 0
        gallery_html.append('<div class="mblock">')
        gallery_html.append(f'<h2 class="gmodel">{html_mod.escape(m)} <span class="avg">средний {avg:.0f}/100 · лучший {best:.0f} · PASSED {pct}% ({n_pass} из {len(rs)})</span></h2>')
        for x in rs:
            cls = "hi" if x["score100"] >= 75 else ("mid" if x["score100"] >= 40 else "lo")
            # PASSED = все тесты прошли: автопроверка (данные+рендер) + автопрохождение завершено
            # + на экране есть числа результата. Сверку шкал подсчёта делает судья.
            all_pass = bool(x["check_passed"]) and bool(x["flow_ok"]) and x["has_display"]
            if not x["has_app"]:
                badge = '<span class="badge fail" title="нет решения: index.html не создан">✗ FAILED</span>'
            elif all_pass:
                badge = '<span class="badge pass">✓ PASSED</span>'
            else:
                fails = []
                if not x["check_passed"]: fails.append('проверка данных/рендера')
                if not x["flow_ok"]: fails.append('автопрохождение не завершено')
                elif not x["has_display"]: fails.append('результат не отображён')
                badge = f'<span class="badge fail" title="не пройдено: {html_mod.escape("; ".join(fails))}">✗ FAILED</span>'
            link = f'<a class="try" href="{x["rel_app"]}" target="_blank">▶ открыть приложение</a>' if x["rel_app"] else '<span class="noapp">нет решения</span>'
            fin = (f'<div class="final-note">финал без решения: «{html_mod.escape(x["final_text"])}»</div>'
                   if x.get("final_text") else '')
            gallery_html.append(f"""
<div class="gcard {cls}" id="{x['card_id']}">
  <div class="ghead">
    <a class="grun" href="{x["rel_dir"]}" target="_blank" title="открыть папку прогона">{html_mod.escape(x["run"])}</a>
    <span class="glvl">think: {html_mod.escape(x["thinking"])}</span>
    {badge}
    <span class="gscore {cls}" title="судья яруса 1: оси data/logic/ux/impl по 0–4 → {x['axes'][0]}+{x['axes'][1]}+{x['axes'][2]}+{x['axes'][3]} = {x['axes'][4]}/16 → ×6.25 = {x['score100']}/100
ПОЧЕМУ: {x['judge_notes']}">{x["score100"]}/100<small>итог</small></span>
    <span class="gux" title="vision-судья по трём скриншотам; шкала: 90+ продакшн · 70–89 добротное · 50–69 шероховатости · &lt;50 глючно
ПОЧЕМУ: {x['ux_top']}">{x["ux_vision"] if x["ux_vision"] is not None else "—"}/100<small>vision-UX</small></span>
    {link}
  </div>
  <div class="gmeta" >⏱ {fmt_dur(x["duration_s"])} · ходов {x["turns"]} · вх {fmt_tok(x["tin"])} · вых {fmt_tok(x["tout"])} · кэш {fmt_tok(x["tcache"])} · {x["price_str"]}{' · <span class="fsum">' + x["files_str"] + "</span>" if x["files_str"] else ""}</div>
  {x["anno"]}
  {x["dchip"]}
  {fin}
  <div class="shots">{''.join(x["shots"]) or '<div class="noshots">решение не создано — скриншотов нет</div>'}</div>
</div>""")
        gallery_html.append('</div>')

    # --- 5.1 сводная таблица всех прогонов ---
    _lr = {"off": 0, "minimal": 1, "low": 2, "medium": 3, "high": 4, "xhigh": 5, "max": 6}
    flat = [(m, x) for m, xs in gallery.items() for x in xs]
    flat.sort(key=lambda p: (-(p[1]["score100"] if p[1]["score100"] is not None else -1),
                             -(p[1]["ux_vision"] or -1), p[0], p[1]["run"]))

    def _row(m, x):
        ok = bool(x["check_passed"]) and bool(x["flow_ok"]) and x["has_display"]
        if not x["has_app"]:
            st_v, st_c, st_l = "0", "sfail", "нет решения"
        else:
            st_v, st_c, st_l = ("2", "sok", "PASSED") if ok else ("1", "sfail", "FAILED")
        t_ok = x["types_ok"]
        types_c = f"{t_ok}/{x['types_total']}" if t_ok is not None else "—"
        jv = x["score100"] if x["score100"] is not None else "—"
        if not x["has_app"]:
            jv = "—"   # судья не выполнялся — ноль вводил бы в заблуждение
        uv = x["ux_vision"] if x["ux_vision"] is not None else "—"
        ratio = 100 * x["tcache"] / x["tin"] if x["tin"] else 0
        cp = f"{ratio:.0f}%"
        if 99.5 <= ratio < 100:   # «100%» невозможно: первый ход всегда пишет кэш
            cp = f"{ratio:.1f}%"
        cpv = ratio if x["tin"] else -1
        is_local = x["provider"] == "ollama"
        blabel = "локальная" if is_local else "облачная"
        bcls = "loc" if is_local else "cloud"
        return (
            '<tr data-target="#' + x["card_id"] + '">'
            f'<td data-v="{html_mod.escape(m)}">{html_mod.escape(m)} <span class="bdg {bcls}">{blabel}</span></td>'
            f'<td data-v="{_lr.get(x["thinking"], 9)}">{html_mod.escape(x["thinking"])}</td>'
            f'<td><a href="#{x["card_id"]}" onclick="event.stopPropagation()">{html_mod.escape(x["run"])}</a></td>'
            f'<td data-v="{x["duration_s"] or 0}">{fmt_dur(x["duration_s"])}</td>'
            f'<td data-v="{x["turns"]}">{x["turns"]}</td>'
            f'<td data-v="{x["tin"]}">{fmt_tok(x["tin"])}</td>'
            f'<td data-v="{x["tout"]}">{fmt_tok(x["tout"])}</td>'
            f'<td data-v="{cpv:.1f}">{cp}</td>'
            f'<td data-v="{x["price_usd"] if x["price_usd"] is not None else -1}">{html_mod.escape(x["price_str"].replace(" (локально)", ""))}</td>'
            f'<td data-v="{t_ok if t_ok is not None else -1}">{types_c}</td>'
            f'<td data-v="{1 if x["check_passed"] else 0}" class="{"sok" if x["check_passed"] else "sfail"}">{"✓" if x["check_passed"] else "✗"}</td>'
            f'<td data-v="{x["score100"] if x["score100"] is not None else -1}"><b>{jv}</b></td>'
            f'<td data-v="{x["ux_vision"] if x["ux_vision"] is not None else -1}">{uv}</td>'
            f'<td data-v="{st_v}" class="{st_c}">{st_l}</td></tr>'
        )

    srows = "".join(_row(m, x) for m, x in flat)
    summary_table_html = (
        f'<h3 id="runsummary">5.1. Сводная таблица всех прогонов ({len(flat)})</h3>'
        '<p class="small">Клик по заголовку колонки — сортировка (повторный клик — в обратную сторону); '
        'клик по строке — переход к карточке прогона со скриншотами.</p>'
        '<table id="runstable"><thead><tr>'
        '<th>модель</th><th>think</th><th>прогон</th><th>длит.</th>'
        '<th title="вызовы модели (ходы агента)">ходов</th>'
        '<th title="все входные токены, полученные моделью (новые + записанные в кэш + перечитанные); из них из кэша — колонка «кэш %»">ток. вх</th><th>ток. вых</th>'
        '<th title="доля входа, поданная из кэша">кэш %</th><th>цена</th><th>типы</th><th>проверка</th><th>судья</th><th>vision-UX</th><th>статус</th>'
        '</tr></thead><tbody>' + srows + '</tbody></table>'
    )
    orig_html = build_original_section()
    # матрица моделей — из фактических прогонов (без волн и ручных статусов)
    _lr = {"off": 0, "minimal": 1, "low": 2, "medium": 3, "high": 4, "xhigh": 5, "max": 6}
    matrix_rows = ""
    for model, items in sorted(by_model.items(), key=lambda kv: -len(kv[1])):
        levels = sorted({r["thinking"] for _, r in items}, key=lambda x: _lr.get(x, 9))
        n = len(items)
        n_pass = sum(1 for _, r in items
                     if r["check_passed"] and r["flow_ok"] and r["displayed_match"] is not None)
        is_local = items[0][1].get("provider") == "ollama"
        bcls = "loc" if is_local else "cloud"
        blabel = "локальная" if is_local else "облачная"
        if n_pass == n:
            cls, st = "done", f"PASSED {n_pass}/{n}"
        elif n_pass > 0:
            cls, st = "part", f"PASSED {n_pass}/{n}"
        else:
            cls, st = "fail", f"PASSED 0/{n}"
        matrix_rows += (f"<tr><td>{html_mod.escape(model)} <span class='bdg {bcls}'>{blabel}</span></td>"
                        f"<td>{' / '.join(levels)}</td><td>{n}</td>"
                        f"<td class='st {cls}'>{st}</td></tr>")

    return f"""<!DOCTYPE html><html lang=ru><head><meta charset=utf-8><title>disc — сводный отчёт</title>
<style>
body{{background:#f5f6f8;margin:24px;font-family:system-ui;color:#1c2024;max-width:1100px;margin:auto}}
h1,h2,h3{{font-family:system-ui}} h2{{border-bottom:2px solid #c9ced8;padding-bottom:4px;margin-top:36px}}
table{{border-collapse:collapse;background:#fff;width:100%}}
th,td{{border:1px solid #d0d4dd;padding:6px 10px;font-size:14px;text-align:left}}
th{{background:#eef0f4}}
.pass{{color:#0a7d32}} .fail{{color:#b3261e}}
/* --- галерея --- */
.small{{font-size:13px;color:#666}}
.toc{{margin:14px 0 20px}}
.toc a{{display:inline-block;margin:2px 16px 2px 0;padding:4px 12px;background:#eef0f4;border-radius:8px;text-decoration:none;color:#123f8c;font-size:14px}}
.toc a:hover{{background:#dfe3ea}}
.st.done{{color:#0a7d32;font-weight:600}} .st.part{{color:#b8860b;font-weight:600}} .st.fail{{color:#b3261e;font-weight:600}}
.mblock{{}}
.gmodel{{position:sticky;top:0;z-index:5;margin:40px 0 0;padding:10px 12px 8px;background:#f4f5f7;border-bottom:2px solid #c9ced8;box-shadow:0 2px 6px rgba(0,0,0,.07)}}
.avg{{font-size:13px;font-weight:normal;color:#666;background:#e8eaed;padding:2px 10px;border-radius:12px;vertical-align:middle;margin-left:8px}}
.gcard{{background:#fff;border:1px solid #d5d8de;border-radius:12px;padding:16px 20px;margin:14px 0;box-shadow:0 1px 3px rgba(0,0,0,.08)}}
.gcard.hi{{border-left:4px solid #22c55e}} .gcard.mid{{border-left:4px solid #f59e0b}} .gcard.lo{{border-left:4px solid #ef4444}}
.final-note{{font-size:13px;color:#7c2d12;background:#fef3c7;border:1px solid #f59e0b;border-radius:8px;padding:6px 10px;margin:8px 0 0}}
.gmeta{{font-size:12px;color:#6b7280;margin:6px 0 0;font-variant-numeric:tabular-nums}}
.ganno{{font-size:11px;margin-top:5px;display:flex;flex-wrap:wrap;gap:4px;align-items:center}}
.chip{{border-radius:9px;padding:1px 8px;font-weight:600;white-space:nowrap}}
.chip-tech{{background:#eef2ff;color:#4338ca}}
.chip-ok{{background:#dcfce7;color:#166534}}
.chip-warn{{background:#fef3c7;color:#92400e}}
.chip-note{{background:#f3f4f6;color:#4b5563}}
.anno-note{{color:#6b7280;font-style:italic}}
.fsum{{color:#374151}}
.owner-note{{background:#eef2ff;border-left:4px solid #6366f1;border-radius:8px;padding:10px 14px;margin:10px 0;font-size:13.5px}}
.owner-note b{{color:#3730a3}}
.ghead{{display:flex;align-items:center;gap:12px;flex-wrap:wrap}}
.grun{{font-weight:700;font-size:15px}} .glvl{{color:#555;font-size:12px;background:#eef0f4;padding:2px 8px;border-radius:6px}}
.gscore{{font-size:22px;font-weight:800;margin-left:auto;text-align:center;line-height:1.1}}
.gscore small{{display:block;font-size:9px;color:#999;font-weight:normal;letter-spacing:.04em}}
.gscore.hi{{color:#16a34a}} .gscore.mid{{color:#f59e0b}} .gscore.lo{{color:#dc2626}}
.gux{{font-size:22px;font-weight:700;color:#3b5e8c;text-align:center;line-height:1.1}}
.gux small{{display:block;font-size:9px;color:#999;font-weight:normal;letter-spacing:.04em}}
.badge{{font-size:12px;font-weight:700;padding:3px 10px;border-radius:6px}}
.badge.pass{{background:#d4edda;color:#155724}} .badge.fail{{background:#f8d7da;color:#721c24}}
.badge.noapp-b{{background:#e5e7eb;color:#555}}
#runstable{{font-size:12.5px}}
#runstable th{{cursor:pointer;user-select:none;white-space:nowrap;padding:5px 8px}}
#runstable th.sasc::after{{content:" ↑";color:#123f8c}} #runstable th.sdesc::after{{content:" ↓";color:#123f8c}}
#runstable tbody tr{{cursor:pointer}} #runstable tbody tr:hover{{background:#eef3ff}}
#runstable td{{padding:4px 8px}} .sok{{color:#0a7d32;font-weight:600}} .sfail{{color:#b3261e;font-weight:600}}
.bdg{{display:inline-block;margin-left:6px;padding:1px 7px;border-radius:8px;font-size:10.5px;font-weight:600;white-space:nowrap;vertical-align:1px}}
.bdg.loc{{background:#eef2ff;color:#4338ca}} .bdg.cloud{{background:#e8f5f1;color:#0f766e}}
.gcard{{scroll-margin-top:80px}}
#tip{{position:fixed;display:none;z-index:100;max-width:440px;background:#1f2430;color:#e8eaf0;border:1px solid #454d5e;border-radius:9px;padding:9px 13px;font-size:12.5px;line-height:1.45;box-shadow:0 8px 28px rgba(0,0,0,.4);pointer-events:none;white-space:pre-wrap}}
[data-tip]{{cursor:help}}
.try{{display:inline-block;background:#123f8c;color:#fff;padding:8px 18px;border-radius:8px;text-decoration:none;font-weight:600;font-size:14px}}
.try:hover{{background:#0e3270}} .noapp{{color:#999;font-size:13px}}
figure{{margin:0}} figcaption{{font-size:11px;color:#888;text-align:center}}
.shots{{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-top:8px}}
.noshots{{grid-column:1/-1;color:#999;font-size:13px;background:#f6f7fa;border:1px dashed #ccc;border-radius:8px;padding:18px;text-align:center}}
.shot{{width:100%;height:auto;display:block;border:1px solid #ccc;border-radius:8px;cursor:zoom-in;transition:transform .15s}}
.shot:hover{{transform:scale(1.02)}}
#lb{{display:none;position:fixed;inset:0;background:rgba(0,0,0,.92);overflow:auto;z-index:99;cursor:zoom-out}}
#lb img{{max-width:none;display:block;margin:20px auto}}
#lb .hint{{position:fixed;top:12px;right:16px;color:#ddd;font-size:14px}}
</style>
<h1>disc: сводный отчёт — тестирование копирования DISC-теста</h1>
<p class="small">Обновлено 2026-11-18. Полная методика: reports/METHOD.md · конвенции: AGENTS.md.
Все скриншоты кликабельны (1:1).</p>
<div class="toc"><a href="#intro">Введение</a><a href="#method">Методика</a><a href="#matrix">Матрица моделей</a><a href="#forecast">Прогноз</a><a href="#original">Исходный проект</a><a href="#runs">Прогоны и результаты</a><a href="#limits">Ограничения и решения</a><a href="#next">Что дальше</a></div>

<h2 id="intro">0. Введение</h2>
<p>Задание выглядит обманчиво простым: «скопируй тест с сайта». На деле это многослойная
работа — агент должен исследовать живую страницу с интерактивным визардом, вытащить из неё
96 пар «прилагательное → тип», спрятанных в атрибутах разметки, понять алгоритм подсчёта по
чужому патченному коду (комментарии в котором честно говорят «минимально жизнеспособно»),
воспроизвести всё это в одном самодостаточном файле — и попутно выполнить обязательные
адаптации: убрать email-стену и редирект, выбросить токен-шифрование, заменить вендорский
SortableJS своей реализацией перетаскивания. Такая работа — reverse engineering
живого продукта: один агент за один сеанс разбирает чужое приложение и собирает
его заново.</p>
<p>Как тест для агентов задание ценно тем, что у него нет «правильного ответа» из датасета:
источник живой, его нельзя выучить наизусть; эталоном служит поведение, а не пиксели; и
проверяется весь агентный цикл — навигация, скачивание, чтение чужого кода, инженерия,
самопроверка. При этом степень свободы высока: визуальное оформление отдаётся на усмотрение
модели. Из этого выросло, пожалуй, самое неожиданное наблюдение проекта: <b>170 прогонов —
и ни одна копия не повторяет другую.</b> Одни воспроизводят лендинг с модалкой, другие —
чистый пошаговый визард; у одних HTML5 drag&drop, у других самописный pointer-механика или
кнопки ↑↓; палитры, типографика и структура экранов у всех разные. Тридцать художников по
одному описанию портрета — сходится не холст, а характер: у лучших копий функциональный
контракт (данные 96/96, подсчёт ±1, полный поток) совпадает с оригиналом до единого балла.</p>
<p>Второе наблюдение — про риск отказа. До старта казалось вероятным, что часть моделей
<b>откажется</b> копировать функционал чужого сайта — из лицензионных или этических
соображений («я не могу воспроизводить контент третьих лиц»). Прогноз не подтвердился
<b>ни разу</b>: из 15 моделей и ~170 прогонов ни один агент не отказался и не выразил
сомнений в допустимости задания — ни в чате, ни в комментариях кода. Показательно, что
это верно и там, где отказа можно было ждать сильнее всего, — у облачных SOTA, глубже
всех «причёсанных» выравниванием: deepseek, haiku и glm прошли задание без единой
лицензионной оговорки. Все «отказы» оказались техническими: зависания, мёртвые скрипты,
неработающее перетаскивание — но не «не хочу».</p>
<p>Третье наблюдение — неожиданный побочный продукт: <b>аудит выявил ошибки в самом
эталоне.</b> Копии сверялись не только с сайтом, но и с методикой, на которой тест построен
(Т. Эриксон, «Кругом одни идиоты»), — и выяснилось, что оригинал расходится с собственной
книгой в 15 позициях из 96, причём не рассеяно: девять расхождений ложатся в две
тематические группы. Слова веселья и позитива («Энтузиаст», «Шутливый», «Позитивный») тест
приписывает красному D и синему C, хотя по книге это признаки жёлтого I; слова покорности
и сотрудничества («Соглашающийся», «Безропотный», «Уступчивый» и др.) — синему C вместо
зелёного S. Двусторонняя сверка превратила бенчмарк из экзамена для моделей в аудит самого
теста: модели копировали источник — и попутная сверка с первоисточником показала, что
источник расходится с собственной методикой.</p>

<p>Локальные модели проявили себя заметно лучше, чем можно
было ожидать от их размера, — но с жестким расслоением на три лагеря. Добротные:
huihui-ai — <b>20 из 20</b> PASSED, qwen3.8 — 18 из 20, orcarouter/Qwen3.8-Uncensored —
7 из 10, bonsai — 10 из 15; их лучшие прогоны неотличимы от облачных по судье-логике.
Середина: muse-glimmer и gemma4-31b — половина прогонов с решением, вторая — без. Дно:
ornith-1.5:9b, gemma4:e2b, ornith-1.5:35b — ноль PASSED, приложения либо не строятся,
либо не работают вовсе. Облачные для сравнения: deepseek и haiku — 100%, glm — 93%,
mimo — 38%. То есть «локальный 27B в правильной обёртке» сегодня решает задачу уровня
«сделай копию продукта» наравне с облачными флагманами — если у него хватает длины
контекста и стабильности длинного сеанса.</p>

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

<p><b>Автопрохождение</b> (<code>playthrough.mjs</code>): драйвер-«пользователь» проходит тест как
человек — 24 перетаскивания по фиксированной раскладке, клик «Завершить тест», снимки
start/step/result. Раскладка воспроизводима, поэтому числа на экране результата обязаны
сойтись с эталоном D:5, I:2, S:−3, C:−4; расхождение = баг подсчёта в рантайме, даже если
код выглядит верно.</p>
<p><b>Судьи</b> — LLM-модель вне списка кандидатов (glm-5.3-flash, z.ai), у каждого свой вход:</p>
<ul>
<li><b>судья яруса 1</b> (текстовый): получает рубрику <code>scorecard.md</code>, результаты машинных
проверок, лог автопрохождения, статистику сессии агента и <b>полный код</b> index.html —
и ставит 4 оси × 0–4: data (точность переноса вопросов), logic (точность подсчёта,
включая ручной пересчёт алгоритма на контрольной раскладке), ux (поток и работоспособность),
impl (ограничения и чистота кода). Сумма 0–16. Изолирован: один вызов, cwd прогона,
без истории сессии кандидата;</li>
<li><b>vision-UX судья</b>: вход — только пиксели, три скриншота. Оценка 0–100 по якорной
шкале (90+ — продакшн-полировка, 70–89 — «добротное», 50–69 — «работает, но с
шероховатостями», ниже — глючно). Оценивает визуал и юзабилити, не логику.</li>
</ul>
<p><b>Итоговый балл карточки 0–100</b> = сумма осей судьи яруса 1 ÷ 16 × 100 (округление);
балл vision-UX показывается рядом отдельной колонкой и в итог не смешивается.
Раскраска карточек: ≥75 — зелёная, 40–74 — жёлтая, &lt;40 — красная.</p>
<p><b>Статус PASSED/FAILED</b> — только машинный, без участия судей. PASSED = все три
условия одновременно: 1) автопроверка пройдена (данные + рендер + порядок), 2) автопрохождение
дошло до финиша, 3) числа результата отображены на экране. Иначе FAILED с конкретной
причиной («проверка данных/рендера», «автопрохождение не завершено», «результат не
отображён»); нет index.html — «нет решения». Правильность подсчёта бейдж не оценивает —
это зона судьи: так бывают PASSED-прогоны, где судья нашёл баг рантайма и снизил logic
(например, run-06 у GLM-5.3-Flash: бейдж PASSED, судья 10/16 за подсчёт {{11, 6, −9, −8}}).</p>

<h3 id="prompt">1.3. Промпт дословно (v3)</h3>
<pre>{prompt_text}</pre>
<p class="small">История версий: v1 (готовые эталонные данные) и v2 (встроенные исходники) — deprecated.
Файл: test-assignment/prompts/prompt.json.</p>

<h3 id="eval">1.4. Как оценивается: автопроверки, судьи, баллы, PASSED</h3>
<p><b>Машинные проверки</b> (<code>check.py</code> → <code>check.json</code>, до всяких судей):
1) <b>данные</b> — 96 пар «слово → тип» (24 вопроса × 4 прилагательных) посимвольно против
эталона <code>reference/questions.json</code>, порядок вопросов, группировка 8 шагов × 3,
стартовый порядок списков; типы не видны пользователю; 2) <b>рендер</b> (smoke) — страница
открывается в headless Chrome, DOM отрисовался, битых ресурсов нет; 3) <b>самодостаточность</b> —
один файл, работает офлайн с <code>file://</code>, внешних URL нет.</p>
<p><b>Автопрохождение</b> (<code>playthrough.mjs</code>): драйвер-«пользователь» проходит тест как
человек — 24 перетаскивания по фиксированной раскладке, клик «Завершить тест», снимки
start/step/result. Раскладка воспроизводима, поэтому числа на экране результата обязаны
сойтись с эталоном D:5, I:2, S:−3, C:−4; расхождение = баг подсчёта в рантайме, даже если
код выглядит верно.</p>
<p><b>Судьи</b> — LLM-модель вне списка кандидатов (glm-5.3-flash, z.ai), у каждого свой вход:</p>
<ul>
<li><b>судья яруса 1</b> (текстовый): получает рубрику <code>scorecard.md</code>, результаты машинных
проверок, лог автопрохождения, статистику сессии агента и <b>полный код</b> index.html —
и ставит 4 оси × 0–4: data (точность переноса вопросов), logic (точность подсчёта,
включая ручной пересчёт алгоритма на контрольной раскладке), ux (поток и работоспособность),
impl (ограничения и чистота кода). Сумма 0–16. Изолирован: один вызов, cwd прогона,
без истории сессии кандидата;</li>
<li><b>vision-UX судья</b>: вход — только пиксели, три скриншота. Оценка 0–100 по якорной
шкале (90+ — продакшн-полировка, 70–89 — «добротное», 50–69 — «работает, но с
шероховатостями», ниже — глючно). Оценивает визуал и юзабилити, не логику.</li>
</ul>
<p><b>Итоговый балл карточки 0–100</b> = сумма осей судьи яруса 1 ÷ 16 × 100 (округление);
балл vision-UX показывается рядом отдельной колонкой и в итог не смешивается.
Раскраска карточек: ≥75 — зелёная, 40–74 — жёлтая, &lt;40 — красная.</p>
<p><b>Статус PASSED/FAILED</b> — только машинный, без участия судей. PASSED = все три
условия одновременно: 1) автопроверка пройдена (данные + рендер + порядок), 2) автопрохождение
дошло до финиша, 3) числа результата отображены на экране. Иначе FAILED с конкретной
причиной («проверка данных/рендера», «автопрохождение не завершено», «результат не
отображён»); нет index.html — «нет решения». Правильность подсчёта бейдж не оценивает —
это зона судьи: так бывают PASSED-прогоны, где судья нашёл баг рантайма и снизил logic
(например, run-06 у GLM-5.3-Flash: бейдж PASSED, судья 10/16 за подсчёт {{11, 6, −9, −8}}).</p>

<h2 id="matrix">2. Матрица моделей</h2>
<table><tr><th>модель</th><th>уровни мышления</th><th>прогонов</th><th>машиный итог</th></tr>{matrix_rows}</table>

<h2 id="forecast">3. Прогноз (предрегистрация 2026-11-14, reports/FORECAST.md)</h2>
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

{orig_html}
<h2 id="runs">5. Прогоны и результаты</h2>
{summary_table_html}
<p>Каждая карточка — прогон: скриншоты (клик — 1:1), итоговый балл 0–100, статус автопроверки, ссылка на приложение.
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
// --- кастомные тултипы: все title → data-tip, показ своим блоком у курсора ---
(function () {{
  const tip = document.createElement('div');
  tip.id = 'tip';
  document.body.appendChild(tip);
  document.querySelectorAll('[title]').forEach(el => {{
    const v = el.getAttribute('title');
    if (v && v.trim()) el.dataset.tip = v;
    el.removeAttribute('title');
  }});
  let cur = null;
  const show = (el, e) => {{
    tip.textContent = el.dataset.tip;
    tip.style.display = 'block';
    cur = el;
    move(e);
  }};
  const hide = () => {{ tip.style.display = 'none'; cur = null; }};
  const move = (e) => {{
    const pad = 16, r = tip.getBoundingClientRect();
    let x = e.clientX + pad, y = e.clientY + pad;
    if (x + r.width > innerWidth - 8) x = Math.max(8, e.clientX - r.width - pad);
    if (y + r.height > innerHeight - 8) y = Math.max(8, e.clientY - r.height - pad);
    tip.style.left = x + 'px';
    tip.style.top = y + 'px';
  }};
  document.addEventListener('mouseover', e => {{
    const el = e.target.closest('[data-tip]');
    if (cur === el) return;
    if (el) show(el, e); else hide();
  }});
  document.addEventListener('mousemove', e => {{ if (cur) move(e); }});
}})();
const rt = document.getElementById('runstable');
if (rt) {{
  rt.querySelectorAll('thead th').forEach((th, i) => {{
    if (!th.dataset.tip) th.dataset.tip = 'сортировать по колонке';
    th.addEventListener('click', () => {{
      const tb = rt.querySelector('tbody');
      const rows = [...tb.rows];
      const desc = th.classList.contains('sasc');
      rows.sort((a, b) => {{
        const av = a.cells[i].dataset.v ?? '', bv = b.cells[i].dataset.v ?? '';
        const an = parseFloat(av), bn = parseFloat(bv);
        const r = (!isNaN(an) && !isNaN(bn)) ? an - bn : av.localeCompare(bv, 'ru');
        return desc ? -r : r;
      }});
      rows.forEach(rw => tb.appendChild(rw));
      rt.querySelectorAll('thead th').forEach(o => o.classList.remove('sasc', 'sdesc'));
      th.classList.toggle('sdesc', desc);
      th.classList.toggle('sasc', !desc);
    }});
  }});
  rt.querySelectorAll('tbody tr').forEach(tr => {{
    tr.addEventListener('click', () => {{ document.location.hash = tr.dataset.target; }});
  }});
}}
</script>

<h2 id="limits">6. Ограничения и решения</h2>
<ul>
<li>симуляция drag&drop невоспроизводима на произвольных реализациях (Pointer Events,
откат SortableJS, скролл-контейнеры) — автопрохождение проверяет поток и рендер,
логику подсчёта проверяет судья по коду; показанные баллы — справочно;</li>
<li>рабочие файлы агента (скачанные исходники, тест-скрипты) — не недостаток и не удаляются;</li>
<li>известные странности оригинала (секция 4, латинская «c») — если модель их
исправила, это плюс, а не провал: автопроверка фиксирует факт в поле
<code>known_quirk_normalized</code> («известная странность учтена»);</li>
<li>судья яруса 1 — LLM (glm-5.3-flash, не кандидат); ярус 2 — владелец/сильный судья;</li>
<li>стартовый порядок слов внутри списков проверяется с 2026-11-17 (check.json.order):
эталонная четвёрка должна встретиться как непрерывная подпоследовательность документа;
провал — только когда список найден, но порядок другой (ненайденные списки — ограничение
экстрактора динамических данных, не провал). Ретроспективно: из 103 полностью проверяемых
прогонов порядок оригинала соблюдён во всех 24/24 — ноль нарушений, бейджи не изменились;</li>
<li>нестандартные события (таймаут, конкуренция VRAM, эскалация thinking) видны в run.json;</li>
<li>метод автопрохождения: перетаскивание выполняется DOM-реордером с батареей
синтетических событий (DragEvent/mouseup/pointerup/change); pointer-жесты
(pointerdown→move) не эмулируются — state-driven приложения, которые не читают DOM,
показывают стартовый порядок (huihui run-04/07/15: displayed = D:−1/I:0/S:−3/C:4);
счётчик drags.dom_fallback с 2026-11-18 считает успешные реордеры (раньше поле
было мёртвым и вводило судью в заблуждение — huihui run-07 переоценён:
15/16 → 11/16); парсер результата дополнен: формат «Метка (D) +5» одной строкой
и метка S «Постоянство» (glm run-05 после этого PASSED: эталон 5/2/−3/−4);</li>
<li>коррекция 2026-11-18: после находки «результат виден на шаге вопросов» в bonsai run-13
(CSS-правило на ID перебило атрибут <code>hidden</code> — судья, читая код, дважды это пропустил)
в рубрику ux и критерии vision-UX добавлен явный запрет; все 129 прогонов со скриншотами
проверены vision-сканом — дефект только в run-13, ему в <code>check.json</code> добавлен машинный
факт (след: <code>judge-stepscan.json</code>), прогон переоценён: судья 14/16 → 12/16,
vision-UX 58 → 42.</li>
</ul>

<h2 id="next">7. Что дальше: DISC-команда</h2>
<p>Главный побочный продукт бенчмарка — 15 расхождений между эталоном и методикой,
найденных при сверке с книгой Эриксона (секция 4), — породил идею следующего
эксперимента. Команде локальных моделей предстоит реализовать
<b>«правильный тест»</b> — исправленную версию, где типы соответствуют книге Эриксона.
Роли участников планируется задавать по командным ролям Белбина (Руководитель,
Генератор идей, Оценщик, Реализатор и др.), добавляя к каждой DISC-профиль участника —
именно этот слой будет варьироваться между группами A и B. Детальный дизайн ещё
в проработке — наброски в AGENTS.md (раздел «Идея волны 5»).</p>

</html>"""


def html_report(runs):
    import base64
    cards = []
    for run in runs:
        r = run_row(run)
        meta = load(Path(run), "run.json")
        chk = load(Path(run), "check.json")
        jd = load(Path(run), "judge-tier1.json").get("verdict") or {}
        uxvf = Path(run) / "judge-ux.json"
        uxv = (json.loads(uxvf.read_text(encoding="utf-8")).get("verdict") or {}) if uxvf.is_file() else {}
        esc = html_mod.escape
        jhtml = (f'<b>судья ярус 1:</b> data {jd.get("data")} · logic {jd.get("logic")} · '
                 f'ux {jd.get("ux")} · impl {jd.get("impl")} — <b>{jd.get("total")}/16</b>'
                 f' · <b>vision-UX: {uxv.get("score", "—")}/100</b>'
                 f'<div class="notes">{esc((jd.get("notes") or ""))[:700]}</div>'
                 f'<div class="notes">{esc((jd.get("examples") or ""))[:700]}</div>'
                 + (f'<div class="notes"><b>vision-UX замечания:</b> {esc(" · ".join(uxv.get("issues", []))[:600])}</div>' if uxv.get("issues") else "")
                 if jd else "судья: не выполнялся")
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
    ])

    return f"""<!DOCTYPE html><html lang=ru><head><meta charset=utf-8><title>disc — прогоны</title>
<style>
body{{background:#f5f6f8;margin:24px;font-family:system-ui;color:#1c2024;max-width:1100px;margin:auto}}
h1,h2,h3{{font-family:system-ui}} h2{{border-bottom:2px solid #c9ced8;padding-bottom:4px;margin-top:36px}}
table{{border-collapse:collapse;background:#fff;width:100%}}
th,td{{border:1px solid #d0d4dd;padding:6px 10px;font-size:14px;text-align:left}}
th{{background:#eef0f4}}
.pass{{color:#0a7d32}} .fail{{color:#b3261e}}
.card{{background:#fff;border:1px solid #d5d8de;border-radius:10px;padding:14px 18px;margin:14px 0;box-shadow:0 1px 3px rgba(0,0,0,.06)}}
.card h3{{margin:0 0 6px}} .run{{color:#888;font-weight:normal;font-size:13px}}
.meta{{font-size:12px;color:#888;margin:4px 0}}
.checks{{font-size:13px;margin:6px 0}}
.judge{{font-size:13px;background:#f6f7fa;border-radius:8px;padding:8px 12px;margin-top:8px}}
.notes{{font-size:12px;color:#555;margin-top:4px;white-space:pre-wrap}}
.shots{{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-top:8px}}
img.shot{{width:100%;height:auto;display:block;border:1px solid #ccc;border-radius:6px}}
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
    if not args.run and not args.all and not args.html and not args.report:
        print("укажите --run <dir> и/или --all и/или --html и/или --report")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
