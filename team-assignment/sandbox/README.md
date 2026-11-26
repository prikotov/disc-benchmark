# Песочница для pi-агентов (bubblewrap, Linux-native)

Изоляция агентных сессий при командных прогонах (`team-assignment/`) без
Docker — средствами ядра Linux (bubblewrap + user namespaces). Паттерн
перенесён из производственной механики публичного чата AI Team в TasK
(`PublicAgentBubblewrapCommandBuilder`) и адаптирован: LLM-провайдер —
не gateway-nginx, а ollama по TCP (`OLLAMA_BASE_URL`).

Зачем: официальная model card inkling-2-mini прямо предупреждает — модель
«может совершать деструктивные действия (удалять/перезаписывать файлы)
без подтверждения» и «неверно отчитываться о сделанном». Общий риск
контейнмента известен и без того (выходы агентов за workdir фиксировались
в test-assignment). Песочница делает такие действия **невозможными**, а не
только обнаруживаемыми постфактум.

## Гарантии

| Слой | Что изолировано |
|---|---|
| Файловая система | видны только `/usr`,`/bin`,`/lib`,`/lib64` (ro), `/proc` (ro), минимальный `/dev`, `/tmp` (tmpfs), **workdir (RW)** и явно перечисленные ro-bind'ы. Домашний каталог, репозиторий, `.env.local`, ключи — не смонтированы вовсе |
| Переменные среды | `--clearenv`; внутрь — allowlist: `PATH`, `HOME=/work`, `TMPDIR=/work/tmp`, `LANG/LC_ALL`, `PI_CODING_AGENT_DIR=/work/.pi-home`, `PROMPT`. Секреты и прокси хоста не проходят |
| Процесс | отдельные user/pid/ipc/uts namespaces; `--die-with-parent` (гибель родителя гасит песочницу); `--new-session` |
| pi | изолированный `PI_CODING_AGENT_DIR` (по образцу `test-assignment/runner.py`): `models.json` генерируется на лету, глобальный `~/.pi/agent` не виден |
| Сеть | `host` (по умолчанию) — общая с хостом, нужна для LLM; `none` (`--unshare-net`) — для агентов без сети |

## Ограничения (честно)

- **Сеть не фильтруется по назначению**: bubblewrap не умеет egress-политику.
  Смягчение: секреты в песочнице невидимы и env пуст — красть нечего;
  модельная карточка допускает «деструктивные действия с файлами» — файлы
  вне workdir недостижимы. Строгий вариант (pasta/slirp4netns с allowlist
  назначений) — отдельная задача, не блокирует серию.
- **Эфемерные каталоги-маунтпойнты** (`/etc`, `/home` и пр. — точки
  монтирования) writable внутри namespace, но умирают вместе с ним; хост
  не затрагивается (проверено selfcheck).
- `/proc` read-only, `/dev` минимальный — node/pi работают, GPU не нужен
  (инференс на nserv).

## Файлы

- **`pi-sandbox.sh`** — запуск. Всё через env (конвенция workspace,
  захардкоженных путей нет); полный список переменных — в шапке скрипта.
  Минимальный пример:

  ```bash
  SANDBOX_WORKDIR=/tmp/run-01 \
  PI_MODEL=inkling-2-mini:pi-128k \
  PI_BASE_URL="$OLLAMA_BASE_URL" \
  ./pi-sandbox.sh "Ответь одним словом: сколько будет 9*9?"
  ```

  Режим `SANDBOX_CMD` запускает произвольную команду вместо pi (smoke,
  самопроверки). Доп. read-only маунты — `SANDBOX_RO_BINDS="SRC:TGT,…"`.
  Собранная bwrap-команда печатается в stderr — попадает в `pi-run.log`
  как провенанс прогона.

- **`selfcheck.sh`** — машинная проверка песочницы (запускать перед серией,
  можно из `check.py`): 1) секреты хоста невидимы; 2) env без секретов;
  3) запись только в workdir; 4) сеть до ollama; 5) живой LLM-ответ
  (санити 9×9=81). Самопроверка пинает `PI_PROVIDER=ollama` явно — не
  должна зависеть от ambient env хоста.

## Интеграция с командным заданием

- Один сабагент = один вызов `pi-sandbox.sh`; workdir — каталог прогона
  (`run-XX`), общий для команды (файлы как среда обмена, см.
  `../ORCHESTRATION.md`); каждый агент получает собственный
  `.pi-home` внутри workdir.
- Прогон-раннер задаёт `PI_MODEL`/`PI_BASE_URL`/`PI_THINKING` из `run.json`
  условий; фактический провайдер фиксируется в `run.json` (не полагаться
  на ambient env хоста).
- Пост-проверка контейнмента (`git status` + посторонние файлы) остаётся
  в силе — теперь как контроль корректности песочницы, а не поиск ущерба.

## Провенанс

- Паттерн: `~/MyProjects/TasK/Development/src/Module/PublicAgent/
  Infrastructure/Component/Pi/PublicAgentBubblewrapCommandBuilder.php`
  (bwrap-argv: unshare user/pid/ipc/uts/cgroup, clearenv, ro-runtime-roots,
  bind session root, resolver+CA при сети, HOME=workdir, минимальный PATH).
- Отличия от TasK: нет gateway-policy (у нас ollama TCP, политика `host`);
  нет capability-модели оркестратора (раннер pi сам решает, что запускать);
  роль/промпт подаются через `SANDBOX_PROMPT`, а не ro-bind файла.
