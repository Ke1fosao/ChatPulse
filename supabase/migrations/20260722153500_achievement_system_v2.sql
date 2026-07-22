-- ChatPulse Achievement System 2.0
-- Durable unlocks, celebration delivery, future progress, and profile pins.

create table if not exists public.achievement_unlocks (
    id bigserial primary key,
    telegram_user_id bigint not null references public.users(telegram_id) on delete cascade,
    telegram_chat_id bigint null references public.chat_groups(telegram_chat_id) on delete cascade,
    scope varchar(16) not null,
    scope_key varchar(64) not null,
    achievement_code varchar(64) not null,
    rarity varchar(16) not null,
    final_progress integer not null default 0,
    definition_version integer not null default 2,
    earned_at timestamptz not null default now(),
    constraint ck_achievement_unlock_scope check (scope in ('group', 'global')),
    constraint uq_achievement_unlock_identity unique (
        telegram_user_id,
        scope_key,
        achievement_code
    )
);

create index if not exists ix_achievement_unlock_user_earned
    on public.achievement_unlocks (telegram_user_id, earned_at);

create index if not exists ix_achievement_unlock_group_earned
    on public.achievement_unlocks (telegram_chat_id, earned_at);

create table if not exists public.achievement_events (
    id bigserial primary key,
    telegram_user_id bigint not null references public.users(telegram_id) on delete cascade,
    achievement_unlock_id bigint null unique references public.achievement_unlocks(id) on delete cascade,
    event_type varchar(32) not null default 'unlock',
    payload_json text not null default '{}',
    created_at timestamptz not null default now(),
    delivered_at timestamptz null,
    seen_at timestamptz null,
    shared_at timestamptz null,
    constraint ck_achievement_event_type check (
        event_type in ('unlock', 'collection_update')
    )
);

create index if not exists ix_achievement_events_pending
    on public.achievement_events (telegram_user_id, seen_at, created_at);

create index if not exists ix_achievement_events_unlock
    on public.achievement_events (achievement_unlock_id);

create table if not exists public.achievement_progress (
    telegram_user_id bigint not null references public.users(telegram_id) on delete cascade,
    scope_key varchar(64) not null,
    achievement_code varchar(64) not null,
    telegram_chat_id bigint null references public.chat_groups(telegram_chat_id) on delete cascade,
    progress integer not null default 0,
    updated_at timestamptz not null default now(),
    primary key (telegram_user_id, scope_key, achievement_code),
    constraint ck_achievement_progress_non_negative check (progress >= 0)
);

create index if not exists ix_achievement_progress_user
    on public.achievement_progress (telegram_user_id, updated_at);

create table if not exists public.featured_achievements (
    telegram_user_id bigint not null references public.users(telegram_id) on delete cascade,
    slot integer not null,
    scope_key varchar(64) not null,
    achievement_code varchar(64) not null,
    created_at timestamptz not null default now(),
    primary key (telegram_user_id, slot),
    constraint ck_featured_achievement_slot check (slot between 1 and 3),
    constraint uq_featured_achievement_identity unique (
        telegram_user_id,
        scope_key,
        achievement_code
    )
);

alter table public.achievement_unlocks enable row level security;
alter table public.achievement_events enable row level security;
alter table public.achievement_progress enable row level security;
alter table public.featured_achievements enable row level security;

revoke all on table public.achievement_unlocks from anon, authenticated;
revoke all on table public.achievement_events from anon, authenticated;
revoke all on table public.achievement_progress from anon, authenticated;
revoke all on table public.featured_achievements from anon, authenticated;
revoke all on sequence public.achievement_unlocks_id_seq from anon, authenticated;
revoke all on sequence public.achievement_events_id_seq from anon, authenticated;
