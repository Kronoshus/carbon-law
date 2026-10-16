-- Carbon Law backend schema (Postgres/Supabase compatible)
create table if not exists matters (
  id text primary key,
  client_name text not null,
  stage text not null,
  owner text not null,
  attorney_reviewer text,
  due_date date,
  last_client_contact date,
  next_client_contact date,
  next_action text,
  blocker text,
  document_status text,
  title_status text,
  funding_status text,
  appointment_status text,
  risk_level text,
  priority text,
  notes text,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);
create table if not exists change_requests (
  id uuid primary key default gen_random_uuid(),
  matter_id text references matters(id),
  requested_by text not null,
  change_type text not null,
  affected_documents text,
  required_attorney_decision boolean default true,
  impact text,
  status text default 'Open',
  created_at timestamptz default now()
);
create table if not exists appointments (
  id uuid primary key default gen_random_uuid(),
  matter_id text references matters(id),
  kind text,
  scheduled_at timestamptz not null,
  status text default 'Booked',
  reschedule_note text,
  created_at timestamptz default now()
);
create table if not exists documents (
  id uuid primary key default gen_random_uuid(),
  matter_id text references matters(id),
  name text not null,
  version integer default 1,
  status text default 'Draft',
  storage_path text,
  created_at timestamptz default now()
);
create table if not exists users (
  id uuid primary key default gen_random_uuid(),
  role text not null check (role in ('client','paralegal','attorney','admin')),
  email text unique not null,
  created_at timestamptz default now()
);
