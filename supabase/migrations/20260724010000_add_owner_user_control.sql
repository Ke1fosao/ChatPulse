create table if not exists public.admin_staff (
    telegram_user_id bigint primary key references public.users(telegram_id) on delete cascade,
    role varchar(32) not null,
    is_active boolean not null default true,
    granted_by_owner_id bigint not null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint ck_admin_staff_role check (role in ('admin', 'moderator', 'support'))
);
create index if not exists ix_admin_staff_role_active
    on public.admin_staff (role, is_active);

create table if not exists public.user_restrictions (
    telegram_user_id bigint primary key references public.users(telegram_id) on delete cascade,
    is_blocked boolean not null default false,
    reason varchar(500) null,
    blocked_by_actor_id bigint null,
    blocked_at timestamptz null,
    unblocked_by_actor_id bigint null,
    unblocked_at timestamptz null,
    unblock_reason varchar(500) null,
    updated_at timestamptz not null default now()
);
create index if not exists ix_user_restrictions_blocked
    on public.user_restrictions (is_blocked, updated_at desc);

create table if not exists public.user_admin_notes (
    telegram_user_id bigint primary key references public.users(telegram_id) on delete cascade,
    note text not null,
    updated_by_actor_id bigint not null,
    updated_at timestamptz not null default now()
);

create table if not exists public.user_admin_tags (
    telegram_user_id bigint not null references public.users(telegram_id) on delete cascade,
    tag varchar(32) not null,
    created_by_actor_id bigint not null,
    created_at timestamptz not null default now(),
    primary key (telegram_user_id, tag),
    constraint ck_user_admin_tags_length check (char_length(tag) between 1 and 32)
);
create index if not exists ix_user_admin_tags_tag on public.user_admin_tags (tag);

create table if not exists public.user_xp_adjustments (
    id bigserial primary key,
    telegram_user_id bigint not null references public.users(telegram_id) on delete cascade,
    telegram_chat_id bigint null references public.chat_groups(telegram_chat_id) on delete cascade,
    amount integer not null,
    previous_total integer not null,
    resulting_total integer not null,
    reason varchar(500) not null,
    actor_telegram_user_id bigint not null,
    created_at timestamptz not null default now(),
    constraint ck_user_xp_adjustments_nonzero check (amount <> 0)
);
create index if not exists ix_user_xp_adjustments_user_created
    on public.user_xp_adjustments (telegram_user_id, created_at desc);

create table if not exists public.admin_message_deliveries (
    id bigserial primary key,
    telegram_user_id bigint not null references public.users(telegram_id) on delete cascade,
    actor_telegram_user_id bigint not null,
    message_text text not null,
    status varchar(16) not null default 'pending',
    safe_error varchar(500) null,
    created_at timestamptz not null default now(),
    sent_at timestamptz null,
    constraint ck_admin_message_deliveries_status check (status in ('pending', 'sent', 'failed'))
);
create index if not exists ix_admin_message_deliveries_user_created
    on public.admin_message_deliveries (telegram_user_id, created_at desc);

create table if not exists public.blocked_access_events (
    id bigserial primary key,
    telegram_user_id bigint not null references public.users(telegram_id) on delete cascade,
    source varchar(32) not null,
    window_key varchar(32) not null,
    attempt_count integer not null default 1,
    first_attempt_at timestamptz not null default now(),
    last_attempt_at timestamptz not null default now(),
    constraint ck_blocked_access_events_source check (source in ('miniapp', 'bot_private', 'bot_group')),
    constraint uq_blocked_access_events_window unique (telegram_user_id, source, window_key)
);
create index if not exists ix_blocked_access_events_user_last
    on public.blocked_access_events (telegram_user_id, last_attempt_at desc);

alter table public.admin_staff enable row level security;
alter table public.user_restrictions enable row level security;
alter table public.user_admin_notes enable row level security;
alter table public.user_admin_tags enable row level security;
alter table public.user_xp_adjustments enable row level security;
alter table public.admin_message_deliveries enable row level security;
alter table public.blocked_access_events enable row level security;

revoke all on table public.admin_staff from anon, authenticated;
revoke all on table public.user_restrictions from anon, authenticated;
revoke all on table public.user_admin_notes from anon, authenticated;
revoke all on table public.user_admin_tags from anon, authenticated;
revoke all on table public.user_xp_adjustments from anon, authenticated;
revoke all on table public.admin_message_deliveries from anon, authenticated;
revoke all on table public.blocked_access_events from anon, authenticated;
revoke all on sequence public.user_xp_adjustments_id_seq from anon, authenticated;
revoke all on sequence public.admin_message_deliveries_id_seq from anon, authenticated;
revoke all on sequence public.blocked_access_events_id_seq from anon, authenticated;
