# ChatPulse

ChatPulse — Telegram-бот для аналітики активності груп. Він рахує повідомлення, медіа, відповіді та реакції, показує рейтинги за різні періоди, формує веселі номінації й може автоматично надсилати щотижневий звіт.

Бот **не зберігає тексти повідомлень, підписи або файли**. У базі залишаються лише Telegram ID, базові дані профілю, ID повідомлення для прив’язки реакцій і числові лічильники.

## Можливості

- статистика за сьогодні, 7 днів, місяць і весь час;
- топ учасників та особиста статистика;
- підрахунок повідомлень, медіа, відповідей і реакцій;
- окремий підрахунок фото, голосових, нічної та ранкової активності;
- щотижневі номінації: «Балакун тижня», «Нічний житель», «Фотограф групи», «Улюбленець групи» та інші;
- автоматичні щотижневі звіти;
- адмінські налаштування групи;
- пауза збору статистики та безпечне скидання;
- захист від повторної обробки одного Telegram update;
- FastAPI webhook, PostgreSQL/Supabase та Google Cloud Run.

## Команди

| Команда | Дія |
|---|---|
| `/start` | Реєстрація та кнопка додавання бота до групи |
| `/help` | Коротка інструкція |
| `/stats` | Статистика з кнопками вибору періоду |
| `/today` | Статистика за сьогодні |
| `/week` | Статистика за останні 7 днів |
| `/month` | Статистика за поточний місяць |
| `/all` | Статистика за весь час |
| `/top` | Рейтинг учасників із вибором періоду |
| `/me` | Особиста статистика з вибором періоду |
| `/weekly` | Попередній перегляд щотижневого звіту |
| `/settings` | Налаштування групи для адміністратора |
| `/resetstats` | Підтверджене скидання статистики |

## Налаштування адміністратора

У `/settings` можна:

- призупинити або відновити збір;
- увімкнути чи вимкнути щотижневі звіти;
- вибрати `Europe/Kyiv`, `Europe/Warsaw` або `Europe/Berlin`;
- змінити день і годину звіту;
- окремо вимкнути повідомлення, медіа, відповіді чи реакції;
- скинути накопичену статистику.

Кожна зміна повторно перевіряє, що користувач є адміністратором або власником групи.

## Як підключити до групи

1. Відкрийте бота в особистому чаті й натисніть `/start`.
2. Натисніть кнопку **«Додати ChatPulse до групи»**.
3. Призначте бота адміністратором.
4. У `@BotFather` відкрийте **Bot Settings → Group Privacy** і вимкніть Privacy Mode.
5. Напишіть звичайне повідомлення — група активується автоматично.
6. Перевірте `/stats` і `/top`.

Для отримання `message_reaction` та `message_reaction_count` Telegram має бачити бота як адміністратора групи.

## Технології

- Python 3.12+
- aiogram 3
- FastAPI
- SQLAlchemy 2 async
- PostgreSQL / Supabase
- SQLite для локальних тестів
- pytest і Ruff
- Docker
- Google Cloud Run

## Локальний запуск

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
uvicorn app.main:create_app --factory --reload --port 8080
```

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
copy .env.example .env
uvicorn app.main:create_app --factory --reload --port 8080
```

`.env`:

```env
BOT_TOKEN=123456:your-real-token
WEBHOOK_BASE_URL=https://your-service.run.app
WEBHOOK_PATH_SECRET=long-random-path-secret
WEBHOOK_HEADER_SECRET=long-random-header-secret
SCHEDULER_SECRET=long-random-scheduler-secret
DATABASE_URL=postgresql://user:password@pooler-host:5432/postgres
DEFAULT_TIMEZONE=Europe/Kyiv
```

Паролі зі спеціальними символами в `DATABASE_URL` потрібно percent-encode. Токени, паролі та секрети не комітьте в GitHub.

## Supabase

Production-проєкт ChatPulse використовує PostgreSQL у Supabase. Схема містить:

- `users`;
- `chat_groups`;
- `group_members`;
- `daily_activity`;
- `message_authors`;
- `message_reaction_state`;
- `daily_reaction_emoji`;
- `processed_updates`.

Для Cloud Run використовуйте **Session pooler** на порту `5432`.

## Google Cloud Run

Рекомендовані параметри:

- region: `europe-central2`;
- minimum instances: `0`;
- maximum instances: `2–3`;
- memory: `512 MiB`;
- public access: увімкнений;
- база: зовнішній PostgreSQL, не локальний SQLite.

Необхідні variables:

| Змінна | Призначення |
|---|---|
| `BOT_TOKEN` | Токен BotFather |
| `WEBHOOK_BASE_URL` | URL Cloud Run без `/` у кінці |
| `WEBHOOK_PATH_SECRET` | Випадкова частина webhook URL |
| `WEBHOOK_HEADER_SECRET` | Секрет заголовка Telegram webhook |
| `SCHEDULER_SECRET` | Захист внутрішнього endpoint звітів |
| `DATABASE_URL` | Supabase Session pooler connection string |
| `DEFAULT_TIMEZONE` | Початковий часовий пояс |

Після кожного push у `main` Cloud Build збирає Docker image і розгортає нову revision.

## Автоматичні щотижневі звіти

ChatPulse має захищений endpoint:

```text
POST /internal/weekly-reports
X-ChatPulse-Scheduler-Secret: <SCHEDULER_SECRET>
```

У Google Cloud Scheduler створіть HTTP job, який запускається раз на годину:

```text
URL: https://your-service.run.app/internal/weekly-reports
Method: POST
Header: X-ChatPulse-Scheduler-Secret=<SCHEDULER_SECRET>
Schedule: 0 * * * *
Timezone: Etc/UTC
```

Endpoint сам перевіряє локальний часовий пояс, день і годину кожної групи, тому один погодинний job обслуговує всі групи. Повторний звіт у той самий локальний день не надсилається.

## Перевірки

```bash
pytest -q
ruff check .
ruff format --check .
python -m compileall app
```

## Структура

```text
app/
├── bot/
│   ├── routers/
│   │   ├── private.py
│   │   ├── groups.py
│   │   ├── reactions.py
│   │   └── settings.py
│   ├── keyboards.py
│   ├── keyboards_stats.py
│   ├── keyboards_settings.py
│   └── setup.py
├── repositories/
│   └── activity.py
├── services/
│   ├── stats.py
│   ├── nominations.py
│   └── weekly_reports.py
├── config.py
├── database.py
├── domain.py
├── main.py
└── models.py
```
