-- PastMetki schema. Run in Supabase SQL Editor as project owner.
create extension if not exists pgcrypto;

create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  username text not null unique check (username ~ '^[a-z0-9_]{3,24}$'),
  display_name text not null default 'Пользователь',
  avatar_url text,
  invite_code text not null unique default upper(substr(encode(gen_random_bytes(8),'hex'),1,6)),
  complete_action text not null default 'history' check (complete_action in ('history','delete')),
  show_creation_time boolean not null default true,
  created_at timestamptz not null default now()
);
create table if not exists public.notes (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references public.profiles(id) on delete cascade,
  title text not null,
  tasks jsonb not null default '[]'::jsonb,
  due_at timestamptz,
  archived boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create table if not exists public.friendships (
  id uuid primary key default gen_random_uuid(),
  user_a uuid not null references public.profiles(id) on delete cascade,
  user_b uuid not null references public.profiles(id) on delete cascade,
  created_by uuid not null references public.profiles(id) on delete cascade,
  created_at timestamptz not null default now(),
  check(user_a < user_b),
  unique(user_a,user_b)
);
create table if not exists public.conversations (
  id uuid primary key default gen_random_uuid(),
  user_a uuid not null references public.profiles(id) on delete cascade,
  user_b uuid not null references public.profiles(id) on delete cascade,
  created_at timestamptz not null default now(),
  check(user_a < user_b),
  unique(user_a,user_b)
);
create table if not exists public.messages (
  id uuid primary key default gen_random_uuid(),
  conversation_id uuid not null references public.conversations(id) on delete cascade,
  sender_id uuid not null references public.profiles(id) on delete cascade,
  body text not null check (length(body) between 1 and 2000),
  created_at timestamptz not null default now()
);
create index if not exists notes_owner_created_idx on public.notes(owner_id,created_at desc);
create index if not exists notes_owner_due_idx on public.notes(owner_id,due_at);
create index if not exists messages_conversation_created_idx on public.messages(conversation_id,created_at);

alter table public.profiles enable row level security;
alter table public.notes enable row level security;
alter table public.friendships enable row level security;
alter table public.conversations enable row level security;
alter table public.messages enable row level security;

drop policy if exists "profiles visible to signed in users" on public.profiles;
create policy "profiles visible to signed in users" on public.profiles for select to authenticated using (true);
drop policy if exists "user inserts own profile" on public.profiles;
create policy "user inserts own profile" on public.profiles for insert to authenticated with check (id=auth.uid());
drop policy if exists "user updates own profile" on public.profiles;
create policy "user updates own profile" on public.profiles for update to authenticated using (id=auth.uid()) with check (id=auth.uid());

drop policy if exists "own notes read" on public.notes;
create policy "own notes read" on public.notes for select to authenticated using (owner_id=auth.uid());
drop policy if exists "own notes insert" on public.notes;
create policy "own notes insert" on public.notes for insert to authenticated with check (owner_id=auth.uid());
drop policy if exists "own notes update" on public.notes;
create policy "own notes update" on public.notes for update to authenticated using (owner_id=auth.uid()) with check (owner_id=auth.uid());
drop policy if exists "own notes delete" on public.notes;
create policy "own notes delete" on public.notes for delete to authenticated using (owner_id=auth.uid());

drop policy if exists "friendships participants read" on public.friendships;
create policy "friendships participants read" on public.friendships for select to authenticated using (auth.uid()=user_a or auth.uid()=user_b);
drop policy if exists "friendships creator inserts" on public.friendships;
create policy "friendships creator inserts" on public.friendships for insert to authenticated with check (created_by=auth.uid() and (auth.uid()=user_a or auth.uid()=user_b));
drop policy if exists "friendship participant deletes" on public.friendships;
create policy "friendship participant deletes" on public.friendships for delete to authenticated using (auth.uid()=user_a or auth.uid()=user_b);

drop policy if exists "conversation members read" on public.conversations;
create policy "conversation members read" on public.conversations for select to authenticated using (auth.uid()=user_a or auth.uid()=user_b);
drop policy if exists "conversation member create" on public.conversations;
create policy "conversation member create" on public.conversations for insert to authenticated with check (auth.uid()=user_a or auth.uid()=user_b);
drop policy if exists "conversation members delete" on public.conversations;
create policy "conversation members delete" on public.conversations for delete to authenticated using (auth.uid()=user_a or auth.uid()=user_b);

drop policy if exists "conversation members read messages" on public.messages;
create policy "conversation members read messages" on public.messages for select to authenticated using (exists(select 1 from public.conversations c where c.id=conversation_id and (c.user_a=auth.uid() or c.user_b=auth.uid())));
drop policy if exists "members send messages" on public.messages;
create policy "members send messages" on public.messages for insert to authenticated with check (sender_id=auth.uid() and exists(select 1 from public.conversations c where c.id=conversation_id and (c.user_a=auth.uid() or c.user_b=auth.uid())));
drop policy if exists "members clear messages" on public.messages;
create policy "members clear messages" on public.messages for delete to authenticated using (exists(select 1 from public.conversations c where c.id=conversation_id and (c.user_a=auth.uid() or c.user_b=auth.uid())));

-- Automatically create profile when Supabase Auth creates a user.
create or replace function public.handle_new_user()
returns trigger language plpgsql security definer set search_path=public as $$
declare uname text;
begin
  uname := coalesce(new.raw_user_meta_data->>'username', split_part(new.email,'@',1));
  insert into public.profiles(id,username,display_name)
  values(new.id, lower(uname), coalesce(new.raw_user_meta_data->>'display_name',lower(uname)))
  on conflict (id) do nothing;
  return new;
end; $$;
drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created after insert on auth.users for each row execute procedure public.handle_new_user();

-- Public profile lookup is intentionally limited to username/display name/avatar/invite code by table columns selected in app.
-- Create a public bucket for profile avatars. Storage policies:
insert into storage.buckets (id,name,public,file_size_limit,allowed_mime_types)
values ('avatars','avatars',true,2097152,array['image/png','image/jpeg','image/webp','image/gif'])
on conflict (id) do nothing;
drop policy if exists "avatar owner upload" on storage.objects;
create policy "avatar owner upload" on storage.objects for insert to authenticated with check (bucket_id='avatars' and (storage.foldername(name))[1]=auth.uid()::text);
drop policy if exists "avatar owner update" on storage.objects;
create policy "avatar owner update" on storage.objects for update to authenticated using (bucket_id='avatars' and (storage.foldername(name))[1]=auth.uid()::text);
drop policy if exists "avatars public read" on storage.objects;
create policy "avatars public read" on storage.objects for select to public using (bucket_id='avatars');
