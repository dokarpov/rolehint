-- RoleHint analytics foundation. Run in a dedicated PostgreSQL database.
BEGIN;
CREATE SCHEMA IF NOT EXISTS job_analytics;
CREATE TABLE IF NOT EXISTS job_analytics.companies (
 id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 name text NOT NULL CHECK (length(trim(name))>0),
 domain text,
 UNIQUE(domain)
);
CREATE TABLE IF NOT EXISTS job_analytics.vacancies (
 id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 company_id bigint NOT NULL REFERENCES job_analytics.companies(id),
 external_key text NOT NULL,
 title text NOT NULL CHECK (length(trim(title))>0),
 source_url text,
 description text,
 discovered_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE(company_id,external_key)
);
CREATE TABLE IF NOT EXISTS job_analytics.requirements (
 id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 vacancy_id bigint NOT NULL REFERENCES job_analytics.vacancies(id) ON DELETE CASCADE,
 statement text NOT NULL,
 importance text NOT NULL CHECK (importance IN ('mandatory','preferred','unknown')),
 source_excerpt text,
 UNIQUE(vacancy_id,statement)
);
CREATE TABLE IF NOT EXISTS job_analytics.channels (
 id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 name text NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS job_analytics.vacancy_sources (
 vacancy_id bigint NOT NULL REFERENCES job_analytics.vacancies(id) ON DELETE CASCADE,
 channel_id bigint NOT NULL REFERENCES job_analytics.channels(id),
 discovered_at timestamptz NOT NULL DEFAULT now(),
 PRIMARY KEY(vacancy_id,channel_id)
);
CREATE TABLE IF NOT EXISTS job_analytics.applications (
 id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 owner_key text NOT NULL CHECK(length(owner_key)>0),
 vacancy_id bigint NOT NULL REFERENCES job_analytics.vacancies(id),
 attempt_no integer NOT NULL DEFAULT 1 CHECK(attempt_no>0),
 applied_at timestamptz,
 created_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE(owner_key,vacancy_id,attempt_no)
);
CREATE TABLE IF NOT EXISTS job_analytics.application_events (
 id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 application_id bigint NOT NULL REFERENCES job_analytics.applications(id) ON DELETE CASCADE,
 event_key text NOT NULL,
 stage text NOT NULL CHECK(stage IN ('saved','applied','screen','interview','final','offer','rejected','withdrawn')),
 occurred_at timestamptz NOT NULL,
 recorded_at timestamptz NOT NULL DEFAULT now(),
 source text NOT NULL CHECK(source IN ('user','email','system','import')),
 confirmed boolean NOT NULL DEFAULT false,
 UNIQUE(application_id,event_key)
);
CREATE INDEX IF NOT EXISTS application_events_history_idx ON job_analytics.application_events(application_id,occurred_at,id);
CREATE INDEX IF NOT EXISTS applications_owner_idx ON job_analytics.applications(owner_key,created_at);
CREATE VIEW job_analytics.stage_reach AS
SELECT a.owner_key, a.id AS application_id, e.stage, min(e.occurred_at) AS first_reached_at
FROM job_analytics.applications a JOIN job_analytics.application_events e ON e.application_id=a.id
WHERE e.confirmed AND e.stage IN ('applied','screen','interview','final','offer')
GROUP BY a.owner_key,a.id,e.stage;
CREATE VIEW job_analytics.stage_funnel AS
SELECT owner_key,stage,count(DISTINCT application_id) AS reached
FROM job_analytics.stage_reach GROUP BY owner_key,stage;
COMMIT;
