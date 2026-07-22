# ChatPulse

ChatPulse — Telegram-бот і преміальний Mini App для аналітики та гейміфікації груп. Він рахує активність, порівнює періоди, видає XP, рівні й досягнення, підтримує серії активності та автоматично створює красиві картки для поширення.

## Mini App

Mini App відкривається з приватного чату через кнопку **«Відкрити ChatPulse»**, команду `/open` або Telegram Menu Button.

Основні екрани:

- **Головна** — глобальний рівень, XP, місце, streak, захисні дні, графік і найактивніші групи;
- **Групи** — пошук, сортування та картки всіх доступних користувачу чатів;
- **Панель групи** — статистика за 7/30 днів або весь час, порівняння, графік, теплова карта, топ, номінації та повідомлення періоду;
- **Рейтинг** — XP, повідомлення, реакції, відповіді або streak;
- **Досягнення** — отримані й заблоковані нагороди, категорії, рідкість і прогрес;
- **Профіль** — глобальний результат, рекорди та shareable PNG-картка;
- **Адмінська панель** — точний час звіту, день, timezone, тема картки, типи статистики, пауза та безпечне скидання.

Frontend написаний на React + TypeScript + Vite й роздається тим самим FastAPI/Cloud Run сервісом за адресою `/miniapp`. API використовує префікс `/api/miniapp/v1`.

## Приватність і безпека

ChatPulse **не зберігає тексти повідомлень, підписи або файли**. У базі залишаються Telegram ID, ID повідомлення, автор, часові мітки, числові лічильники та кількість реакцій.

Для антиспаму зберігаються лише keyed fingerprints: точний відбиток і 64-бітний similarity fingerprint. Вони створюються із секретним ключем сервера, тому початковий текст у базу не записується.

Mini App:

- перевіряє Telegram `initData` через HMAC на кожному API-запиті;
- приймає особу користувача лише з перевіреного `initData`;
- відхиляє сесії старші за 15 хвилин;
- не показує групи без membership-запису;
- у production додатково перевіряє актуальне членство через `getChatMember`;
- перед кожною адмінською зміною повторно перевіряє роль `administrator` або `creator`;
- повертає `404` для недоступних груп, не розкриваючи їх існування.

## Можливості бота

- статистика за сьогодні, 7 днів, місяць і весь час;
- порівняння поточних і попередніх 7 днів;
- топ учасників та особисті профілі;
- повідомлення тижня з кнопкою переходу;
- груповий і глобальний рівні ChatPulse;
- досягнення з комбінованими сповіщеннями;
- streak із трьома захисними днями на календарний місяць;
- автоматичні PNG-картки в трьох темах;
- точний час звіту у форматі `HH:MM`;
- FastAPI webhook, PostgreSQL/Supabase та Google Cloud Run.

## Команди

### Приватний чат

| Команда | Дія |
|---|---|
| `/start` | Реєстрація, Mini App і кнопка додавання в групу |
| `/open` | Відкрити ChatPulse Mini App |
| `/profile` | Короткий глобальний XP-профіль |
| `/groups` | Список груп користувача |
| `/achievements` | Останні отримані нагороди |
| `/help` | Коротка інструкція |

### Груповий чат

| Команда | Дія |
|---|---|
| `/stats` | Статистика з кнопками вибору періоду |
| `/today`, `/week`, `/month`, `/all` | Швидкий вибір періоду |
| `/top` | Рейтинг учасників |
| `/me` | Базова особиста статистика |
| `/profile` | XP, рівні, streak і досягнення |
| `/compare` | Два останні 7-денні періоди |
| `/weekly` | PNG-картка тижневого звіту |
| `/settings` | Налаштування для адміністратора |
| `/setreporttime 20:30` | Точний локальний час звіту |
| `/resetstats` | Підтверджене скидання статистики |

## XP та антиспам

Базові нагороди:

- повноцінне текстове повідомлення: `+1 XP`;
- відповідь: `+2 XP`;
- фото або голосове/video note: `+2 XP`;
- отримана реакція: `+3 XP`.

