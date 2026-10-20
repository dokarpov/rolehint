BEGIN;
-- Isolated fixture owner and requisition; all writes are rolled back.
INSERT INTO job_analytics.companies(name,domain)
VALUES ('RoleHint Analytics Fixture','rolehint-fixture.invalid')
ON CONFLICT(domain) DO NOTHING;
INSERT INTO job_analytics.vacancies(company_id,external_key,title)
SELECT id,'rolehint-fixture-001','Fixture Product Manager'
FROM job_analytics.companies WHERE domain='rolehint-fixture.invalid'
ON CONFLICT(company_id,external_key) DO NOTHING;
INSERT INTO job_analytics.applications(owner_key,vacancy_id)
SELECT 'rolehint-fixture-owner',v.id FROM job_analytics.vacancies v
JOIN job_analytics.companies c ON c.id=v.company_id
WHERE c.domain='rolehint-fixture.invalid' AND v.external_key='rolehint-fixture-001'
ON CONFLICT(owner_key,vacancy_id,attempt_no) DO NOTHING;
-- Inferred stages must never count as confirmed reach.
INSERT INTO job_analytics.application_events(application_id,event_key,stage,occurred_at,source,confirmed)
SELECT a.id,'fixture-inferred-interview','interview',now(),'email',false
FROM job_analytics.applications a WHERE a.owner_key='rolehint-fixture-owner'
ON CONFLICT(application_id,event_key) DO NOTHING;
INSERT INTO job_analytics.application_events(application_id,event_key,stage,occurred_at,source,confirmed)
SELECT a.id,'fixture-confirmed-apply','applied',now(),'user',true
FROM job_analytics.applications a WHERE a.owner_key='rolehint-fixture-owner'
ON CONFLICT(application_id,event_key) DO NOTHING;
-- Replaying an identical event must not duplicate reach.
INSERT INTO job_analytics.application_events(application_id,event_key,stage,occurred_at,source,confirmed)
SELECT a.id,'fixture-confirmed-apply','applied',now(),'user',true
FROM job_analytics.applications a WHERE a.owner_key='rolehint-fixture-owner'
ON CONFLICT(application_id,event_key) DO NOTHING;
DO $$
DECLARE n bigint;
BEGIN
 SELECT reached INTO n FROM job_analytics.stage_funnel
 WHERE owner_key='rolehint-fixture-owner' AND stage='applied';
 IF n IS DISTINCT FROM 1 THEN RAISE EXCEPTION 'confirmed application reach expected 1, got %',n; END IF;
 SELECT reached INTO n FROM job_analytics.stage_funnel
 WHERE owner_key='rolehint-fixture-owner' AND stage='interview';
 IF n IS NOT NULL THEN RAISE EXCEPTION 'unconfirmed interview must not count'; END IF;
 IF (SELECT count(*) FROM job_analytics.application_events e
 JOIN job_analytics.applications a ON a.id=e.application_id
 WHERE a.owner_key='rolehint-fixture-owner' AND e.event_key='fixture-confirmed-apply') <> 1
 THEN RAISE EXCEPTION 'duplicate event replay'; END IF;
END $$;
ROLLBACK;
