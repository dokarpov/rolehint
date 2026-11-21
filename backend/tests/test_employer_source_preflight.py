import unittest
from datetime import datetime, timezone
from app.services.employer_source_preflight import preflight_employer_source

BASE = dict(source="ashby", source_url="https://jobs.ashbyhq.com/example/123",
            company="Example", source_job_id="123", source_status="open",
            application_form_verified=True, geographic_eligibility="eligible",
            source_checked_at=datetime.now(timezone.utc).isoformat(),
            source_check_method="ats_listing_api", hard_requirements_checked=True)

class EmployerSourcePreflightTests(unittest.TestCase):
    def test_verified(self):
        self.assertEqual(preflight_employer_source(BASE)["decision"], "SOURCE_VERIFIED")
    def test_closed(self):
        self.assertEqual(preflight_employer_source({**BASE, "source_status": "closed"})["decision"], "DO_NOT_APPLY")
    def test_unknown_geography(self):
        self.assertEqual(preflight_employer_source({**BASE, "geographic_eligibility": None})["decision"], "VERIFY_FIRST")
    def test_intermediary(self):
        self.assertEqual(preflight_employer_source({**BASE, "source_url": "https://www.linkedin.com/jobs/view/123"})["reason"], "intermediary_source")
    def test_missing_form(self):
        self.assertEqual(preflight_employer_source({**BASE, "application_form_verified": False})["decision"], "VERIFY_FIRST")
    def test_missing_requirements(self):
        self.assertEqual(preflight_employer_source({**BASE, "hard_requirements_checked": False})["decision"], "VERIFY_FIRST")
    def test_rejects_blank_employer_identity(self):
        for payload in (
            {**BASE, "company": "  "},
            {**BASE, "company": None},
            {**BASE, "source_job_id": " \t"},
            {**BASE, "source_job_id": None},
            {**BASE, "source_job_id": True},
            {**BASE, "source_job_id": []},
        ):
            with self.subTest(payload=payload):
                result = preflight_employer_source(payload)
                self.assertEqual(result["decision"], "VERIFY_FIRST")
                self.assertEqual(result["reason"], "missing_employer_identity")

    def test_numeric_ats_job_id_is_accepted(self):
        self.assertEqual(preflight_employer_source({**BASE, "source_job_id": 123})["decision"], "SOURCE_VERIFIED")

    def test_bad_url(self):
        self.assertEqual(preflight_employer_source({**BASE, "source_url": "http://example.com/job"})["reason"], "invalid_source_url")
    def test_aggregator_not_verified(self):
        self.assertEqual(preflight_employer_source({**BASE, "source": "adzuna"})["reason"], "source_not_direct_ats")

if __name__ == "__main__":
    unittest.main()
