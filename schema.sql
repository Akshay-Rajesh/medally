-- Run this once in your Supabase SQL editor

create table users (
  id uuid primary key default gen_random_uuid(),
  email text unique not null,
  password_hash text not null,
  name text not null,
  created_at timestamptz default now()
);

create table family_members (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references users(id) on delete cascade,
  name text not null,
  relationship text not null,  -- 'self', 'father', 'mother', 'spouse', 'child', 'other'
  age int,
  gender text,
  created_at timestamptz default now()
);

create table medications (
  id uuid primary key default gen_random_uuid(),
  family_member_id uuid references family_members(id) on delete cascade,
  name text not null,
  dosage text not null,           -- e.g. "500mg"
  frequency text not null,        -- 'once_daily', 'twice_daily', 'three_times_daily', 'custom'
  times_of_day text[] not null,   -- e.g. ['08:00', '20:00']
  start_date date not null,
  end_date date,
  is_active boolean default true,
  created_at timestamptz default now()
);

create table reminders (
  id uuid primary key default gen_random_uuid(),
  medication_id uuid references medications(id) on delete cascade,
  scheduled_time timestamptz not null,
  status text default 'pending',   -- 'pending', 'taken', 'skipped', 'missed'
  confirmed_at timestamptz,
  alert_sent boolean default false,
  created_at timestamptz default now()
);

-- Index for scheduler performance
create index idx_reminders_scheduled on reminders(scheduled_time, status);
create index idx_reminders_alert on reminders(status, alert_sent, scheduled_time);
