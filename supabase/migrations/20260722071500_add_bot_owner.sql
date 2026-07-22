create table if not exists public.bot_owner (
    owner_key varchar(16) primary key,
    telegram_user_id bigint not null unique,
    claimed_username varchar(64) not null,
    claimed_at timestamptz not null default now(),
    constraint ck_bot_owner_singleton check (owner_key = 'primary')
);

alter table public.bot_owner enable row level security;

revoke all on table public.bot_owner from anon;
revoke all on table public.bot_owner from authenticated;
