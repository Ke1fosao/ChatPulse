create table if not exists public.vip_grants (
    telegram_user_id bigint primary key references public.users(telegram_id) on delete cascade,
    is_active boolean not null default true,
    starts_at timestamptz not null default now(),
    expires_at timestamptz null,
    granted_by_owner_id bigint not null,
    grant_reason varchar(300) not null,
    revoked_at timestamptz null,
    revoked_by_owner_id bigint null,
    revoke_reason varchar(300) null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint ck_vip_grants_valid_expiry check (expires_at is null or expires_at > starts_at)
);

create index if not exists ix_vip_grants_active_expiry
    on public.vip_grants (is_active, expires_at);

create table if not exists public.owner_audit_log (
    id bigserial primary key,
    owner_telegram_user_id bigint not null,
    action varchar(64) not null,
    target_type varchar(32) not null,
    target_id varchar(64) not null,
    metadata_json text not null default '{}',
    created_at timestamptz not null default now()
);

create index if not exists ix_owner_audit_created
    on public.owner_audit_log (created_at desc);
create index if not exists ix_owner_audit_target
    on public.owner_audit_log (target_type, target_id);

alter table public.vip_grants enable row level security;
alter table public.owner_audit_log enable row level security;

revoke all on table public.vip_grants from anon;
revoke all on table public.vip_grants from authenticated;
revoke all on table public.owner_audit_log from anon;
revoke all on table public.owner_audit_log from authenticated;
revoke all on sequence public.owner_audit_log_id_seq from anon;
revoke all on sequence public.owner_audit_log_id_seq from authenticated;
