#!/usr/bin/env python3
"""Прогон анкеты DISC (блиц-тест) через ollama: chat-модели и decision-модели.

Не агентная сессия (в отличие от test-assignment/runner.py): прямые вызовы
API без инструментов. Chat-модели — /api/chat с промптом из prompts/prompt.json
(ответ — JSON «номер вопроса → ответ»), decision-модели (clef) —
/v1/systemone с noul-пробами по кандидатам, выбор argmax (паттерн сестринского
workspace: ~/MyProjects/Models/interview/score.py).

Изоляция и честность:
- фактическая шкала мышления запрашивается у /api/show, несуществующие уровни
  не запрашиваются никогда (ollama молча подменяет их дефолтом);
- снапшот /api/ps перед каждым прогоном -> run.json (ollama_contention);
- ретраи только на транспортные ошибки; поведенческие сбои — результат;
- модель выгружается после блока (keep_alive: 0);
- seed не фиксируется, сэмплинг — дефолты модели (options: num_ctx/num_predict).

Запуск:
    python3 quiz/runner.py --list
    python3 quiz/runner.py --model qwen3.8:27b-pi-100k --thinking low --runs 5
    python3 quiz/runner.py --model clef --runs 5
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent          # quiz/
ROOT = HERE.parent                              # корень worktree

NUM_CTX = 65536
NUM_PREDICT = 32768
CALL_TIMEOUT = 1200          # 20 мин на вызов
# Бюджет 32768 — правило AGENTS.md для моделей с энергичным максимумом в
# шкале: при 8192 thinking выжигает весь бюджет до начала ответа (наблюдалось
# в первом прогоне серии: bonsai@low — 30к символов thinking, content пуст,
# eval_count впритык 8192). num_ctx 65536 — запас, чтобы thinking успел
# израсходовать бюджет без усечения промпта.
RETRIES = 2                  # только транспортные ошибки
KEEP_ALIVE = "10m"           # внутри блока модель держится загруженной


def log(msg: str) -> None:
    print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] {msg}", flush=True)


def base_url() -> str:
    v = __import__("os").environ.get("OLLAMA_BASE_URL", "").strip()
    if not v:
        sys.exit("задайте OLLAMA_BASE_URL (в worktree .env.local нет — передавайте через env)")
    return v.rstrip("/")


def http_json(path: str, payload: dict | None = None, timeout: int = 60) -> dict:
    url = base_url() + path
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    last_exc = None
    for attempt in range(1, RETRIES + 2):
        try:
            req = urllib.request.Request(url, data=data, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read())
        except (urllib.error.URLError, TimeoutError, OSError,
                __import__("http").client.HTTPException,
                json.JSONDecodeError) as e:
            # HTTPException (IncompleteRead/RemoteDisconnected) — сервер
            # обрывает соединение/тело ответа; JSONDecodeError — обрыв тела
            last_exc = e
            if attempt <= RETRIES:
                log(f"  транспортная ошибка ({e}); повтор {attempt}/{RETRIES}")
                time.sleep(5 * attempt)
    raise RuntimeError(f"транспорт не ответил после {RETRIES + 1} попыток: {last_exc}")


# ---------------------------------------------------------------- шкалы мышления

def model_show(tag: str) -> dict:
    return http_json("/api/show", {"model": tag}, timeout=120)


def thinking_scale(tag: str) -> list:
    """Значения ручки мышления из /api/show (пусто — ручки нет)."""
    t = model_show(tag).get("thinking")
    if isinstance(t, dict):
        return list(t.get("values") or [])
    return []


def requested_levels(doc_levels: list, scale: list) -> list:
    """Уровни, которые реально запрашиваем: пересечение документации и шкалы.
    Булева шкала (или отсутствие ручки) -> off/on. decision -> [None]."""
    if not doc_levels or doc_levels == [None]:
        return [None]
    str_levels = [v for v in scale if isinstance(v, str)]
    if not str_levels:
        return ["off", "on"] if len(doc_levels) > 1 else [doc_levels[0]]
    out = []
    for lvl in doc_levels:
        if lvl == "off" or lvl in str_levels:
            out.append(lvl)
    return out or ["off"]


def think_payload(level) -> tuple[dict | None, str]:
    """Значение ручки think для /api/chat: None = не отправлять.
    Возвращает (значение, пометка для run.json)."""
    if level is None:
        return None, "decision-протокол без ручки"
    if level == "off":
        return False, "think=false"
    if level == "on":
        return True, "think=true"
    return level, f"think={level}"


# ---------------------------------------------------------------- парсинг ответа

def strip_think(text: str) -> tuple[str, str | None]:
    m = re.search(r"<think>(.*?)</think>", text, re.S)
    if m:
        return (text[:m.start()] + text[m.end():]).strip(), m.group(1).strip()
    return text, None


def norm_text(s: str) -> str:
    s = s.lower().replace("ё", "е")
    s = re.sub(r"[^0-9a-zа-я\- ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


# --- языковые таблицы матчера; активный язык = KEY["lang"] ------------------
# цветовые стемы и черты (полные слова); одиночные буквы — только если ответ
# целиком одна буква (ru: защита от «с»/«к»-предлогов) или короткий ответ
# из <=8 токенов с отдельными латинскими d/i/s/c (оба языка)
COLOR_RE_BY_LANG = {
    "ru": {
        "red":    r"\b(?:красн\w*|доминир\w*|доминант\w*|red)\b",
        "yellow": r"\b(?:желт\w*|жолт\w*|влия\w*|yellow)\b",
        "green":  r"\b(?:зелен\w*|стабил\w*|постоян\w*|green)\b",
        "blue":   r"\b(?:син(?:ь|ий|яя|ее|ие|его|ему|им|их|ими|юю)\b|\bпослуш\w*|\bсоответ\w*|\bаналит\w*|\bblue\b)",
    },
    "en": {
        "red":    r"\b(?:reds?|dominan\w*)\b",
        "yellow": r"\b(?:yellows?|yellowish|influen\w*)\b",
        "green":  r"\b(?:greens?|greenish|stead\w*|patien\w*|calm\w*)\b",
        "blue":   r"\b(?:blues?|analyt\w*|complian\w*|conscient\w*|perfection\w*)\b",
    },
}
KEY_COLOR_BY_LANG = {
    "ru": {"красный": "red", "желтый": "yellow", "зеленый": "green", "синий": "blue"},
    "en": {"red": "red", "yellow": "yellow", "green": "green", "blue": "blue"},
}
LETTER_MAP = {"d": "red", "i": "yellow", "s": "green", "c": "blue"}
CYR_MAP = {"к": "red", "д": "red", "ж": "yellow", "з": "green", "с": "blue"}

# «нет однозначного ответа» и семья (для kind=none — это ключ; для остальных
# вопросов — отказ отвечать по ключу)
NO_ANSWER_RE_BY_LANG = {
    "ru": re.compile(
        r"\bнеоднозначн\w*|\bодногозначн\w*"   # вторая — опечатка моделей «одногозначного»
        r"|\bнет\b[^.]{0,40}\b(?:однозначн\w*|одногозначн\w*|единственн\w*|правильн\w*|верн\w*|конкретн\w*)\b"
        r"|\b(?:однозначн\w*|одногозначн\w*|единственн\w*|правильн\w*|верн\w*|конкретн\w*)\b[^.]{0,40}\b(?:ответа?\b[^.]{0,10})?(?:нет|нельзя)\b"
        r"|\b(?:зависит|по-разному|разное|нельзя)\b|\bневозможно (?:определить|сказать)\b"
        r"|\bнедостаточно (?:данных|информации)\b"
        r"|\b(?:смешанн\w*|смешени\w*|индивидуальн\w*)\b|\bсмес[ьи]\b"
        r"|\bу всех\b[^.]{0,20}\bразн\w*"
        r"|\bу каждого\b"),
    "en": re.compile(
        r"\bno\b.{0,20}\b(?:single|given|clear|definitive|definite|unambiguous|correct|right|universal|specific)\b.{0,25}\banswer\b"
        r"|\bthere (?:is|'s|was) no\b.{0,40}\banswer\b"
        r"|\bnot a single\b.{0,25}\banswer\b|\bno such profile\b|\bno single profile\b|\bno specific profile\b"
        r"|\b(?:it|this|that|one) depends\b|\bdepends on\b"
        r"|\b(?:varies|vary|differs|differ)\b|\bdifferent for (?:everyone|each|everybody)\b"
        r"|\b(?:cannot|can't|can not|impossible)\b.{0,30}\b(?:say|determine|tell|know|define|answer)\b"
        r"|\b(?:not enough|insufficient)\b.{0,25}\b(?:data|information|context)\b"
        r"|\bno way to\b.{0,25}\b(?:know|tell|determine|say)\b"
        r"|\bnone of the above\b|\bmixed\b|\bindividual\b"
        r"|\bno answer\b|\bn a\b"),
}
# «не применимо, я ИИ» — самоотвод, не «нет однозначного ответа»
REFUSAL_RE_BY_LANG = {
    "ru": re.compile(
        r"\bне\s?применимо\b"
        r"|\b(?:я|как)\s+(?:ии|языковая модель|модель|лм)\b"
        r"|\bличный вопрос\b"
        r"|\bу меня нет (?:круга|знакомых|друзей)\b"),
    "en": re.compile(
        r"\bas an ai\b"
        r"|\bi(?:'m| am)\b.{0,10}\b(?:an )?(?:ai|language model|llm)\b"
        r"|\bi (?:don't |do not |)have no\b.{0,25}\b(?:social )?(?:circle|friends|acquaintances)\b"
        r"|\bi don't have\b.{0,25}\b(?:social )?(?:circle|friends|acquaintances)\b"
        r"|\bpersonal question\b|\bnot applicable\b|\bnot relevant to me\b|\bdoesn't apply to me\b"),
}
# «все вышеперечисленные»/«любые» — ответ «любой из вариантов»
ALL_OPT_RE_BY_LANG = {
    "ru": re.compile(
        r"\b(?:любые?|любой из них|любой вариант"
        r"|все (?:вышеперечисленные|вышеуказанные|профили|варианты|четыре|сразу)"
        r"|сочетание (?:всех|разн\w*)|комбинация всех|микс всех|смесь всех)\b"),
    "en": re.compile(
        r"\ball of the above\b|\ball of them\b|\bany of (?:them|the above|these)\b"
        r"|\bany profile\b|\bany combination\b"
        r"|\b(?:all|every)\b.{0,10}\b(?:profiles|colors|options)\b|\bevery (?:single )?(?:one|color|profile)\b"
        r"|\ball four\b"),
}
# «два жёлтых»: маркер удвоения (ru Q1 / en Q1)
DUO_RE_BY_LANG = {
    "ru": re.compile(r"\b(?:два|две|оба|пар\w*)\b"),
    "en": re.compile(r"\b(?:two|both|pair|2)\b"),
}
# «зелёный с любым»: маркер универсальности (ru Q2 / en Q2)
ANYONE_RE_BY_LANG = {
    "ru": re.compile(r"\b(?:люб\w*|все|всех|всеми|всем)\b"),
    "en": re.compile(r"\b(?:anyone|anybody|any other|everyone|everybody|every|any|all|others|both)\b"),
}
# «смешение всех цветов» (ru Q18 / en Q17): маркеры смеси
MIX_RE_BY_LANG = {
    "ru": re.compile(r"\b(?:смеш\w*|смес\w*|микс\w*|комбинац\w*|сочетани\w*|команд\w*|сбалансированн\w*)\b"),
    "en": re.compile(r"\b(?:mix\w*|combin\w*|blend\w*|balanc\w*|fusion|union|team)\b"),
}
MIX_WORD_RE_BY_LANG = {
    "ru": re.compile(r"\b(?:все|всех|четыре)\b"),
    "en": re.compile(r"\b(?:all|four)\b"),
}
ALL_FOUR_RE_BY_LANG = {
    "ru": re.compile(r"\bвсе четыре\b"),
    "en": re.compile(r"\ball four\b"),
}


def find_colors(answer: str) -> list:
    """Цвета в ответе: слова-стемы всегда; если цветовых слов нет —
    одиночные буквы: ответ из <=8 токенов с отдельными латинскими d/i/s/c
    (кириллические одиночные «с»/«к» — предлоги, не мапим вне правила
    «весь ответ — одна буква», только ru)."""
    n = norm_text(answer)
    colors = []
    for color, pat in COLOR_RE_BY_LANG[KEY.get("lang", "ru")].items():
        if re.search(pat, n):
            colors.append(color)
    if not colors:
        tokens = n.split()
        if len(tokens) <= 8:
            for tok in tokens:
                if tok in LETTER_MAP:
                    colors.append(LETTER_MAP[tok])
        if not colors and KEY.get("lang", "ru") == "ru" and len(n) <= 2:
            ch = n.strip()
            if ch in CYR_MAP:
                colors.append(CYR_MAP[ch])
    return colors


def match_answer(q: dict, answer: str) -> dict:
    """Вердикт по одному вопросу: correct/incorrect/unparsed/skipped + флаги.
    Язык матчера и спец-ветки — из KEY (kind, generic) и языковых таблиц."""
    lang = KEY.get("lang", "ru")
    no_answer_re = NO_ANSWER_RE_BY_LANG[lang]
    refusal_re = REFUSAL_RE_BY_LANG[lang]
    all_opt_re = ALL_OPT_RE_BY_LANG[lang]
    key_norm = norm_text(q["key"])
    ans = (answer or "").strip()
    if not ans:
        return {"verdict": "skipped"}
    n = norm_text(ans)
    if n == key_norm:
        return {"verdict": "correct", "matched": "exact"}
    if n in [norm_text(a) for a in q.get("aliases", [])]:
        return {"verdict": "correct", "matched": "alias"}
    no_answer = bool(no_answer_re.search(n))
    refusal = bool(refusal_re.search(n))
    all_opt = bool(all_opt_re.search(n))
    colors = find_colors(ans)
    if q["kind"] == "none":
        # ключ — «нет однозначного ответа»: семья таких формулировок — зачёт
        if no_answer or all_opt:
            return {"verdict": "correct", "matched": "no-single-answer"}
        if refusal:
            return {"verdict": "incorrect", "flag": "refusal"}
        if colors:
            return {"verdict": "incorrect", "colors": colors}
        return {"verdict": "unparsed"}
    if refusal:
        return {"verdict": "incorrect", "flag": "refusal"}
    if no_answer:
        return {"verdict": "incorrect", "flag": "no-answer"}
    if all_opt and q.get("generic") != "all-four":
        # «любые»/«all of the above» — не по ключу; для вопроса-команды
        # «все четыре» и есть ключ, дженерик ниже разберётся
        return {"verdict": "incorrect", "flag": "all-option"}
    if q["kind"] == "color":
        key_color = KEY_COLOR_BY_LANG[lang][norm_text(q["key"])]
        if len(colors) == 1:
            if colors[0] == key_color:
                return {"verdict": "correct", "matched": "color-token"}
            return {"verdict": "incorrect", "colors": colors}
        if len(colors) > 1:
            return {"verdict": "incorrect", "flag": "ambiguous", "colors": colors}
        return {"verdict": "unparsed"}
    if q["kind"] == "book":
        # дженерики поверх алиасов, ветка — по generic из ключа
        g = q.get("generic")
        if g == "yellow-duo":
            if colors == ["yellow"] and DUO_RE_BY_LANG[lang].search(n):
                return {"verdict": "correct", "matched": "generic"}
            if colors == ["yellow"]:
                return {"verdict": "incorrect", "flag": "near", "colors": colors}
        elif g == "green-anyone":
            if "green" in colors and ANYONE_RE_BY_LANG[lang].search(n):
                return {"verdict": "correct", "matched": "generic"}
            if colors == ["green"]:
                return {"verdict": "incorrect", "flag": "near", "colors": colors}
        elif g == "all-four":
            if MIX_RE_BY_LANG[lang].search(n) and MIX_WORD_RE_BY_LANG[lang].search(n):
                return {"verdict": "correct", "matched": "generic"}
            if set(colors) == {"red", "yellow", "green", "blue"}:
                return {"verdict": "correct", "matched": "all-four-colors"}
            if ALL_FOUR_RE_BY_LANG[lang].search(n):
                return {"verdict": "correct", "matched": "generic"}
        # назван конкретный другой набор цветов
        if colors:
            return {"verdict": "incorrect", "colors": colors}
        return {"verdict": "unparsed"}
    return {"verdict": "unparsed"}


def extract_json_answers(content: str) -> tuple[dict | None, bool]:
    """JSON «N -> ответ»: сначала весь текст, затем первый сбалансированный {...}."""
    def try_obj(s: str):
        try:
            obj = json.loads(s)
            if isinstance(obj, dict):
                return obj
        except (json.JSONDecodeError, ValueError):
            pass
        return None

    obj = try_obj(content)
    src = content
    if obj is None:
        start = content.find("{")
        while start != -1:
            depth = 0
            in_str = False
            esc = False
            for i in range(start, len(content)):
                ch = content[i]
                if in_str:
                    if esc:
                        esc = False
                    elif ch == "\\":
                        esc = True
                    elif ch == '"':
                        in_str = False
                    continue
                if ch == '"':
                    in_str = True
                elif ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        obj = try_obj(content[start:i + 1])
                        if obj is not None:
                            src = content[start:i + 1]
                        break
            if obj is not None:
                break
            start = content.find("{", start + 1)
    if obj is None:
        return None, False
    answers = {}
    for k, v in obj.items():
        m = re.fullmatch(r"\s*(\d{1,2})\s*", str(k))
        if m and isinstance(v, str):
            answers[int(m.group(1))] = v
        elif m and isinstance(v, (int, float)) and int(v) in (1, 2, 3, 4):
            pass  # цифра вместо текста профиля — не ответ; останется skipped
    return answers, True


def parse_chat_answers(content: str, total: int = 24) -> tuple[dict, dict]:
    """-> (answers {n: text}, flags {json_ok, fallback}). Фолбэк — «N. ответ»."""
    flags = {"json_ok": False, "fallback": False}
    answers, ok = extract_json_answers(content)
    if ok and answers:
        flags["json_ok"] = True
        return answers, flags
    answers = {}
    for m in re.finditer(r"(?:^|\n)\s*(\d{1,2})\s*[\.\)\-–—:]\s*(.+)", content):
        answers[int(m.group(1))] = m.group(2).strip()
    if answers:
        flags["fallback"] = True
        return answers, flags
    return {}, flags


# ---------------------------------------------------------------- вызовы моделей

def chat_call(tag: str, prompt: str, think) -> dict:
    body = {
        "model": tag,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "keep_alive": KEEP_ALIVE,
        "options": {"num_ctx": NUM_CTX, "num_predict": NUM_PREDICT},
    }
    if think is not None:
        body["think"] = think
    r = http_json("/api/chat", body, timeout=CALL_TIMEOUT)
    msg = r.get("message") or {}
    content = msg.get("content") or ""
    thinking = msg.get("thinking")
    content, embedded = strip_think(content)
    if thinking is None and embedded:
        thinking = embedded
    usage_keys = ("prompt_eval_count", "eval_count", "eval_duration",
                  "prompt_eval_duration", "load_duration", "total_duration")
    usage = {k: r.get(k) for k in usage_keys if r.get(k) is not None}
    return {"content": content, "thinking": thinking, "usage": usage,
            "done_reason": r.get("done_reason")}


def ps_snapshot() -> list:
    try:
        r = http_json("/api/ps", timeout=30)
        return [m.get("name") for m in r.get("models", [])]
    except RuntimeError:
        return []


def unload(tag: str) -> None:
    try:
        http_json("/api/generate", {"model": tag, "keep_alive": 0}, timeout=60)
        log(f"  модель {tag} выгружена (keep_alive=0)")
    except RuntimeError as e:
        log(f"  выгрузка {tag} не удалась (не критично): {e}")


# ---------------------------------------------------------------- decision-протокол

def decision_probe_question(q: dict) -> dict:
    state = ("Блиц-тест по модели DISC. Четыре поведенческих профиля называются "
             "цветами: красный, жёлтый, зелёный и синий.\n\n"
             f"Вопрос {q['n']}: {q['question']}\n\n"
             "Ниже перечислены утверждения о правильном ответе на этот вопрос.")
    questions = {}
    for i, opt in enumerate(q["options"]):
        questions[f"opt{i}"] = {
            "type": "noul",
            "instructions": f"Правильный ответ на вопрос {q['n']} — «{opt}».",
            "criteria": {"false": f"«{opt}» — не правильный ответ",
                         "true": f"«{opt}» — правильный ответ"},
        }
    return {"state": state, "questions": questions}


def decision_run(tag: str, key: dict) -> dict:
    per_question, usage = [], {"input_tokens": 0, "output_tokens": 0}
    for q in key["questions"]:
        payload = {"model": tag, **decision_probe_question(q)}
        t0 = time.monotonic()
        r = http_json("/v1/systemone", payload, timeout=CALL_TIMEOUT)
        latency = round(time.monotonic() - t0, 2)
        u = r.get("usage") or {}
        usage["input_tokens"] += u.get("input_tokens") or 0
        usage["output_tokens"] += u.get("output_tokens") or 0
        answers = r.get("answers") or {}
        probs = {}
        for i, opt in enumerate(q["options"]):
            a = answers.get(f"opt{i}") or {}
            probs[opt] = round(float(a.get("noul", -1)), 4)
        valid = {k: v for k, v in probs.items() if v >= 0}
        if not valid:
            chosen, p_chosen = None, None
        else:
            chosen = max(valid, key=valid.get)
            p_chosen = valid[chosen]
        correct = (chosen == q["key"])
        p_correct = probs.get(q["key"])
        per_question.append({
            "n": q["n"], "question": q["question"], "key": q["key"],
            "probs": probs, "chosen": chosen, "p_chosen": p_chosen,
            "p_correct": p_correct, "correct": correct, "latency_s": latency,
        })
        log(f"  Q{q['n']:>2}: выбрано «{chosen}» (p={p_chosen}) "
            f"{'верно' if correct else 'НЕВЕРНО'} [{latency}s]")
    return {"per_question": per_question, "usage": usage}


# ---------------------------------------------------------------- облако (OpenAI-совместимое)

CLOUD_PROVIDERS = {
    # $/1M токенов (вход / кэш-хит / выход), пик; оф-пик вдвое дешевле
    "deepseek": {
        "url": "https://api.deepseek.com/chat/completions",
        "key": "env-file:DEEPSEEK_API_KEY",   # путь к файлу — env MODELS_RU_ENV
        "tariff": (0.30, 0.006, 1.20),
        "scale": ("low", "high"),
        "thinking": lambda lvl: {"reasoning_effort": lvl} if lvl else {},
        "doc_levels_note": "reasoning_effort, минимум low (off не существует)",
    },
    "xiaomi": {
        # подписка Xiaomi (token plan sgp); паттерн сестринского workspace
        # (knowledge-map/runner_cloud.py). Шкала из ошибки 400 API:
        # reasoning_effort none/low/medium/high; off = none.
        "url": "https://token-plan-sgp.xiaomimimo.com/v1/chat/completions",
        "key": "pi-auth:xiaomi-token-plan-sgp",
        "tariff": None,                       # квота подписки
        "scale": ("off", "low", "medium", "high"),
        "thinking": lambda lvl: ({"reasoning_effort": "none"} if lvl == "off"
                                 else {"reasoning_effort": lvl} if lvl else {}),
        "doc_levels_note": "reasoning_effort none/low/medium/high (перечислено в 400 API); off = none",
    },
    "alibabacloud": {
        # подписка alibabacloud (Model Studio token plan); паттерн сестринского
        # workspace (knowledge-map/runner_cloud.py). Ключ pi-auth.
        # ВАЖНО (карточка qwen4-max-preview): при транспорте без enable_thinking
        # запрошенный off эскалируется в low — прямой вызов передаёт
        # enable_thinking=False честно.
        "url": "https://token-plan.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1/chat/completions",
        "key": "pi-auth:qwen-token-plan-individual",
        "tariff": None,                       # квота подписки
        "scale": ("off", "low", "medium", "high"),
        "thinking": lambda lvl: ({"enable_thinking": False} if lvl == "off"
                                 else {"reasoning_effort": lvl} if lvl else {}),
        "doc_levels_note": ("ШКАЛА ЗАВИСИТ ОТ МОДЕЛИ (доки 2026-11-17): qwen4-max — "
                            "low/high/xhigh (дефолт high; medium→high); qwen4-max-preview — "
                            "low/medium/xhigh (дефолт xhigh; high недокументирован, "
                            "фактически ≈medium). off — enable_thinking=False"),
    },
    "zai": {
        # подписка z.ai (coding plan); паттерн сестринского workspace
        # (~/MyProjects/Models/knowledge-map/runner_cloud.py)
        "url": "https://api.z.ai/api/coding/paas/v4/chat/completions",
        "key": "pi-auth:zai",                 # запись zai в ~/.pi/agent/auth.json
        "tariff": None,                       # квота подписки, не по-токеново
        "scale": ("low", "high", "max"),
        "thinking": lambda lvl: ({"thinking": {"type": "enabled"},
                                  "reasoning_effort": lvl} if lvl else {}),
        "doc_levels_note": ("шкала low/high/max (docs.z.ai, дефолт max); "
                            "off не существует — «thinking cannot be disabled», "
                            "запрошенный off провайдер выполняет как минимальное "
                            "мышление (низведён к low); medium — legacy, не запускаем"),
    },
}


def cloud_key(provider: str) -> str:
    """Ключ провайдера: из env-файла (путь — env MODELS_RU_ENV) или из
    pi-auth (~/.pi/agent/auth.json). Секреты в репо не живут и не печатаются."""
    spec = CLOUD_PROVIDERS[provider]["key"]
    kind, _, name = spec.partition(":")
    if kind == "env-file":
        env_path = __import__("os").environ.get("MODELS_RU_ENV", "")
        if not env_path:
            sys.exit(f"задайте MODELS_RU_ENV — путь к env-файлу с ключами облаков ({provider})")
        for line in Path(env_path.replace("~", str(Path.home()))).read_text().splitlines():
            if line.startswith(name + "="):
                return line.split("=", 1)[1].strip()
        sys.exit(f"{name} не найден в {env_path}")
    if kind == "pi-auth":
        d = json.loads((Path.home() / ".pi/agent/auth.json").read_text())
        return d[name]["key"]
    sys.exit(f"неизвестный источник ключа: {spec}")


def cloud_call(tag: str, prompt: str, level, provider: str) -> dict:
    cfg = CLOUD_PROVIDERS[provider]
    body = {"model": tag, "messages": [{"role": "user", "content": prompt}],
            **cfg["thinking"](level)}
    req = urllib.request.Request(
        cfg["url"],
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {cloud_key(provider)}"})
    last_exc = None
    for attempt in range(1, RETRIES + 2):
        try:
            with urllib.request.urlopen(req, timeout=CALL_TIMEOUT) as r:
                resp = json.loads(r.read())
            msg = (resp.get("choices") or [{}])[0].get("message") or {}
            content = msg.get("content") or ""
            thinking = msg.get("reasoning_content")
            content, embedded = strip_think(content)
            if thinking is None and embedded:
                thinking = embedded
            u = resp.get("usage") or {}
            usage = {
                "prompt_tokens": u.get("prompt_tokens"),
                "cached_tokens": (u.get("prompt_tokens_details") or {}).get("cached_tokens"),
                "completion_tokens": u.get("completion_tokens"),
                "reasoning_tokens": (u.get("completion_tokens_details") or {}).get("reasoning_tokens"),
            }
            return {"content": content, "thinking": thinking, "usage": usage,
                    "model_version": resp.get("model"),
                    "done_reason": resp.get("choices", [{}])[0].get("finish_reason")}
        except (urllib.error.URLError, TimeoutError, OSError,
                __import__("http").client.HTTPException,
                json.JSONDecodeError) as e:
            last_exc = e
            if attempt <= RETRIES:
                log(f"  транспортная ошибка ({e}); повтор {attempt}/{RETRIES}")
                time.sleep(5 * attempt)
    raise RuntimeError(f"облако не ответило после {RETRIES + 1} попыток: {last_exc}")


def spend_row(provider: str, model: str, purpose: str, requests: int,
              usage: dict) -> None:
    """Правило 9: каждая платная операция — строка в reports/spend.csv
    (главный workspace, в git не живёт). Подписки (tariff None) —
    стоимость 0, токены записываются как расход квоты."""
    import csv as _csv
    tin, tcout = usage.get("prompt_tokens") or 0, usage.get("completion_tokens") or 0
    cached = usage.get("cached_tokens") or 0
    tariff = CLOUD_PROVIDERS[provider]["tariff"]
    if tariff:
        ti, tc, to = tariff
        cost = (tin - cached) * ti / 1e6 + cached * tc / 1e6 + tcout * to / 1e6
        cost_str = f"{cost:.4f}"
    else:
        cost_str = "0 (квота)"
    if ROOT.name == "disc-quiz":  # worktree — учёт в главном tree
        target = ROOT.parent / "disc" / "reports" / "spend.csv"
    else:
        target = ROOT / "reports" / "spend.csv"
    target.parent.mkdir(exist_ok=True)
    new = not target.exists()
    with open(target, "a", newline="") as f:
        w = _csv.writer(f)
        if new:
            w.writerow(["дата", "модель", "цель", "запросов", "токены вх",
                        "из них кэш", "токены вых", "стоимость $"])
        w.writerow([datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"),
                    model, purpose, requests, tin, cached, tcout, cost_str])


def run_cloud_block(tag: str, folder: str, levels: list, runs: int,
                    prompt_ver: int, prompt_sha: str, prompt: str,
                    cloud_provider: str = "deepseek") -> None:
    cfg = CLOUD_PROVIDERS[cloud_provider]
    log(f"{tag}: облачный провайдер {cloud_provider}, уровни {levels}")
    (ROOT / "models" / folder / "quiz").mkdir(parents=True, exist_ok=True)
    total_usage = {}
    for level in levels:
        do_pilot = True
        for i in range(runs):
            if do_pilot:  # пилот: один выброшенный вызов
                try:
                    pilot = cloud_call(tag, prompt, level, cloud_provider)
                    do_pilot = False
                    log(f"  пилот: ok ({len(pilot['content'])} симв., "
                        f"reasoning={'есть' if pilot['thinking'] else 'нет'}, "
                        f"версия {pilot['model_version']})")
                except RuntimeError as e:
                    log(f"  пилот: {e}")
            d = next_run_dir(folder)
            t0 = time.monotonic()
            try:
                resp = cloud_call(tag, prompt, level, cloud_provider)
                content, thinking, usage = resp["content"], resp["thinking"], resp["usage"]
                error = done_reason = None
            except RuntimeError as e:
                resp = {"model_version": None}
                content, thinking, usage = "", None, {}
                error, done_reason = str(e), None
                log(f"  прогон прерван: {e}")
            duration = round(time.monotonic() - t0, 1)
            answers, flags = parse_chat_answers(content)
            per_q, score, stats = chat_verdict(answers)
            run = {
                "model": tag, "folder": folder, "provider": "cloud",
                "lang": KEY.get("lang", "ru"),
                "cloud_provider": cloud_provider,
                "thinking": {"requested": level, "scale": list(cfg["scale"]),
                             "sent": level, "note": cfg["doc_levels_note"]},
                "options": dict(cfg["thinking"](level) or {}),
                "model_version": resp.get("model_version") if not error else None,
                "prompt_version": prompt_ver, "prompt_sha256": prompt_sha,
                "started_utc": datetime.now(timezone.utc).isoformat(),
                "duration_s": duration, "error": error,
                "done_reason": done_reason, "usage": usage,
                "ps_snapshot": ["облако, /api/ps неприменим"],
                "parsed": {"answers": {str(k): v for k, v in sorted(answers.items())}, **flags},
                "verdict": {"score": score, "total": len(KEY["questions"]),
                            "stats": stats, "per_question": per_q},
            }
            (d / "run.json").write_text(
                json.dumps(run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            (d / "answer.txt").write_text(content, encoding="utf-8")
            for k in ("prompt_tokens", "completion_tokens"):
                total_usage[k] = (total_usage.get(k) or 0) + (usage.get(k) or 0)
            log(f"  run-{d.name[4:]} @{level}: {score}/24 "
                f"(json_ok={flags['json_ok']}, unparsed={stats['unparsed']}, "
                f"{duration}s, tok={usage.get('prompt_tokens', '?')}/"
                f"{usage.get('completion_tokens', '?')}, версия {run['model_version']})")
    spend_row(cloud_provider, tag, f"анкета DISC (quiz, {cloud_provider})",
              runs * len(levels), total_usage)
    log(f"  траты записаны в reports/spend.csv: {total_usage}")


# ---------------------------------------------------------------- конвейер прогона

def load_prompt() -> tuple[int, str, str]:
    data = json.loads((HERE / "prompts" / "prompt.json").read_text(encoding="utf-8"))
    prompt = data["prompt"]
    return data["version"], hashlib.sha256(prompt.encode()).hexdigest(), prompt


def next_run_dir(folder: str) -> Path:
    base = ROOT / "models" / folder / QUIZ_DIRNAME
    base.mkdir(parents=True, exist_ok=True)
    nums = [int(p.name.split("-")[1]) for p in base.glob("run-*") if p.name[4:].isdigit()]
    num = max(nums) + 1 if nums else 1
    d = base / f"run-{num:02d}"
    d.mkdir(exist_ok=True)
    return d


def set_lang_keys(key: dict) -> None:
    """Переключить глобальный ключ матчера (для rescore двух языков)."""
    global KEY
    KEY = key


def chat_verdict(answers: dict) -> tuple[list, int, dict]:
    """Вердикты по всем 24 вопросам + балл + счётчики флагов."""
    per_q = []
    score = 0
    for q in KEY["questions"]:
        m = match_answer(q, answers.get(q["n"]))
        m["correct"] = m["verdict"] == "correct"
        m.update({"n": q["n"], "answer": answers.get(q["n"], "")})
        per_q.append(m)
        score += 1 if m["verdict"] == "correct" else 0
    stats = {}
    for v in ("skipped", "unparsed", "ambiguous", "near"):
        stats[v] = sum(1 for x in per_q
                       if str(x.get("flag", "")).startswith(v) or x["verdict"] == v)
    return per_q, score, stats


def run_chat_block(tag: str, folder: str, levels: list, runs: int, prompt_ver: int,
                   prompt_sha: str, prompt: str, do_pilot: bool) -> None:
    scale = thinking_scale(tag)
    str_scale = [v for v in scale if isinstance(v, str)]
    log(f"{tag}: шкала /api/show = {scale or 'нет ручки'}; запрашиваем: {levels}")
    (ROOT / "models" / folder / "quiz").mkdir(parents=True, exist_ok=True)
    (ROOT / "models" / folder / "quiz" / "pilot.json").write_text(
        json.dumps({"scale": scale, "levels_requested": levels}, ensure_ascii=False) + "\n",
        encoding="utf-8")

    for level in levels:
        think, think_note = think_payload(level)
        # пилот: один выброшенный вызов перед блоком (если ещё не было удачного)
        if do_pilot:
            try:
                pilot = chat_call(tag, prompt, think)
                if pilot["content"].strip():
                    do_pilot = False
                    log(f"  пилот: ok ({len(pilot['content'])} симв., "
                        f"thinking={'есть' if pilot['thinking'] else 'нет'})")
                else:
                    log("  пилот: пустой ответ — блок продолжается, факт виден в прогонах")
            except RuntimeError as e:
                log(f"  пилот: {e}")
                if think is False:
                    think = None
                    think_note = "think=false отклонён сервером, off отправлен без ручки"
                    log("  think=false не принят — off идёт без ручки (факт в run.json)")
        for i in range(runs):
            d = next_run_dir(folder)
            t0 = time.monotonic()
            ps = ps_snapshot()
            contention = [m for m in ps if m and m != tag]
            try:
                resp = chat_call(tag, prompt, think)
                content, thinking, usage = resp["content"], resp["thinking"], resp["usage"]
                done_reason = resp.get("done_reason")
                error = None
            except RuntimeError as e:
                content, thinking, usage, done_reason, error = "", None, {}, None, str(e)
                log(f"  прогон прерван: {e}")
            duration = round(time.monotonic() - t0, 1)
            answers, flags = parse_chat_answers(content)
            per_q, score, stats = chat_verdict(answers)
            run = {
                "model": tag, "folder": folder, "provider": "chat",
                "lang": KEY.get("lang", "ru"),
                "thinking": {"requested": level, "scale": scale,
                             "sent": think, "note": think_note},
                "options": {"num_ctx": NUM_CTX, "num_predict": NUM_PREDICT},
                "prompt_version": prompt_ver, "prompt_sha256": prompt_sha,
                "started_utc": datetime.now(timezone.utc).isoformat(),
                "duration_s": duration, "error": error,
                "done_reason": done_reason, "usage": usage,
                "ps_snapshot": ps, "ollama_contention": bool(contention),
                "raw": content, "thinking_raw": thinking,
                "parsed": {"answers": {str(k): v for k, v in sorted(answers.items())}, **flags},
                "verdict": {"score": score, "total": len(KEY["questions"]),
                            "stats": stats, "per_question": per_q},
            }
            (d / "run.json").write_text(
                json.dumps(run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            (d / "answer.txt").write_text(content, encoding="utf-8")
            log(f"  run-{d.name[4:]} @{level}: {score}/24 "
                f"(json_ok={flags['json_ok']}, unparsed={stats['unparsed']}, "
                f"skipped={stats['skipped']}, {duration}s, "
                f"tok={usage.get('prompt_eval_count', '?')}/{usage.get('eval_count', '?')})")
        unload(tag)


def run_decision_block(tag: str, folder: str, runs: int) -> None:
    log(f"{tag}: decision-протокол /v1/systemone")
    for i in range(runs):
        d = next_run_dir(folder)
        t0 = time.monotonic()
        try:
            res = decision_run(tag, KEY)
            error = None
        except RuntimeError as e:
            res, error = {"per_question": [], "usage": {}}, str(e)
            log(f"  прогон прерван: {e}")
        duration = round(time.monotonic() - t0, 1)
        pq = res["per_question"]
        score = sum(1 for x in pq if x["correct"])
        pc = [x["p_correct"] for x in pq if x["p_correct"] is not None]
        flips = sum(1 for x in pq if x["chosen"] is None)
        run = {
            "model": tag, "folder": folder, "provider": "decision",
            "lang": KEY.get("lang", "ru"),
            "thinking": {"requested": None, "scale": [], "sent": None,
                         "note": "decision-протокол, ручки нет"},
            "prompt_version": PROMPT_VER, "prompt_sha256": PROMPT_SHA,
            "started_utc": datetime.now(timezone.utc).isoformat(),
            "duration_s": duration, "error": error,
            "usage": {"input_tokens": res["usage"]["input_tokens"],
                      "output_tokens": res["usage"]["output_tokens"]},
            "ps_snapshot": ps_snapshot(),
            "parsed": {"json_ok": None, "fallback": False},
            "verdict": {"score": score, "total": len(KEY["questions"]),
                        "p_correct_mean": round(sum(pc) / len(pc), 4) if pc else None,
                        "no_verdict_questions": flips, "per_question": pq},
        }
        (d / "run.json").write_text(
            json.dumps(run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        lines = []
        for x in pq:
            lines.append(f"Q{x['n']:>2}. {'верно' if x['correct'] else 'неверно'} — "
                         f"выбрано «{x['chosen']}» p={x['p_chosen']}, "
                         f"ключ «{x['key']}» p={x['p_correct']}")
        (d / "answer.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
        log(f"  run-{d.name[4:]}: {score}/24, p_correct="
            f"{run['verdict']['p_correct_mean']}, {duration}s, "
            f"tok={run['usage']['input_tokens']}/{run['usage']['output_tokens']}")
    unload(tag)


# ---------------------------------------------------------------- CLI

def load_matrix() -> list:
    return json.loads(MATRIX_PATH.read_text(encoding="utf-8"))["models"]


KEY = json.loads((HERE / "reference" / "key.json").read_text(encoding="utf-8"))
LANG = KEY.get("lang", "ru")            # активный язык матчера
QUIZ_DIRNAME = "quiz"                   # имя папки прогонов (quiz / quiz-en)
MATRIX_PATH = HERE / "models.json"
PROMPT_VER, PROMPT_SHA, PROMPT = load_prompt()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", help="тег модели (см. --list)")
    ap.add_argument("--thinking", default=None,
                    help="уровень мышления (по умолчанию — все существующие по /api/show)")
    ap.add_argument("--runs", type=int, default=5)
    ap.add_argument("--no-pilot", action="store_true")
    ap.add_argument("--rescore", action="store_true",
                    help="пересчитать вердикты chat-прогонов по сохранённым ответам "
                         "(без вызова моделей) — после правок матчера")
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()

    if args.rescore:
        # каждый прогон пересчитывается ключом СВОЕГО языка (run.json.lang)
        keys = {"ru": json.loads((HERE / "reference" / "key.json").read_text(encoding="utf-8")),
                "en": json.loads((HERE.parent / "quiz-en" / "reference" / "key-en.json")
                                 .read_text(encoding="utf-8"))}
        n = 0
        for pattern in ("models/*/quiz/run-*/run.json",
                        "models/*/quiz-en/run-*/run.json"):
            for p in sorted(ROOT.glob(pattern)):
                r = json.loads(p.read_text(encoding="utf-8"))
                if r.get("provider") != "chat":
                    continue
                runner_key = KEY
                try:  # матчеру нужен ключ нужного языка
                    set_lang_keys(keys[r.get("lang") or "ru"])
                except NameError:
                    pass
                answers = {int(k): v for k, v in
                           (r.get("parsed") or {}).get("answers", {}).items()}
                per_q, score, stats = chat_verdict(answers)
                r["verdict"] = {"score": score, "total": len(KEY["questions"]),
                                "stats": stats, "per_question": per_q}
                p.write_text(json.dumps(r, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                n += 1
        set_lang_keys(runner_key)  # вернуть исходное состояние
        log(f"rescore: пересчитано {n} chat-прогонов (оба языка)")
        return 0

    if args.list:
        for m in load_matrix():
            scale = thinking_scale(m["tag"]) if m["provider"] == "chat" else "decision"
            lv = requested_levels(m["doc_levels"], scale) if m["provider"] == "chat" else [None]
            print(f"{m['tag']:<45} {m['provider']:<9} шкала={scale or '—'} -> {lv}")
        return 0
    if not args.model:
        ap.error("укажите --model (или --list)")

    m = next((x for x in load_matrix() if x["tag"] == args.model), None)
    if not m:
        sys.exit(f"тег {args.model} не в quiz/models.json")

    if m["provider"] == "cloud":
        levels = args.thinking.split(",") if args.thinking else [l for l in m["doc_levels"] if l]
        run_cloud_block(m["tag"], m["folder"], levels, args.runs,
                        PROMPT_VER, PROMPT_SHA, PROMPT,
                        cloud_provider=m.get("cloud_provider", "deepseek"))
        return 0

    if m["provider"] == "decision":
        run_decision_block(m["tag"], m["folder"], args.runs)
        return 0

    scale = thinking_scale(m["tag"])
    levels = requested_levels(m["doc_levels"], scale)
    if args.thinking:
        if args.thinking not in levels:
            sys.exit(f"уровень {args.thinking} не поддерживается (шкала={scale}, доступно {levels})")
        levels = [args.thinking]
    run_chat_block(m["tag"], m["folder"], levels, args.runs,
                   PROMPT_VER, PROMPT_SHA, PROMPT, do_pilot=not args.no_pilot)
    return 0


if __name__ == "__main__":
    sys.exit(main())