Захист від накрутки:

- XP не частіше ніж раз на 5 секунд;
- повідомлення з 1–2 символів, emoji-only та стікери не дають XP;
- точні та майже однакові повідомлення блокуються;
- після 20 повідомлень за 10 хвилин XP зменшується;
- після 40 повідомлень за 10 хвилин повідомлення тимчасово не дають XP;
- максимум `200 XP` на день у кожній групі;
- максимум `400 XP` на день у глобальний профіль.

Звичайні лічильники працюють і після XP-ліміту. Рівень `L` починається на сумарному XP `50 × (L - 1) × L`. Тири: Новачок, Бронза, Срібло, Золото, Діамант.

День зараховується у streak після щонайменше `10 XP`. Щомісяця доступні три автоматичні захисні дні, які не переносяться далі.

## Локальний запуск

### Backend

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

### Mini App frontend

```bash
cd miniapp
npm install
npm run dev
```

Vite працює на `http://localhost:5173` і проксіює `/api` на `http://localhost:8080`.

У production Mini App без справжнього Telegram `initData` показує екран «Відкрийте через Telegram». Development і test режими дозволяють відкрити UI для локальної верстки, але backend API все одно потребує валідної авторизації, якщо dependency не перевизначена тестом.

## Змінні середовища

```env
BOT_TOKEN=123456:your-real-token
WEBHOOK_BASE_URL=https://your-service.run.app
WEBHOOK_PATH_SECRET=long-random-path-secret
WEBHOOK_HEADER_SECRET=long-random-header-secret
SCHEDULER_SECRET=long-random-scheduler-secret
DATABASE_URL=postgresql://user:password@pooler-host:5432/postgres
DEFAULT_TIMEZONE=Europe/Kyiv
```

`WEBHOOK_BASE_URL` одночасно визначає:

- webhook URL бота;
- адресу Mini App: `${WEBHOOK_BASE_URL}/miniapp`;
- Telegram Menu Button.

Секрети, токени й production-паролі не комітьте в GitHub.

## BotFather після deployment

1. Відкрийте `@BotFather`.
2. Оберіть бот → **Bot Settings → Menu Button**.
3. Встановіть URL `https://your-service.run.app/miniapp`.
4. За потреби відкрийте **Web Apps → Edit Web App URL** і вкажіть той самий URL.
5. Для групової аналітики вимкніть **Group Privacy** та призначте бота адміністратором.

ChatPulse також автоматично викликає `setChatMenuButton` під час запуску production revision, якщо налаштований `WEBHOOK_BASE_URL`.

## Docker і Cloud Run

Dockerfile має два етапи:

1. Node 22 збирає `miniapp/dist`;
2. Python 3.12 встановлює backend, шрифти DejaVu й копіює frontend у `/app/miniapp_dist`.

```bash
docker build -t chatpulse .
docker run --env-file .env -p 8080:8080 chatpulse
```

Після push у `main` production pipeline збирає один образ і розгортає бота, API та Mini App разом.

## Автоматичні щотижневі звіти

Захищений endpoint:

```text
POST /internal/weekly-reports
X-ChatPulse-Scheduler-Secret: <SCHEDULER_SECRET>
```

Cloud Scheduler перевіряє точний локальний час кожні 5 хвилин:

```text
URL: https://your-service.run.app/internal/weekly-reports
Method: POST
Schedule: */5 * * * *
Timezone: Etc/UTC
```

```bash
gcloud scheduler jobs update http chatpulse-weekly-reports \
  --location=europe-central2 \
  --schedule="*/5 * * * *" \
  --time-zone="Etc/UTC"
```

## Перевірки

```bash
cd miniapp
npm install
npm test -- --run
npm run typecheck
npm run build

cd ..
ruff check .
ruff format --check .
pytest -q
python -m compileall app
```

GitHub Actions виконує frontend і backend перевірки паралельно.
