#!/usr/bin/env bash
# pi-агент в песочнице bubblewrap — запуск команды/LLM-сессии изолированно.
#
# Паттерн перенесён из TasK (PublicAgentBubblewrapCommandBuilder, публичный
# чат AI Team) и адаптирован под прогоны disc: LLM-провайдер — голый TCP
# (ollama на OLLAMA_BASE_URL), поэтому сетевая политика — host (см. README,
# раздел «Ограничения»).
#
# Гарантии:
#   - ФС: видны ТОЛЬКО /usr,/bin,/lib,/lib64 (ro), /proc (ro), /dev (мин.),
#     /tmp (tmpfs), workdir (RW) и явно перечисленные ro-bind'ы.
#     Домашний каталог хоста, репозиторий, секреты — не смонтированы.
#   - env: --clearenv, внутрь передаётся только allowlist (PATH/HOME/TMPDIR/
#     LANG/LC_ALL/PI_CODING_AGENT_DIR + опциональные прокси).
#   - Процесс: отдельные user/pid/ipc/uts namespaces, die-with-parent
#     (гибель песочницы при гибели родителя), new-session.
#   - pi получает изолированный PI_CODING_AGENT_DIR (models.json генерируется
#     на лету — по образцу test-assignment/runner.py).
#
# Всё задаётся env — никаких захардкоженных путей (конвенция workspace):
#   SANDBOX_WORKDIR     (обязателен) каталог прогона, монтируется RW на /work
#   PI_BIN              путь к pi (по умолчанию: `command -v pi`)
#   PI_MODEL            (обязателен) тег модели
#   PI_PROVIDER         провайдер pi (по умолчанию: ollama)
#   PI_BASE_URL         baseUrl провайдера (по умолчанию: $OLLAMA_BASE_URL;
#                       обязателен, если OLLAMA_BASE_URL не задан)
#   PI_CONTEXT          contextWindow в models.json (по умолчанию 131072)
#   PI_MAX_TOKENS       maxTokens в models.json (по умолчанию 32768)
#   PI_THINKING         уровень мышления (по умолчанию: low)
#   SANDBOX_PI_HOME     готовый pi-home (ro-источник); иначе генерируется
#                       в workdir/.pi-home
#   SANDBOX_NETWORK     host | none (по умолчанию host; none = --unshare-net)
#   SANDBOX_RO_BINDS    доп. ro-маунты через ':' — "SRC:TGT[,SRC:TGT…]"
#   SANDBOX_ENV_PREFIX  префиксы env хоста для проброса внутрь через запятую
#                       (напр. "DISC_") — значения хоста по этим префиксам
#                       попадают в песочницу через --setenv
#   SANDBOX_PI_ARGS     доп. аргументы pi (напр. "--session-dir /work/pi-session")
#   SANDBOX_PROMPT      текст промпта; иначе читается первый аргумент скрипта
#   SANDBOX_CMD         вместо pi запускает команду (smoke/самопроверки)
#
# Примеры:
#   SANDBOX_WORKDIR=/tmp/run-01 PI_MODEL=inkling-2-mini:pi-128k \
#     ./pi-sandbox.sh "Ответь одним словом: сколько будет 9*9?"
#   SANDBOX_WORKDIR=/tmp/run-01 SANDBOX_CMD='/bin/bash /work/smoke.sh' \
#     PI_MODEL=x ./pi-sandbox.sh
set -euo pipefail

die() { printf '%s\n' "pi-sandbox: $*" >&2; exit 2; }

WORKDIR="${SANDBOX_WORKDIR:-}"
[ -n "$WORKDIR" ] || die "задай SANDBOX_WORKDIR"
[ -d "$WORKDIR" ] || die "SANDBOX_WORKDIR не существует: $WORKDIR"
WORKDIR="$(cd "$WORKDIR" && pwd)"

# Путь как есть (без readlink): симлинк bin/pi указывает внутрь пакета,
# а нужен именно стабильный корень (…/npm-global) для ro-bind и PATH.
PI_BIN="${PI_BIN:-$(command -v pi || true)}"
[ -n "$PI_BIN" ] && [ -x "$PI_BIN" ] || die "pi не найден; задай PI_BIN"
PI_BIN_ROOT="$(dirname "$(dirname "$PI_BIN")")"   # …/npm-global/bin/pi -> …/npm-global
PI_PROVIDER="${PI_PROVIDER:-ollama}"   # явный дефолт: не брать случайное из env хоста

MODEL="${PI_MODEL:-}"
[ -n "$MODEL" ] || { [ -n "${SANDBOX_CMD:-}" ] || die "задай PI_MODEL"; MODEL="none"; }

BASE_URL="${PI_BASE_URL:-${OLLAMA_BASE_URL:-}}"
[ -n "$BASE_URL" ] || { [ -n "${SANDBOX_CMD:-}" ] || die "задай PI_BASE_URL или OLLAMA_BASE_URL"; BASE_URL="unused"; }

NETWORK="${SANDBOX_NETWORK:-host}"
case "$NETWORK" in host|none) ;; *) die "SANDBOX_NETWORK: host|none" ;; esac

THINKING="${PI_THINKING:-low}"
CONTEXT="${PI_CONTEXT:-131072}"
MAX_TOKENS="${PI_MAX_TOKENS:-32768}"

