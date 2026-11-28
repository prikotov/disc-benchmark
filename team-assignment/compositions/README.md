# Составы команд

`compositions/<слаг>.json` — определения составов (роль → модель → уровень
мышления + условие A/B). Правила:

- **слаг** = имя файла; смена модели в роли = новый состав = новый файл
  (`team-alpha`, `team-beta`, …);
- поля: `slug`, `condition` (`A` — DISC-карточки `roles/`, `B` — нейтральные
  `roles-neutral/`), `roles_dir`, `roles` (7 ролей), `rules`;
- `status`: `proposal` → `approved` (утверждает владелец); запускать можно
  только `approved`;
- одна модель может занимать несколько ролей; разнообразие составов —
  предмет отдельных серий;
- `{{model}}` карточек ролей подставляется из `roles` этой композиции.

Для A/B-сравнения: состав B повторяет состав A той же связкой
роль → модель → уровень, отличаясь только `condition`/`roles_dir`.

## team-alpha.json (предложение, волна 1)

Текущее предложение (status: proposal): тимлид и tester — huihui-ai:pi-100k
(low); architect и devops — qwen3.8:27b-pi-100k (low); frontend —
muse-glimmer:ctx100k (low); backend — orcarouter/Qwen3.8-27B-Uncensored:ctx100k
(think); reviewer — ornith-1.5:35b-ctx100k (think).
