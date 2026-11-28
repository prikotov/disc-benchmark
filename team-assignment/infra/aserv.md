# aserv: провижининг прод-деплоя команд

Одноразовые шаги владельца на aserv (ai-aid.pro) перед серией полных
прогонов. Схема проверена тестовым стендом 2026-11-28 (результаты —
в `../INFRA.md` §3). Все пути и паттерны здесь — рабочие, проверенные.

Секреты в этот файл и в git не попадают: значения подставляются из
вопросов владельца на сервере.

## 1. Пользователь и каталог

```bash
sudo useradd -m -s /bin/bash disc          # shell нужен владельцу каталога,
                                            # агенту он недоступен (rrsync -wo)
sudo mkdir -p /srv/disc
sudo chown disc:disc /srv/disc
sudo chmod 750 /srv/disc                   # листинг только у владельца
```

## 2. Пул php-fpm `wwwdisc` (второй слой изоляции)

`/etc/php-fpm.d/wwwdisc.conf`:

```ini
[wwwdisc]
user = disc
group = disc
listen = /run/php-fpm/wwwdisc.sock
listen.acl_users = nginx
pm = dynamic
pm.max_children = 4
pm.start_servers = 1
pm.min_spare_servers = 1
pm.max_spare_servers = 2
php_admin_value[open_basedir] = /srv/disc
php_admin_value[error_log] = /var/log/php-fpm/wwwdisc-error.log
php_admin_flag[log_errors] = on
```

```bash
sudo systemctl enable --now php-fpm && sudo systemctl reload php-fpm
```

(Отдельный пул — чтобы код команд выполнялся юзером `disc`, а не
apache/wwwtask; `php_admin_value` в пуле — второй слой после
per-request `PHP_VALUE` из nginx.)

## 3. Nginx: generic-блок для всех версий

Вставить в `server { server_name task.ai-aid.pro; … }`
(`/etc/nginx/conf.d/task.ai-aid.pro.conf`) **до** существующего
`location ~ \.php$`:

```nginx
    # ---- DISC team deployments (generic, версия = каталог) ----
    location ^~ /disc-v- {
        try_files $uri $uri/ =404;

        location ~ ^/disc-v-(?<ver>[^/]+)(?<rest>/.*)\.php$ {
            include fastcgi_params;
            fastcgi_pass unix:/run/php-fpm/wwwdisc.sock;
            fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
            fastcgi_param PHP_VALUE "open_basedir=/srv/disc/disc-v-$ver
upload_tmp_dir=/srv/disc/disc-v-$ver/var/tmp";
            # секреты продакшена: значения вписывает владелец, в git не
            # попадают; код команд читает их из $_SERVER
            fastcgi_param DISC_SMTP_DSN "<из .env.local владельца>";
            fastcgi_param DISC_LLM_BASE_URL "<…>";
            fastcgi_param DISC_LLM_MODEL "<…>";
            fastcgi_param DISC_LLM_KEY "<…>";
        }
    }
```

Проверено на nginx 1.20.1: root-паттерн + захват `$ver` в php-локейшне;
паттерн с `alias` — сломан (не использовать). После вставки:
`nginx -t && systemctl reload nginx`.

## 4. rrsync (канал деплоя без shell)

```bash
curl -fsSL -o /tmp/rrsync https://raw.githubusercontent.com/RsyncProject/rsync/master/rrsync \
  && sudo install -m 0755 /tmp/rrsync /usr/local/bin/rrsync
```

## 5. SSH-ключ и forced command

```bash
ssh-keygen -t ed25519 -f ~/.disc-keys/disc-deploy -C disc-deploy -N ""
sudo mkdir -p /home/disc/.ssh && sudo chown disc:disc /home/disc/.ssh
printf 'command="/usr/local/bin/rrsync -wo /srv/disc",from="<IP владельца>",no-port-forwarding,no-agent-forwarding,no-X11-forwarding %s\n' \
  "$(cat ~/.disc-keys/disc-deploy.pub)" \
  | sudo tee /home/disc/.ssh/authorized_keys >/dev/null
sudo chown disc:disc /home/disc/.ssh/authorized_keys && sudo chmod 600 /home/disc/.ssh/authorized_keys
```

- `rrsync -wo` — канал только заливка: без shell, без чтения
  (включая собственные файлы — они есть у команды локально).
- `from=` — ключ работает только с адресов владельца (второй эшелон:
  sshd/firewall — по решению владельца; WireGuard-вариант описан в
  обсуждении, здесь по умолчанию не требуется).

## 6. Проверка конца-в-конец (после провижининга)

```bash
# с машины владельца:
rsync -e "ssh -i ~/.disc-keys/disc-deploy" -r --delete \
  <тестовый каталог>/ disc@aserv:/srv/disc/disc-v-selfcheck/
curl -fsS https://task.ai-aid.pro/disc-v-selfcheck/ | head   # 200 + вывод index.php
ssh -i ~/.disc-keys/disc-deploy disc@aserv 'ls /'            # ДОЛЖЕН быть отказ (rrsync)
# затем убрать тестовую версию:
rsync -e "ssh -i ~/.disc-keys/disc-deploy" -r --delete --del empty/ disc@aserv:/srv/disc/disc-v-selfcheck/
```

## Переменные для раннера (после провижининга)

| env | значение |
|---|---|
| `DISC_DEPLOY_HOST` | `aserv` (ssh-алиас с машины владельца) |
| `DISC_DEPLOY_USER` | `disc` |
| `DISC_DEPLOY_ROOT` | `/srv/disc` |
| `DISC_DEPLOY_KEY_FILE` | путь к `~/.disc-keys/disc-deploy` (файл вне репо) |

Ключ раннером загружается в `ssh-agent`, в песочницу идёт только сокет —
агент пользуется ключом, но прочитать его не может.
