#!/usr/bin/env python3
"""Один агентный прогон тестового задания через pi (копирование DISC-теста).

Адаптация runner_pi.py сестринского workspace (~/MyProjects/Models). Ключевые
свойства сохранены:

- глобальный конфиг pi (~/.pi/agent) НЕ используется: каждый прогон получает
  собственный PI_CODING_AGENT_DIR во временном каталоге, models.json для
  единственной модели собирается на лету (thinkingLevelMap — из /api/show
  фактической шкалы модели);
- рабочая директория агента — временный каталог ВНЕ репозитория: в контекст
  агента не попадает ни AGENTS.md, ни эталон (reference/), ни результаты;
- pi — лидер собственной process group: SIGTERM/таймаут гасят всю группу;
- pi-run.log пишется стримингом (живой просмотр: tail -f);
- фоновый наблюдатель /api/ps фиксирует чужие модели в VRAM (конкуренция) —
  факт попадает в run.json;
- артефакты: run.json, pi-session/ (JSONL-след), pi-run.log, всё, что агент
  создал в рабочей директории (ожидается index.html), копируется в run-XX.

Отличия от сестринского: без скелета-репозитория (задание передаётся целиком
в промпте из prompts/prompt.json), без диффа (решение создаётся с нуля).

Запуск:
    python3 test-assignment/runner.py --model huihui-ai:pi-100k \
        --thinking low --results models/huihui-ai-pi-100k/test-assignment/run-01
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent          # test-assignment/
ROOT = HERE.parent                              # корень disc

DEFAULT_CONTEXT = 102_400
DEFAULT_TIMEOUT = 3600
DEFAULT_THINKING = "low"

PI_LEVELS_RANKED = ["low", "medium", "high", "xhigh", "max"]
PI_CHOICES = ["off", "minimal", *PI_LEVELS_RANKED]


def log(msg: str) -> None:
    print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] {msg}", flush=True)


def repo_root() -> Path:
    for parent in HERE.parents:
        if (parent / ".git").is_dir():
            return parent
    return ROOT


def env_var(name: str) -> str:
    """env, затем .env.local корня репозитория."""
    v = os.environ.get(name)
    if v:
        return v.strip()
    env_local = repo_root() / ".env.local"
    if env_local.is_file():
        for line in env_local.read_text().splitlines():
            if line.startswith(name + "="):
                return line.split("=", 1)[1].strip()
    sys.exit(f"задайте {name} (env или .env.local)")


def ollama_base_url() -> str:
    return env_var("OLLAMA_BASE_URL").rstrip("/")


def model_thinking_values(model: str) -> list:
    import urllib.request
    try:
        req = urllib.request.Request(
            f"{ollama_base_url()}/api/show",
            data=json.dumps({"model": model}).encode(),
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as r:
            d = json.loads(r.read())
        t = d.get("thinking") if isinstance(d.get("thinking"), dict) else {}
        return list(t.get("values") or [])
    except OSError:
        return []


def thinking_map_for(values: list) -> tuple[dict, bool]:
    """Карта уровней pi -> значения модели + признак «энергичный максимум».
    Несуществующее значение ollama молча подменяет дефолтом, поэтому карту
    строим из фактической шкалы /api/show. pi валидирует значения карты как
    СТРОКИ (boolean true ломает models.json целиком)."""
    levels = [v for v in values if isinstance(v, str)]
    top = None
    for cand in reversed(PI_LEVELS_RANKED):
        if cand in levels:
            top = cand
            break
    m: dict = {}
    for pi_level in ("off", "minimal", "low", "medium", "high", "xhigh", "max"):
        if pi_level == "off":
            m[pi_level] = "none"
        elif pi_level in levels:
            m[pi_level] = pi_level
        elif top is not None:
            m[pi_level] = top
        else:
            m[pi_level] = "high"   # boolean-шкалы: любая строка -> true
    eager = top in ("xhigh", "max")
    return m, eager


def load_prompt() -> tuple[dict, str]:
    p = HERE / "prompts" / "prompt.json"
    d = json.loads(p.read_text(encoding="utf-8"))
    return d, d["prompt"]


class PiRun:
    """pi — лидер собственной process group; остановка убивает группу."""

    def __init__(self, cmd: list[str], cwd: Path, env: dict[str, str], log_path: Path) -> None:
        self.log = log_path.open("w", encoding="utf-8")
        self.proc = subprocess.Popen(cmd, cwd=cwd, env=env, stdout=self.log,
                                     stderr=subprocess.STDOUT, text=True,
                                     start_new_session=True)
        self.killed = False

    def wait(self, timeout: int) -> int:
        try:
            return self.proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            self.terminate(reason="timeout")
            return self.proc.returncode if self.proc.returncode is not None else 124

    def terminate(self, reason: str = "signal") -> None:
        if self.proc.poll() is None:
            self.killed = True
            print(f"остановка pi ({reason}): убиваю группу {self.proc.pid}", file=sys.stderr)
            try:
                os.killpg(self.proc.pid, signal.SIGTERM)
                try:
                    self.proc.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    os.killpg(self.proc.pid, signal.SIGKILL)
                    self.proc.wait(timeout=10)
            except ProcessLookupError:
                pass
        if not self.log.closed:
            self.log.close()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--model", required=True, help="ollama-тег (например huihui-ai:pi-100k)")
    ap.add_argument("--results", required=True, help="каталог результатов run-XX")
    ap.add_argument("--thinking", default=DEFAULT_THINKING, choices=PI_CHOICES)
    ap.add_argument("--context", type=int, default=DEFAULT_CONTEXT)
    ap.add_argument("--max-tokens", type=int, default=8192)
    ap.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    ap.add_argument("--smoke", action="store_true",
                    help="проверка сантехники: короткий промпт вместо задания")
    ap.add_argument("--keep", action="store_true", help="не удалять временные каталоги")
    args = ap.parse_args()

    results = Path(args.results).resolve()
    results.mkdir(parents=True, exist_ok=True)

    prompt_data, prompt_text = load_prompt()
    smoke_prompt = "Создай в текущем каталоге файл answer.txt с текстом 'ok' (без кавычек) и заверши работу."
    if args.smoke:
        prompt_text = smoke_prompt

    tmp = Path(tempfile.mkdtemp(prefix="disc-pi-"))
    repo = tmp / "run"          # рабочая директория агента (вне репозитория!)
    started = time.time()

    scale = model_thinking_values(args.model)
    if scale:
        _, eager = thinking_map_for(scale)
        if args.max_tokens == 8192 and eager:
            args.max_tokens = 32768
            log("энергичный максимум в шкале модели: maxTokens поднят до 32768")
    else:
        log("внимание: thinking-шкала модели пуста — reasoning-флаг не ставим")

    meta: dict = {
        "model": args.model,
        "provider": "ollama",
        "thinking": args.thinking,
        "thinking_scale": scale,
        "context": args.context,
        "max_tokens": args.max_tokens,
        "timeout_s": args.timeout,
        "smoke": args.smoke,
        "prompt_version": prompt_data.get("version"),
        "prompt_task": prompt_data.get("task"),
        "prompt_sha256": hashlib.sha256(prompt_text.encode()).hexdigest()[:16],
        "started_at": datetime.now(timezone.utc).isoformat(),
    }

    # models.json на лету
    pi_home = tmp / "pi-home"
    pi_home.mkdir()
    entry = {"id": args.model, "contextWindow": args.context, "maxTokens": args.max_tokens}
    if scale:
        entry["reasoning"] = True
        entry["thinkingLevelMap"] = thinking_map_for(scale)[0]
    providers = {"ollama": {"baseUrl": f"{ollama_base_url()}/v1",
                            "api": "openai-completions", "apiKey": "ollama",
                            "models": [entry]}}
    (pi_home / "models.json").write_text(
        json.dumps({"providers": providers}, ensure_ascii=False, indent=2), encoding="utf-8")

    run_holder: dict[str, PiRun] = {}
    stop_watch = threading.Event()
    foreign_models: list[str] = []

    def watch_ollama_foreign() -> None:
        import urllib.request
        while True:
            try:
                with urllib.request.urlopen(f"{ollama_base_url()}/api/ps", timeout=10) as r:
                    for m in json.loads(r.read()).get("models", []):
                        name = m.get("name", "")
                        if name and name != args.model and name not in foreign_models:
                            foreign_models.append(name)
            except Exception:
                pass
            if stop_watch.wait(30):
                return

    def on_signal(signum, _frame) -> None:
        if (r := run_holder.get("run")) is not None:
            r.terminate(reason=f"signal {signum}")

    signal.signal(signal.SIGTERM, on_signal)
    signal.signal(signal.SIGINT, on_signal)

    rc = None
    run: PiRun | None = None
    try:
        repo.mkdir()
        threading.Thread(target=watch_ollama_foreign, daemon=True).start()

        cmd = ["pi", "-p",
               "--session-dir", str(results / "pi-session"),
               "--model", args.model,
               "--thinking", args.thinking,
               prompt_text]
        env = {**dict(os.environ),
               "PI_CODING_AGENT_DIR": str(pi_home),
               "PI_OFFLINE": "1"}
        log(f"запуск: pi -p --model {args.model} --thinking {args.thinking} (ctx {args.context})")
        log(f"  cwd={repo}\n  pi-home={pi_home} (изолирован)\n  лог (live): {results / 'pi-run.log'}")

        run = PiRun(cmd, repo, env, results / "pi-run.log")
        run_holder["run"] = run
        rc = run.wait(timeout=args.timeout)
        elapsed = time.strftime("%H:%M:%S", time.gmtime(time.time() - started))
        log(f"pi завершился: код={rc}, убит={'да' if run.killed else 'нет'}, время={elapsed}")
        meta["exit_code"] = rc
        meta["killed"] = run.killed

        # всё, что агент создал, копируем в run-XX (ожидается index.html)
        created = sorted(p for p in repo.rglob("*") if p.is_file())
        for p in created:
            rel = p.relative_to(repo)
            dst = results / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, dst)
        meta["files"] = [{"path": str(p.relative_to(repo)), "bytes": p.stat().st_size}
                         for p in created]
        meta["index_html"] = (results / "index.html").is_file()
        log(f"артефакты агента: {len(created)} файл (ов); index.html: {meta['index_html']}")

        session_files = sorted((results / "pi-session").glob("*.jsonl")) if (results / "pi-session").is_dir() else []
        meta["session_files"] = [p.name for p in session_files]
        log(f"сессия: {len(session_files)} файл(ов) JSONL"
            + (f", последний: {session_files[-1].name}" if session_files else " — НЕ СОЗДАНА, проверить!"))
        return rc if rc is not None else 1
    finally:
        stop_watch.set()
        if foreign_models:
            meta["ollama_contention"] = True
            meta["ollama_foreign_models"] = sorted(foreign_models)
        meta["finished_at"] = datetime.now(timezone.utc).isoformat()
        meta["duration_s"] = round(time.time() - started, 1)
        if run is not None:
            meta.setdefault("exit_code", run.proc.returncode)
            meta["killed"] = run.killed
        (results / "run.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if args.keep:
            print(f"(keep) временные каталоги: {tmp}")
        else:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
