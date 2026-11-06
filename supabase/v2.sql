-- Leox Player - rozszerzenie v2: zdjęcia profilowe, bany czasowe, dziennik admina,
-- reset hasła i usuwanie kont przez admina.

alter table public.profiles add column if not exists avatar_path text not null default '';
alter table public.profiles add column if not exists ban_until timestamptz;

create table if not exists public.admin_log (
    id         bigserial primary key,
    admin_id   uuid references public.profiles (id) on delete set null,
    target_id  uuid references public.profiles (id) on delete set null,
    target_name text not null default '',
    action     text not null,
    details    text not null default '',
    created_at timestamptz not null default now()
);
create index if not exists admin_log_created_idx on public.admin_log (created_at desc);
create index if not exists admin_log_admin_idx on public.admin_log (admin_id);
create index if not exists admin_log_target_idx on public.admin_log (target_id);
alter table public.admin_log enable row level security;
create policy admin_log_select on public.admin_log for select to authenticated
    using ((select is_admin()));
grant select on public.admin_log to authenticated;

-- ban czasowy: po upływie ban_until konto działa jak aktywne
create or replace function public.is_active() returns boolean
language sql stable security definer set search_path = public as $$
    select exists (select 1 from profiles where id = auth.uid()
                   and (status = 'active'
                        or (status = 'banned' and ban_until is not null and ban_until < now())));
$$;

create or replace function public.guard_profile() returns trigger
language plpgsql security definer set search_path = public as $$
begin
    if auth.uid() is null then
        return new;
    end if;
    if not is_admin() then
        if new.role is distinct from old.role or new.status is distinct from old.status
           or new.ban_reason is distinct from old.ban_reason or new.muted is distinct from old.muted
           or new.ban_until is distinct from old.ban_until
           or new.username is distinct from old.username or new.created_at is distinct from old.created_at then
            raise exception 'Brak uprawnień do zmiany tych pól';
        end if;
        if new.avatar_path <> '' and new.avatar_path not like (auth.uid()::text || '/%') then
            raise exception 'Nieprawidłowe zdjęcie profilowe';
        end if;
    elsif new.id = auth.uid() and (new.role <> 'admin' or new.status <> 'active') then
        if (select count(*) from profiles where role = 'admin' and status = 'active' and id <> new.id) = 0 then
            raise exception 'Nie możesz odebrać sobie uprawnień - jesteś jedynym adminem';
        end if;
    end if;
    return new;
end $$;

-- dziennik: każda zmiana cudzego profilu przez admina
create or replace function public.log_profile_change() returns trigger
language plpgsql security definer set search_path = public as $$
declare
    parts text[] := '{}';
begin
    if auth.uid() is null or auth.uid() = new.id then
        return new;
    end if;
    if new.status is distinct from old.status then
        parts := parts || ('status: ' || old.status || ' -> ' || new.status);
    end if;
    if new.ban_reason is distinct from old.ban_reason and new.ban_reason <> '' then
        parts := parts || ('powód: ' || new.ban_reason);
    end if;
    if new.ban_until is distinct from old.ban_until and new.ban_until is not null then
        parts := parts || ('do: ' || to_char(new.ban_until at time zone 'Europe/Warsaw', 'YYYY-MM-DD HH24:MI'));
    end if;
    if new.role is distinct from old.role then
        parts := parts || ('rola: ' || old.role || ' -> ' || new.role);
    end if;
    if new.muted is distinct from old.muted then
        parts := parts || (case when new.muted then 'wyciszony' else 'odciszony' end);
    end if;
    if new.display_name is distinct from old.display_name then
        parts := parts || ('nazwa: ' || old.display_name || ' -> ' || new.display_name);
    end if;
    if new.bio is distinct from old.bio then
        parts := parts || 'zmieniono opis';
    end if;
    if new.avatar_path is distinct from old.avatar_path then
        parts := parts || (case when new.avatar_path = '' then 'usunięto zdjęcie' else 'zmieniono zdjęcie' end);
    end if;
    if array_length(parts, 1) > 0 then
        insert into admin_log (admin_id, target_id, target_name, action, details)
        values (auth.uid(), new.id, new.username, 'profil', array_to_string(parts, '; '));
    end if;
    return new;
end $$;

create trigger log_profile_change after update on public.profiles
    for each row execute function public.log_profile_change();

-- admin ustawia nowe hasło (np. ktoś zapomniał)
create or replace function public.admin_set_password(target uuid, new_password text) returns void
language plpgsql security definer set search_path = public, extensions as $$
begin
    if not is_admin() then
        raise exception 'Tylko dla admina';
    end if;
    if char_length(new_password) < 6 then
        raise exception 'Hasło musi mieć co najmniej 6 znaków';
    end if;
    update auth.users set encrypted_password = extensions.crypt(new_password, extensions.gen_salt('bf')),
                          updated_at = now()
     where id = target;
    if not found then
        raise exception 'Nie ma takiego konta';
    end if;
    insert into admin_log (admin_id, target_id, target_name, action, details)
    select auth.uid(), target, username, 'hasło', 'ustawiono nowe hasło' from profiles where id = target;
end $$;

-- admin usuwa konto (profil, wiadomości; utwory zostają)
create or replace function public.admin_delete_user(target uuid) returns void
language plpgsql security definer set search_path = public as $$
declare
    uname text;
begin
    if not is_admin() then
        raise exception 'Tylko dla admina';
    end if;
    if target = auth.uid() then
        raise exception 'Nie możesz usunąć własnego konta';
    end if;
    select username into uname from profiles where id = target;
    if uname is null then
        raise exception 'Nie ma takiego konta';
    end if;
    insert into admin_log (admin_id, target_id, target_name, action, details)
    values (auth.uid(), null, uname, 'usunięto konto', '');
    delete from auth.users where id = target;
end $$;

revoke execute on function public.log_profile_change() from public, anon, authenticated;
revoke execute on function public.admin_set_password(uuid, text) from public, anon;
revoke execute on function public.admin_delete_user(uuid) from public, anon;
grant execute on function public.admin_set_password(uuid, text) to authenticated;
grant execute on function public.admin_delete_user(uuid) to authenticated;

-- zdjęcia profilowe: avatars/<id_użytkownika>/<plik>.jpg
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('avatars', 'avatars', false, 2097152, array['image/jpeg', 'image/png', 'image/webp'])
on conflict (id) do nothing;

create policy avatars_read on storage.objects for select to authenticated
    using (bucket_id = 'avatars' and ((select public.is_active())
                                      or (storage.foldername(name))[1] = (select auth.uid())::text));
create policy avatars_insert on storage.objects for insert to authenticated
    with check (bucket_id = 'avatars' and (storage.foldername(name))[1] = (select auth.uid())::text);
create policy avatars_delete on storage.objects for delete to authenticated
    using (bucket_id = 'avatars' and ((storage.foldername(name))[1] = (select auth.uid())::text
                                      or (select public.is_admin())));
