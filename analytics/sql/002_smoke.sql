BEGIN;
INSERT INTO job_analytics.companies(name,domain) VALUES ('Fixture Company','fixture.invalid') ON CONFLICT(domain) DO NOTHING;
INSERT INTO job_analytics.vacancies(company_id,external_key,title)
SELECT id,'fixture-001','Fixture Product Manager' FROM job_analytics.companies WHERE domain='fixture.invalid'
ON CONFLICT(company_id,external_key) DO NOTHING;
INSERT INTO job_analytics.applications(owner_key,vacancy_id)
SELECT 'fixture-user',id FROM job_analytics.vacancies WHERE external_key='fixture-001'
ON CONFLICT(owner_key,vacancy_id,attempt_no) DO NOTHING;
INSERT INTO job_analytics.application_events(application_id,event_key,stage,occurred_at,source,confirmed)
SELECT id,'fixture-apply','applied',now(),'user',true FROM job_analytics.applications WHERE owner_key='fixture-user'
ON CONFLICT(application_id,event_key) DO NOTHING;
DO $$ BEGIN
IF (SELECT reached FROM job_analytics.stage_funnel WHERE owner_key='fixture-user' AND stage='applied') <> 1
THEN RAISE EXCEPTION 'funnel count incorrect'; END IF;
END $$;
ROLLBACK;
