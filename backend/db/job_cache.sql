-- Supabase job_cache table used by backend/services/cache_service.py (JobCache)
-- Run this SQL in your Supabase project's SQL editor before using caching in prod.

create table if not exists job_cache (
  service    text        not null,
  cache_key  text        not null,
  response   jsonb       not null,
  created_at timestamptz not null default now(),
  primary key (service, cache_key)
);

create index if not exists idx_job_cache_created_at
  on job_cache (created_at);