PROMPT="${SANDBOX_PROMPT:-${1:-}}"

# --- pi-home: готовый (ro) или сгенерированный в workdir --------------------
PI_HOME_SRC="${SANDBOX_PI_HOME:-}"
PI_HOME_INNER="/work/.pi-home"
if [ -z "$PI_HOME_SRC" ]; then
  PI_HOME_SRC="$WORKDIR/.pi-home-src"
  mkdir -p "$PI_HOME_SRC"
  python3 - "$PI_HOME_SRC" "$BASE_URL" "$MODEL" "$CONTEXT" "$MAX_TOKENS" "$PI_PROVIDER" <<'PYEOF'
import json, sys
dst, base, model, ctx, maxtok, provider = sys.argv[1:7]
providers = {provider: {"baseUrl": base.rstrip('/') + "/v1", "api": "openai-completions",
    "apiKey": "sandbox", "models": [{"id": model, "contextWindow": int(ctx),
    "maxTokens": int(maxtok), "reasoning": True,
    "thinkingLevelMap": {"off": "false", "low": "low", "medium": "medium", "high": "high"}}]}}
open(dst + "/models.json", "w").write(json.dumps({"providers": providers}, indent=2))
PYEOF
fi
[ -f "$PI_HOME_SRC/models.json" ] || die "в SANDBOX_PI_HOME нет models.json: $PI_HOME_SRC"

mkdir -p "$WORKDIR/tmp"

# --- сборка argv bubblewrap --------------------------------------------------
ARGS=(
  bwrap
  --die-with-parent --new-session --clearenv
  --unshare-user --unshare-pid --unshare-ipc --unshare-uts --unshare-cgroup-try
)
[ "$NETWORK" = "none" ] && ARGS+=( --unshare-net )

ARGS+=( --proc /proc --dev /dev --tmpfs /tmp )   # свежий procfs: хостовая таблица процессов не видна (НЕ --ro-bind /proc)

# runtime roots + корень pi (нода и библиотеки pi живут вне /usr)
for r in /usr /bin /lib /lib64 "$PI_BIN_ROOT"; do
  [ -d "$r" ] && ARGS+=( --ro-bind "$r" "$r" )
done

# резолвер и CA — только при host-сети; отсутствующие файлы пропускаем
if [ "$NETWORK" = "host" ]; then
  for f in /etc/hosts /etc/resolv.conf /etc/nsswitch.conf \
           /etc/ssl/cert.pem /etc/pki/tls/cert.pem /etc/pki/tls/certs/ca-bundle.crt; do
    [ -e "$f" ] && ARGS+=( --ro-bind "$f" "$f" )
  done
  [ -d /etc/ssl/certs ] && ARGS+=( --ro-bind /etc/ssl/certs /etc/ssl/certs )
fi

# дополнительные read-only маунты "SRC:TGT[,SRC:TGT…]"
if [ -n "${SANDBOX_RO_BINDS:-}" ]; then
  IFS=',' read -ra PAIRS <<< "$SANDBOX_RO_BINDS"
  for p in "${PAIRS[@]}"; do
    SRC="${p%%:*}"; TGT="${p#*:}"
    [ -e "$SRC" ] || die "SANDBOX_RO_BINDS: нет источника $SRC"
    ARGS+=( --ro-bind "$SRC" "$TGT" )
  done
fi

# pi-home — ro внутрь; рабочая копия сделает сам invoked shell
ARGS+=( --ro-bind "$PI_HOME_SRC" /pi-home-ro )

ARGS+=(
  --bind "$WORKDIR" /work
  --chdir /work
  --setenv HOME /work
  --setenv TMPDIR /work/tmp
  --setenv PATH "$PI_BIN_ROOT/bin:/usr/local/bin:/usr/bin:/bin"  # bin/pi живёт в $PI_BIN_ROOT/bin
  --setenv LANG ru_RU.UTF-8
  --setenv LC_ALL ru_RU.UTF-8
)

# проброс env хоста по префиксам (напр. DISC_* для продуктового окружения)
if [ -n "${SANDBOX_ENV_PREFIX:-}" ]; then
  IFS=',' read -ra PREFIXES <<< "$SANDBOX_ENV_PREFIX"
  for p in "${PREFIXES[@]}"; do
    while IFS='=' read -r k v; do
      [ -n "$k" ] && ARGS+=( --setenv "$k" "$v" )
    done < <(env | grep "^${p}=" || true)
  done
fi

if [ -n "${SANDBOX_CMD:-}" ]; then
  INNER="$SANDBOX_CMD"
else
  [ -n "$PROMPT" ] || die "задай SANDBOX_PROMPT или первый аргумент"
  INNER="mkdir -p /work/.pi-home && cp /pi-home-ro/models.json /work/.pi-home/ \\
    && PI_CODING_AGENT_DIR=/work/.pi-home pi -p ${SANDBOX_PI_ARGS:-} \\
       --provider $PI_PROVIDER --model $MODEL --thinking $THINKING \\
       \"\$PROMPT\""
  ARGS+=( --setenv PROMPT "$PROMPT" )
fi

# журнал argv (провенанс прогона)
printf '%q ' "${ARGS[@]}" >&2
printf ' -- /bin/sh -c %q\n' "$INNER" >&2

exec "${ARGS[@]}" -- /bin/sh -c "$INNER"
