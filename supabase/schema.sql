-- Leox Player - baza w Supabase (profile, czat, wspólna muzyka, bany, przerwa techniczna).
-- Uruchom raz: Supabase -> SQL Editor -> New query -> wklej całość -> Run.
-- Można uruchomić ponownie (np. po aktualizacji) - nie kasuje danych.

-- ---------------------------------------------------------------- tabele
create table if not exists public.profiles (
    id           uuid primary key references auth.users (id) on delete cascade,
    username     text not null unique check (username ~ '^[a-z0-9_]{3,20}$'),
    display_name text not null default '' check (char_length(display_name) <= 40),
    bio          text not null default '' check (char_length(bio) <= 300),
    role         text not null default 'user' check (role in ('user', 'admin')),
    status       text not null default 'pending' check (status in ('pending', 'active', 'banned')),
    ban_reason   text not null default '',
    muted        boolean not null default false,          -- nie może pisać na czacie
    created_at   timestamptz not null default now(),
    last_seen    timestamptz
);

create table if not exists public.messages (
    id         bigserial primary key,
    user_id    uuid not null references public.profiles (id) on delete cascade,
    content    text not null check (char_length(btrim(content)) between 1 and 500),
    deleted    boolean not null default false,
    created_at timestamptz not null default now()
);
create index if not exists messages_created_idx on public.messages (created_at desc);

create table if not exists public.tracks (
    id          bigserial primary key,
    title       text not null check (char_length(title) between 1 and 200),
    artist      text not null default '' check (char_length(artist) <= 200),
    duration    real not null default 0,
    object_path text not null unique,                      -- plik w buckecie "music"
    size_bytes  bigint not null default 0,
    uploaded_by uuid references public.profiles (id) on delete set null,
    created_at  timestamptz not null default now()
);

create table if not exists public.app_settings (
    id            int primary key default 1 check (id = 1),
    maintenance   boolean not null default false,          -- aplikacja wyłączona dla wszystkich poza adminami
    maintenance_msg text not null default 'Przerwa techniczna. Spróbuj później.',
    announcement  text not null default '',                -- ogłoszenie na górze czatu
    updated_at    timestamptz not null default now()
);
insert into public.app_settings (id) values (1) on conflict (id) do nothing;

-- ---------------------------------------------------------------- funkcje pomocnicze
create or replace function public.is_admin() returns boolean
language sql stable security definer set search_path = public as $$
    select exists (select 1 from profiles
                   where id = auth.uid() and role = 'admin' and status = 'active');
$$;

create or replace function public.is_active() returns boolean
language sql stable security definer set search_path = public as $$
    select exists (select 1 from profiles where id = auth.uid() and status = 'active');
$$;

-- nowy użytkownik -> profil "pending" (nazwa z rejestracji)
create or replace function public.handle_new_user() returns trigger
language plpgsql security definer set search_path = public as $$
declare
    uname text := lower(coalesce(new.raw_user_meta_data ->> 'username', ''));
begin
    if uname !~ '^[a-z0-9_]{3,20}$' then
        uname := 'user_' || substr(replace(new.id::text, '-', ''), 1, 10);
    end if;
    insert into profiles (id, username, display_name)
    values (new.id, uname, coalesce(new.raw_user_meta_data ->> 'display_name', uname));
    return new;
end $$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created after insert on auth.users
    for each row execute function public.handle_new_user();

-- zwykły użytkownik nie zmieni sobie roli, statusu, wyciszenia ani nazwy konta
create or replace function public.guard_profile() returns trigger
language plpgsql security definer set search_path = public as $$
begin
    if auth.uid() is null then
        return new;                 -- SQL Editor / klucz serwisowy
    end if;
    if not is_admin() then
        if new.role is distinct from old.role or new.status is distinct from old.status
           or new.ban_reason is distinct from old.ban_reason or new.muted is distinct from old.muted
           or new.username is distinct from old.username or new.created_at is distinct from old.created_at then
            raise exception 'Brak uprawnień do zmiany tych pól';
        end if;
    elsif new.id = auth.uid() and (new.role <> 'admin' or new.status <> 'active') then
        if (select count(*) from profiles where role = 'admin' and status = 'active' and id <> new.id) = 0 then
            raise exception 'Nie możesz odebrać sobie uprawnień - jesteś jedynym adminem';
        end if;
    end if;
    return new;
end $$;

drop trigger if exists guard_profile on public.profiles;
create trigger guard_profile before update on public.profiles
    for each row execute function public.guard_profile();

-- czat: wyciszeni nie piszą, limit 1 wiadomość na 2 sekundy
create or replace function public.guard_message() returns trigger
language plpgsql security definer set search_path = public as $$
begin
    if (select muted from profiles where id = new.user_id) then
        raise exception 'Jesteś wyciszony na czacie';
    end if;
    if exists (select 1 from messages where user_id = new.user_id
               and created_at > now() - interval '2 seconds') then
        raise exception 'Za szybko - poczekaj chwilę';
    end if;
    new.created_at := now();
    new.deleted := false;
    return new;
