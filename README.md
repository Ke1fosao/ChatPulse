# ChatPulse

ChatPulse — Telegram-бот для статистики активності в групах. Він автоматично реєструє учасників, рахує повідомлення, медіа та відповіді й показує рейтинг найактивніших людей.

Бот **не зберігає текст повідомлень, підписи або файли** — тільки числові лічильники та базові Telegram-дані профілю.

## Що вже реалізовано

- реєстрація користувача через `/start`;
- кнопка додавання бота до групи;
- автоматична реєстрація групи;
- активація статистики після надання прав адміністратора;
- автоматична реєстрація учасника після першого повідомлення;
- підрахунок повідомлень, медіа та відповідей;
- загальна статистика групи;
- рейтинг учасників;
- особиста статистика;
- захищений Telegram webhook;
- запуск у Google Cloud Run;
- SQLite для локальної розробки та PostgreSQL для production.

## Команди

| Команда | Дія |
|---|---|
| `/start` | Реєстрація та кнопка додавання бота до групи |
| `/help` | Коротка інструкція |
| `/stats` | Загальна статистика групи |
| `/top` | Топ-10 учасників |
| `/me` | Особиста статистика користувача |

## Як працює реєстрація

1. Користувач пише боту `/start` в особистому чаті.
2. ChatPulse зберігає Telegram ID, ім'я, username і мову профілю.
3. Користувач додає бота до групи.
4. ChatPulse реєструє групу, але не рахує активність, поки не стане адміністратором.
5. Після надання прав адміністратора група стає активною.
6. Коли учасник уперше пише звичайне повідомлення, створюється його статистичний профіль у цій групі.

Команди, повідомлення інших ботів і службові оновлення до рейтингу не потрапляють.

## Стек

- Python 3.12+
- aiogram 3
- FastAPI
- SQLAlchemy 2 async
- SQLite / PostgreSQL
- pytest
- Ruff
- Docker
- Google Cloud Run

## Локальний запуск

### 1. Створіть Telegram-бота

Відкрийте `@BotFather`, виконайте `/newbot` і скопіюйте токен.

### 2. Підготуйте середовище

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

Для Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
copy .env.example .env
```

### 3. Заповніть `.env`

```env
BOT_TOKEN=123456:your-real-token
WEBHOOK_BASE_URL=https://your-public-domain.example
WEBHOOK_PATH_SECRET=long-random-path-secret
WEBHOOK_HEADER_SECRET=long-random-header-secret
DATABASE_URL=sqlite+aiosqlite:///./chatpulse.db
DEFAULT_TIMEZONE=Europe/Kyiv
```

Для локальної перевірки health endpoint можна не задавати `WEBHOOK_BASE_URL`.

### 4. Запустіть сервер

```bash
uvicorn app.main:create_app --factory --reload --port 8080
```

Перевірка:

```text
http://127.0.0.1:8080/health
```

Щоб Telegram надсилав webhook локально, потрібен публічний HTTPS-тунель, наприклад Cloudflare Tunnel або ngrok. У `WEBHOOK_BASE_URL` вкажіть отриману HTTPS-адресу та перезапустіть застосунок.

## База даних

Локально можна використовувати SQLite:

```env
DATABASE_URL=sqlite+aiosqlite:///./chatpulse.db
```

Для Google Cloud Run використовуйте зовнішню PostgreSQL-базу, наприклад Supabase, Neon або Cloud SQL:

```env
DATABASE_URL=postgresql://user:password@host:5432/database
```

ChatPulse автоматично перетворює `postgresql://` на async-драйвер `postgresql+asyncpg://`.

> Локальний SQLite-файл у Cloud Run не підходить для постійних даних: файлове сховище контейнера тимчасове й може зникнути після нового деплою або масштабування.

## Деплой у Google Cloud Run через GitHub

### Перший деплой

1. Створіть проєкт у Google Cloud і підключіть billing account.
2. Відкрийте **Cloud Run** → **Create service**.
3. Оберіть **Continuously deploy from a repository**.
4. Підключіть GitHub і виберіть репозиторій `Ke1fosao/ChatPulse`.
5. Виберіть гілку `main` і збірку через наявний `Dockerfile`.
6. Виберіть регіон, наприклад `europe-central2` (Warsaw).
7. Увімкніть **Allow unauthenticated invocations**, щоб Telegram міг викликати webhook.
8. Для економії встановіть minimum instances `0`.
9. Додайте environment variables, крім `WEBHOOK_BASE_URL`.
10. Виконайте перший деплой і скопіюйте URL сервісу виду `https://chatpulse-....run.app`.

### Активація webhook

Додайте або оновіть змінну:

```env
WEBHOOK_BASE_URL=https://chatpulse-....run.app
```

Після нового деплою ChatPulse сам викличе Telegram `setWebhook` із секретним заголовком.

### Необхідні змінні Cloud Run

| Змінна | Призначення |
|---|---|
| `BOT_TOKEN` | Токен від BotFather |
| `WEBHOOK_BASE_URL` | Публічний URL Cloud Run без `/` у кінці |
| `WEBHOOK_PATH_SECRET` | Випадкова частина URL webhook, мінімум 8 символів |
| `WEBHOOK_HEADER_SECRET` | Секрет Telegram-заголовка, мінімум 8 символів |
| `DATABASE_URL` | PostgreSQL connection string |
| `DEFAULT_TIMEZONE` | Початковий часовий пояс груп, наприклад `Europe/Kyiv` |

Токени та паролі не додавайте до GitHub. Зберігайте їх у Cloud Run Environment Variables або Google Secret Manager.

## Перевірки

```bash
pytest -q
ruff check .
python -m compileall app
```

## Структура

```text
app/
├── bot/
│   ├── routers/
│   │   ├── private.py
│   │   └── groups.py
│   ├── keyboards.py
│   └── setup.py
├── repositories/
│   └── activity.py
├── services/
│   └── stats.py
├── config.py
├── database.py
├── domain.py
├── main.py
└── models.py
```

## Наступні етапи

- статистика за день і тиждень;
- реакції;
- автоматичні щотижневі звіти;
- налаштування часового поясу;
- пауза збору статистики;
- цікаві нагороди на кшталт «нічний житель» або «король реакцій»;
- Mini App із графіками.
