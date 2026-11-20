#!/usr/bin/env python3
"""Разовый прогон модели через pi-подписку (pi -p, OAuth-провайдеры типа
kimi-coding): 1 прогон на каждый документированный уровень мышления.

Отличие от runner.py: транспорт pi-подписки с прямым non-stream вызовом
(pi сам refresh'ит OAuth-токен; streaming-транспорт pi рвёт соединение на
длинной генерации). Скоринг и артефакты — общие (quiz.runner).

Запуск: python3 quiz/kimi-run.py --lang ru --model kimi-coding/k3.1-pro \
    --folder kimi-k3.1-pro --levels low,high,max
"""
import argparse
import hashlib
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import runner as R  # noqa: E402

PI_TIMEOUT = 1500          # 25 мин на вызов (max-thinking длинный)
KIMI_URL = "https://api.kimi.com/coding/v1/chat/completions"


def kimi_token() -> str:
    """Access-токен подписки kimi-coding из pi-auth (refresh делает pi; при
    401 — дергаем pi-тестовый вызов и перечитываем токен)."""
    a = json.loads((Path.home() / ".pi/agent/auth.json").read_text())
    return a["kimi-coding"]["access"]


def api_call(model_short: str, level: str, prompt: str,
             timeout: int = PI_TIMEOUT) -> tuple[str, str | None, str, dict]:
    """Прямой non-stream вызов api.kimi.com (pi-транспорт со streaming рвёт
    соединение на длинной генерации: UND_ERR_SOCKET/ECONNRESET ×6 —
    наблюдение 2026-11-17; подписка та же, токен из pi-auth).
    Возвращает (content, thinking, длительность, usage)."""
    body = {"model": model_short,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False}
    if level:
        body["reasoning_effort"] = level
    t0 = time.monotonic()
    for attempt in range(2):
        req = urllib.request.Request(KIMI_URL, data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {kimi_token()}"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                d = json.loads(r.read())
            msg = (d.get("choices") or [{}])[0].get("message") or {}
            content = msg.get("content") or ""
            thinking = msg.get("reasoning_content")
            content, embedded = R.strip_think(content)
            if thinking is None and embedded:
                thinking = embedded
            dur = f"{round(time.monotonic() - t0, 1)}s"
            u = d.get("usage") or {}
            usage = {"prompt_tokens": u.get("prompt_tokens"),
                     "completion_tokens": u.get("completion_tokens")}
            return content, thinking, dur, usage
        except urllib.error.HTTPError as e:
            if e.code == 401 and attempt == 0:
                # токен протух — pi refresh (тестовый вызов) и повтор
                subprocess.run(["pi", "-p", "--no-session", "--model",
                                "kimi-coding/k3.1-pro", "Ответь: ok"],
                               capture_output=True, text=True, timeout=300,
                               env={"PATH": "/home/dp/.npm-global/bin:" +
                                    __import__("os").environ["PATH"],
                                    "HOME": str(Path.home())})
                continue
            raise RuntimeError(f"HTTP {e.code}: {e.read()[:200].decode(errors='ignore')}")
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            if attempt == 0:
                time.sleep(10)
                continue
            raise RuntimeError(str(e)[:200])
    raise RuntimeError("не ответил после 2 попыток")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--lang", choices=["ru", "en"], required=True)
    ap.add_argument("--model", required=True, help="модель для pi: provider/id")
    ap.add_argument("--folder", required=True, help="папка в models/ (артefакты)")
    ap.add_argument("--levels", default="low,high,max")
    ap.add_argument("--scale-note", default="")
    args = ap.parse_args()

    if args.lang == "ru":
        R.KEY = json.loads((HERE / "reference" / "key.json").read_text(encoding="utf-8"))
        prompt_path = HERE / "prompts" / "prompt.json"
    else:
        R.KEY = json.loads((HERE.parent / "quiz-en" / "reference" / "key-en.json")
                           .read_text(encoding="utf-8"))
        prompt_path = HERE.parent / "quiz-en" / "prompts" / "prompt.json"
    R.LANG = R.KEY["lang"]
    R.QUIZ_DIRNAME = "quiz" if args.lang == "ru" else "quiz-en"
    data = json.loads(prompt_path.read_text(encoding="utf-8"))
    pver, psha, prompt = data["version"], hashlib.sha256(
        data["prompt"].encode()).hexdigest(), data["prompt"]

    levels = args.levels.split(",")
    scale_note = args.scale_note or f"документированные уровни: {', '.join(levels)}"
    log = R.log
    log(f"{args.model} [{args.lang}] через pi-подписку: уровни {levels}")

    for level in levels:
        d = R.next_run_dir(args.folder)
        t0 = time.monotonic()
        try:
            content, thinking, dur_note, usage = api_call(
                args.model.split("/")[-1], level, prompt)
            error = None
        except (RuntimeError, subprocess.TimeoutExpired) as e:
            content, thinking, dur_note, usage = "", None, None, {}
            error = str(e)[:300]
            log(f"  прогон прерван: {error}")
        duration = round(time.monotonic() - t0, 1)
        answers, flags = R.parse_chat_answers(content)
        per_q, score, stats = R.chat_verdict(answers)
        run = {
            "model": args.model, "folder": args.folder,
            "provider": "cloud", "lang": R.KEY.get("lang", "ru"),
            "cloud_provider": "kimi-coding (pi-подписка)",
            "transport": "прямой non-stream (pi-streaming рвётся на длинной генерации)",
            "thinking": {"requested": level or None, "scale": levels,
                         "sent": level or None, "note": scale_note},
            "options": {"reasoning_effort": level} if level else {},
            "model_version": args.model.split("/")[-1],
            "prompt_version": pver, "prompt_sha256": psha,
            "started_utc": datetime.now(timezone.utc).isoformat(),
            "duration_s": duration, "error": error,
            "done_reason": dur_note, "usage": usage,
            "ps_snapshot": ["облако (pi-подписка), /api/ps неприменим"],
            "parsed": {"answers": {str(k): v for k, v in sorted(answers.items())}, **flags},
            "verdict": {"score": score, "total": len(R.KEY["questions"]),
                        "stats": stats, "per_question": per_q},
        }
        (d / "run.json").write_text(
            json.dumps(run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (d / "answer.txt").write_text(content, encoding="utf-8")
        log(f"  run-{d.name[4:]} @{level or 'default'}: {score}/24 "
            f"(json_ok={flags['json_ok']}, unparsed={stats['unparsed']}, "
            f"{duration}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
