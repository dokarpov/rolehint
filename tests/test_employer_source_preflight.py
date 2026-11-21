import unittest
from app.services.employer_source_preflight import preflight_employer_source

BASE = dict(source_url="https://jobs.ashbyhq.com/example/123", employer="Example",
            requisition_id="123", source_status="open",
            application_form_verified=True, geographic_eligibility="eligible",
            hard_requirements_checked=True)

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
    def test_bad_url(self):
        self.assertEqual(preflight_employer_source({**BASE, "source_url": "http://example.com/job"})["reason"], "invalid_source_url")

if __name__ == "__main__":
    unittest.main()
