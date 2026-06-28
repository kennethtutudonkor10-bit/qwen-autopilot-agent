-- Durable agent run-state for the publishing autopilot.
-- Apply against the GHAMAZON Supabase project.

create table if not exists agent_runs (
  id              uuid primary key default gen_random_uuid(),
  author_id       uuid,                              -- references users(id)
  book_id         uuid,                              -- references books(id) once published
  status          text not null default 'intake',   -- pipeline state machine
  step            text not null default 'intake',
  manuscript_uri  text,                              -- OSS object key
  draft_listing   jsonb,                             -- agent's proposed listing
  quality_flags   jsonb,
  pending_action  jsonb,                             -- what a human checkpoint is approving
  trace           jsonb not null default '[]',       -- reasoning steps for the dashboard
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now()
);

create index if not exists agent_runs_status_idx on agent_runs (status);

-- keep updated_at fresh
create or replace function set_agent_runs_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end $$;

drop trigger if exists agent_runs_updated_at on agent_runs;
create trigger agent_runs_updated_at
  before update on agent_runs
  for each row execute function set_agent_runs_updated_at();

-- RLS: admins can read runs from the dashboard; the Python backend uses the
-- service-role key, which bypasses RLS for writes.
alter table agent_runs enable row level security;

drop policy if exists "Admins read agent runs" on agent_runs;
create policy "Admins read agent runs"
  on agent_runs for select
  using (exists (select 1 from public.users u where u.id = auth.uid() and u.role = 'admin'));
