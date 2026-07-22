# ChatPulse Owner Panel + VIP Design

## Goal

Додати до існуючого Telegram Mini App окрему owner-систему за маршрутом `/miniapp/owner`, доступну лише єдиному власнику ChatPulse, а також захищену роль VIP-клієнта, яку може видати або відкликати тільки власник.

## Security boundary

- Власник визначається тільки через перевірений Telegram `initData` і незмінний Telegram user ID у singleton-таблиці `bot_owner`.
- Username не використовується для авторизації після одноразового `/claimadmin`.
- Owner API має окремий префікс `/api/owner/v1`.
- Кожен owner endpoint повторно виконує HMAC-перевірку `initData` та `OwnerRepository.is_owner()`.
- Клієнт не передає `owner_id`, роль або список прав; ці значення визначає сервер.
- VIP не має доступу до owner API, не може видавати VIP і не отримує групові адміністративні права.
- Для видачі та відкликання VIP потрібне явне підтвердження у payload.
- Усі зміни ролей і керувальні дії записуються в append-only audit log.
- Власника не можна змінити, видалити, заблокувати або перетворити на VIP через панель.

## Data model

### `vip_grants`

Один активний стан VIP на користувача:

- `telegram_user_id` — primary key і FK до `users.telegram_id`;
- `is_active`;
- `starts_at`;
- `expires_at` nullable для безстрокового VIP;
- `granted_by_owner_id`;
- `grant_reason`;
- `revoked_at`, `revoked_by_owner_id`, `revoke_reason`;
- `created_at`, `updated_at`.

VIP вважається активним, коли `is_active = true`, `starts_at <= now` і `expires_at` відсутня або знаходиться в майбутньому.

### `owner_audit_log`

- surrogate `id`;
- `owner_telegram_user_id`;
- `action`;
- `target_type` і `target_id`;
- `metadata_json` без секретів і текстів повідомлень;
- `created_at`.

## Central entitlement model

Сервіс `app/services/entitlements.py` повертає:

- `plan`: `free`, `vip` або `owner`;
- `is_owner`, `is_vip`;
- `vip_expires_at`;
- повний набір premium entitlement keys.

Owner та активний VIP мають усі premium entitlement keys. Майбутні платні можливості повинні перевіряти цей сервіс, а не напряму читати таблицю VIP.

## Owner API

- `GET /api/owner/v1/session` — owner profile і підтвердження доступу.
- `GET /api/owner/v1/overview` — користувачі, групи, активні групи, VIP, активність за 7 днів.
- `GET /api/owner/v1/users` — пошук, фільтр за VIP, пагінація.
- `GET /api/owner/v1/users/{telegram_user_id}` — деталі користувача та його групи.
- `POST /api/owner/v1/users/{telegram_user_id}/vip` — видати безстроковий або строковий VIP.
- `DELETE /api/owner/v1/users/{telegram_user_id}/vip` — відкликати VIP.
- `GET /api/owner/v1/groups` — пошук і системний стан груп.
- `PATCH /api/owner/v1/groups/{chat_id}` — owner-level пауза, активація звітів і тема картки.
- `GET /api/owner/v1/audit` — останні owner-дії.

## Mini App routing

Той самий Vite bundle обслуговує:

- `/miniapp` — звичайний ChatPulse;
- `/miniapp/owner` — окремий `OwnerApp`.

`main.tsx` обирає root component за `window.location.pathname`. Owner UI не покладається на прихованість маршруту: при 401/403 показується закритий екран, а всі дані й мутації захищені сервером.

## Owner UI

- власний top bar `Owner Control`;
- overview cards;
- вкладки `Огляд`, `Користувачі`, `Групи`, `Аудит`;
- пошук користувачів;
- VIP badge, дата завершення, форма причини й строку;
- підтвердження перед видачею/відкликанням;
- керування паузою групи та звітами;
- повернення до звичайного Mini App.

## Privacy

Owner Panel не показує і не зберігає тексти повідомлень, captions або файли. Показуються тільки агреговані лічильники, Telegram profile fields, групове membership-метадані та системні події керування.
