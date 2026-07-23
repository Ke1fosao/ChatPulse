alter table public.featured_achievements
    drop constraint if exists ck_featured_achievement_slot;

alter table public.featured_achievements
    add constraint ck_featured_achievement_slot
    check (slot between 1 and 5);
