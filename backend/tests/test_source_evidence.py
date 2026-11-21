import unittest
from app.services.job_sources.source_evidence import annotate_listing
from app.services.employer_source_preflight import preflight_employer_source

class SourceEvidenceTests(unittest.TestCase):
    def test_listing_does_not_verify_form_or_geography(self):
        job = annotate_listing({
            "source": "ashby", "source_url": "https://jobs.ashbyhq.com/acme/123",
            "source_job_id": "123", "company": "acme",
        }, checked_at="2026-11-21T11:00:00+00:00")
        self.assertEqual(job["source_status"], "open")
        self.assertEqual(job["source_check_method"], "ats_listing_api")
        self.assertEqual(job["source_checked_at"], "2026-11-21T11:00:00+00:00")
        self.assertFalse(job["application_form_verified"])
        self.assertEqual(preflight_employer_source(job)["decision"], "VERIFY_FIRST")
    def test_no_mutation(self):
        original = {"source": "lever"}
        annotate_listing(original)
        self.assertNotIn("source_status", original)

if __name__ == "__main__":
    unittest.main()
