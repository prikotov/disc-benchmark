# Инструкция деплоя (для полного прогона)

Требуется полные учётные данные (DISC_DEPLOY_HOST / USER / KEY_FILE / DEPLOY_ROOT, DISC_SMTP_DSN, DISC_TEST_MAILBOX).

1. Сборка: `cd /work/disc && composer install --no-dev --optimize-autoloader`
2. На сервере: путь `/disc-v-<имя версии>/` под `DISC_DEPLOY_ROOT`.
3. Скопировать код (rsync/scp через SSH с `DISC_DEPLOY_KEY_FILE`).
4. `.env` / окружение: `APP_ENV=prod`, `APP_SECRET`, `DISC_SMTP_DSN`, `DISC_LLM_BASE_URL`, `DISC_LLM_MODEL`, `DISC_LLM_KEY_FILE` (если требуется).
5. Права: папка `var/` и `.env` недоступны HTTP.
6. Веб-сервер: `public/index.php` в качестве точки входа, rewrite / → public/index.php.
7. Проверка по адресу `https://ai-aid.pro/disc-v-<имя версии>/`: старт, 8 шагов, подсчёт, интерпретация (LLM), отправка письма на контрольный ящик DISC_TEST_MAILBOX.
8. Не трогать остальные пути сайта.