end $$;

drop trigger if exists guard_message on public.messages;
create trigger guard_message before insert on public.messages
    for each row execute function public.guard_message();

-- statystyki dla panelu admina
create or replace function public.admin_stats() returns json
language plpgsql stable security definer set search_path = public as $$
begin
    if not is_admin() then
        raise exception 'Tylko dla admina';
    end if;
    return json_build_object(
        'users',    (select count(*) from profiles),
        'pending',  (select count(*) from profiles where status = 'pending'),
        'active',   (select count(*) from profiles where status = 'active'),
        'banned',   (select count(*) from profiles where status = 'banned'),
        'online',   (select count(*) from profiles where last_seen > now() - interval '5 minutes'),
        'messages', (select count(*) from messages where not deleted),
        'tracks',   (select count(*) from tracks),
        'mb',       (select coalesce(round(sum(size_bytes) / 1048576.0, 1), 0) from tracks));
end $$;

-- znak życia (kto jest online); działa też dla oczekujących
create or replace function public.touch() returns void
language sql security definer set search_path = public as $$
    update profiles set last_seen = now() where id = auth.uid();
$$;

-- ---------------------------------------------------------------- uprawnienia (RLS)
alter table public.profiles     enable row level security;
alter table public.messages     enable row level security;
alter table public.tracks       enable row level security;
alter table public.app_settings enable row level security;

drop policy if exists profiles_select on public.profiles;
create policy profiles_select on public.profiles for select to authenticated
    using (id = auth.uid() or is_active());
drop policy if exists profiles_update on public.profiles;
create policy profiles_update on public.profiles for update to authenticated
    using (id = auth.uid() or is_admin()) with check (id = auth.uid() or is_admin());

drop policy if exists messages_select on public.messages;
create policy messages_select on public.messages for select to authenticated
    using (is_active() and (not deleted or is_admin()));
drop policy if exists messages_insert on public.messages;
create policy messages_insert on public.messages for insert to authenticated
    with check (is_active() and user_id = auth.uid());
drop policy if exists messages_update on public.messages;
create policy messages_update on public.messages for update to authenticated
    using (is_admin()) with check (is_admin());
drop policy if exists messages_delete on public.messages;
create policy messages_delete on public.messages for delete to authenticated
    using (is_admin());

drop policy if exists tracks_select on public.tracks;
create policy tracks_select on public.tracks for select to authenticated
    using (is_active());
drop policy if exists tracks_insert on public.tracks;
create policy tracks_insert on public.tracks for insert to authenticated
    with check (is_admin());
drop policy if exists tracks_update on public.tracks;
create policy tracks_update on public.tracks for update to authenticated
    using (is_admin()) with check (is_admin());
drop policy if exists tracks_delete on public.tracks;
create policy tracks_delete on public.tracks for delete to authenticated
    using (is_admin());

drop policy if exists settings_select on public.app_settings;
create policy settings_select on public.app_settings for select to anon, authenticated
    using (true);
drop policy if exists settings_update on public.app_settings;
create policy settings_update on public.app_settings for update to authenticated
    using (is_admin()) with check (is_admin());

grant select, update on public.profiles to authenticated;
grant select, insert, update, delete on public.messages to authenticated;
grant usage, select on sequence public.messages_id_seq to authenticated;
grant select, insert, update, delete on public.tracks to authenticated;
grant usage, select on sequence public.tracks_id_seq to authenticated;
grant select on public.app_settings to anon, authenticated;
grant update on public.app_settings to authenticated;
grant execute on function public.admin_stats() to authenticated;
grant execute on function public.touch() to authenticated;

-- ---------------------------------------------------------------- pliki MP3 (Storage)
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('music', 'music', false, 52428800,
        array['audio/mpeg', 'audio/mp4', 'audio/x-m4a', 'audio/aac', 'audio/ogg',
              'audio/opus', 'audio/flac', 'audio/wav', 'audio/webm', 'application/octet-stream'])
on conflict (id) do update set file_size_limit = excluded.file_size_limit,
                               allowed_mime_types = excluded.allowed_mime_types;

drop policy if exists music_read on storage.objects;
create policy music_read on storage.objects for select to authenticated
    using (bucket_id = 'music' and public.is_active());
drop policy if exists music_insert on storage.objects;
create policy music_insert on storage.objects for insert to authenticated
    with check (bucket_id = 'music' and public.is_admin());
drop policy if exists music_delete on storage.objects;
create policy music_delete on storage.objects for delete to authenticated
    using (bucket_id = 'music' and public.is_admin());

-- ---------------------------------------------------------------- pierwszy admin
-- Po założeniu konta w aplikacji uruchom (zmień nazwę na swoją):
--   update public.profiles set role = 'admin', status = 'active' where username = 'twoja_nazwa';
