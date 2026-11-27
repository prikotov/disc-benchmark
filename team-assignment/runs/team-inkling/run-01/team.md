# Команда прогона: team-inkling (условие A)

Композиция: `compositions/team-inkling.json` @ `efbdf92cda66`
Методология: `5bca3afd29a4` · Промпт: v1 · Карточки ролей: `roles/`

| Роль | Белбин | DISC-профиль | Модель | Уровень (факт) |
|---|---|---|---|---|
| teamlead | Координатор | D высокий, I средний | `inkling-2-mini:pi-128k` | low |
| architect | Мыслитель/Plant | C высокий, D средний | `inkling-2-mini:pi-128k` | default модели |
| frontend | Исследователь ресурсов | I высокий, D средний | `inkling-2-mini:pi-128k` | default модели |
| backend | Реализатор | S высокий, C средний | `inkling-2-mini:pi-128k` | default модели |
| reviewer | Оценщик/Monitor Evaluator | C высокий, I низкий | `inkling-2-mini:pi-128k` | default модели |
| devops | Мотиватор/Shaper | D высокий, C средний | `inkling-2-mini:pi-128k` | default модели |
| tester | Доводчик/Completer Finisher | C высокий, S средний | `inkling-2-mini:pi-128k` | default модели |

- Сабагенты не наследуют уровень тимлида (механика subagent: карточки
  с `model:` идут без `--thinking`) — уровень «default модели».
- Карточки моделей: `models/<модель>/model.md`, раздел «disc».
