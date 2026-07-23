create table if not exists public.user_group_preferences (
    telegram_user_id bigint not null references public.users(telegram_id) on delete cascade,
    telegram_chat_id bigint not null references public.chat_groups(telegram_chat_id) on delete cascade,
    is_favorite boolean not null default false,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    primary key (telegram_user_id, telegram_chat_id)
);

create index if not exists ix_user_group_preferences_chat
    on public.user_group_preferences (telegram_chat_id);
create index if not exists ix_user_group_preferences_favorite
    on public.user_group_preferences (telegram_user_id, is_favorite);

alter table public.user_group_preferences enable row level security;

comment on table public.user_group_preferences is
    'Private per-user ordering preferences for Groups 2.0. Service role only.';
