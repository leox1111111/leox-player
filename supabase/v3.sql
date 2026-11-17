-- Leox Player - rozszerzenie v3: rola "creator" (dodaje i usuwa własne utwory we wspólnej muzyce).
-- Role: admin (role = 'admin'), creator (creator = true), member (pozostali).

alter table public.profiles add column if not exists creator boolean not null default false;

create or replace function public.is_creator() returns boolean
language sql stable security definer set search_path = public as $$
    select exists (select 1 from profiles where id = auth.uid()
                   and (creator or role = 'admin')
                   and (status = 'active'
                        or (status = 'banned' and ban_until is not null and ban_until < now())));
$$;
revoke execute on function public.is_creator() from public, anon;
grant execute on function public.is_creator() to authenticated;

create or replace function public.guard_profile() returns trigger
language plpgsql security definer set search_path = public as $$
begin
    if auth.uid() is null then
        return new;
    end if;
    if not is_admin() then
        if new.role is distinct from old.role or new.status is distinct from old.status
           or new.ban_reason is distinct from old.ban_reason or new.muted is distinct from old.muted
           or new.ban_until is distinct from old.ban_until or new.creator is distinct from old.creator
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
    if new.role is distinct from old.role or new.creator is distinct from old.creator then
        parts := parts || ('rola: '
            || case when old.role = 'admin' then 'admin' when old.creator then 'creator' else 'member' end
            || ' -> '
            || case when new.role = 'admin' then 'admin' when new.creator then 'creator' else 'member' end);
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

-- creator: własne utwory (dodatkowe reguły - admin ma swoje)
create policy tracks_insert_creator on public.tracks for insert to authenticated
    with check ((select is_creator()) and uploaded_by = (select auth.uid()));
create policy tracks_delete_creator on public.tracks for delete to authenticated
    using ((select is_creator()) and uploaded_by = (select auth.uid()));
create policy music_insert_creator on storage.objects for insert to authenticated
    with check (bucket_id = 'music' and (select public.is_creator())
                and (storage.foldername(name))[1] = (select auth.uid())::text);
create policy music_delete_creator on storage.objects for delete to authenticated
    using (bucket_id = 'music' and (select public.is_creator())
           and (storage.foldername(name))[1] = (select auth.uid())::text);
