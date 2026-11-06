from app.services.market_compensation import observed_compensation
from app.services.auto_match.service import evaluate_constraints
from app.services.funnel.planner import classify


def row(i, *, title="Senior Product Manager", location="Remote Spain",
        currency="EUR", lo=40000, hi=60000, period="annual"):
    return {
        "title": title, "location": location, "currency": currency,
        "salary_min": lo, "salary_max": hi, "salary_period": period,
        "source_url": f"https://jobs.ashbyhq.com/company{i}/{i}"
    }


def test_salary_below_funnel_target_does_not_block_qualified_job():
    job = {"title": "Senior Product Manager", "description": "Own SaaS activation and experimentation.", "source": "ashby"}
    analysis = {
        "constraints": {"salary_min": 40000, "salary_max": 45000, "currency": "EUR"},
        "constraint_evaluation": {"hard": [], "unknown": [], "state": "CLEAR"},
        "verified_count": 4, "must_have_count": 5, "gap_count": 1, "review_count": 0
    }
    out = classify(job, analysis, {"remote_only": False, "salary_floor_annual": 0}, {"breadth": "standard"})
    assert out["tier"] in {"P0", "P1", "P2", "LOW_COST"}
    assert out["hard_blockers"] == []
    assert out["salary_signal"]["below_target"] is True


def test_explicit_hard_salary_floor_still_blocks():
    c = {"work_mode": "remote", "relocation_required": False,
         "salary_min": 40000, "salary_max": 50000, "currency": "EUR",
         "location": "Remote Spain", "remote_geo_restriction": "Spain"}
    assert evaluate_constraints(c, {"salary_floor_annual": 85000})["state"] == "BLOCKED"
    assert evaluate_constraints(c, {"salary_floor_annual": 0})["state"] == "CLEAR"


def test_sparse_salary_evidence_must_not_be_presented_as_market_median():
    jobs = [row(i) for i in range(4)]
    out = observed_compensation(row("target"), jobs)
    assert out["status"] == "insufficient_data"
    assert out["comparable_count"] == 4
    assert "median_listed_midpoint" not in out


def test_only_strictly_comparable_disclosed_bands_are_used():
    jobs = [row(i, lo=40000+i*1000, hi=60000+i*1000) for i in range(5)]
    jobs += [
        row(0),  # same canonical source, do not double-count
        row("us", currency="USD"),
        row("portugal", location="Portugal"),
        row("designer", title="Senior Product Designer"),
        row("head", title="Head of Product"),
        row("monthly", period="monthly")
    ]
    out = observed_compensation(row("target"), jobs)
    assert out["status"] == "descriptive_only"
    assert out["comparable_count"] == 5
    assert out["median_listed_midpoint"] == 52000
    assert len(out["source_urls"]) == 5
    assert out["distinct_employers"] == 5
    assert out["recommendation"].startswith("Do not turn")


def test_zero_salary_observations_never_invent_a_number():
    out = observed_compensation(row("target"), [])
    assert out["status"] == "insufficient_data"
    assert out["comparable_count"] == 0
    assert "median_listed_midpoint" not in out


def test_multiple_roles_from_one_employer_do_not_pretend_to_be_the_market():
    jobs = [row(i) for i in range(5)]
    for job in jobs:
        job["source_url"] = job["source_url"].replace("company"+str(job["source_url"].split("/")[-1]), "singlecompany")
    out = observed_compensation(row("target"), jobs)
    assert out["comparable_count"] == 5
    assert out["distinct_employers"] == 1
    assert out["status"] == "insufficient_data"
