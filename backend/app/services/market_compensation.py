"""Conservative, provenance-aware description of observed vacancy compensation.

Not a population estimate, an offer predictor or a personal market value.
Only comparable public listing bands are used; no FX guesses or salary imputation.
"""
from __future__ import annotations

from statistics import median
from urllib.parse import urlsplit


def _family(title):
    t = str(title or "").lower()
    if any(s in t for s in ("product manager", "product lead", "head of product", "product owner", "chief product")):
        return "product_management"
    if any(s in t for s in ("product designer", "design lead", "head of design", "design director")):
        return "product_design"
    return None


def _region(location):
    t = str(location or "").lower()
    if any(s in t for s in ("spain", "barcelona", "madrid", "valencia", "catalonia")):
        return "spain_eligible"
    if any(s in t for s in ("europe", "european union", "eu remote", "emea")):
        return "europe"
    return None


def _seniority(title):
    t = str(title or "").lower()
    if any(s in t for s in ("chief", "vp ", "vice president", "head of", "director")):
        return "executive"
    if any(s in t for s in ("senior", "sr.", "lead", "staff", "principal", "founding")):
        return "senior_lead"
    return "unspecified"


def _extract(job):
    raw = job.get("payload") or job
    constraints = (raw.get("analysis") or {}).get("constraints") or {}
    lo = raw.get("salary_min")
    hi = raw.get("salary_max")
    if lo is None: lo = constraints.get("salary_min")
    if hi is None: hi = constraints.get("salary_max")
    currency = str(raw.get("currency") or constraints.get("currency") or "").upper()
    loc = job.get("location") or raw.get("location")
    title = job.get("title") or raw.get("title")
    url = job.get("source_url") or raw.get("source_url")
    if not (url and str(url).startswith("https://")):
        return None
    try:
        lo, hi = float(lo), float(hi)
    except (ValueError, TypeError):
        return None
    # Annual band only. Monthly, daily, hourly and missing periodicity are not converted.
    period = str(raw.get("salary_period") or constraints.get("salary_period") or "annual").lower()
    if period not in ("annual", "year", "yearly"): return None
    if not (20000 <= lo <= hi <= 500000): return None
    if currency not in ("EUR", "USD", "GBP"): return None
    if not (urlsplit(str(url)).hostname): return None
    return {"role_family": _family(title), "seniority": _seniority(title),
            "region": _region(loc), "currency": currency,
            "midpoint": (lo + hi) / 2, "lower": lo, "upper": hi, "url": str(url).split("?")[0],
            "employer_key": (urlsplit(str(url)).path.split("/")[1].lower() if urlsplit(str(url)).hostname in ("jobs.ashbyhq.com", "boards.greenhouse.io", "job-boards.greenhouse.io", "jobs.lever.co") and len(urlsplit(str(url)).path.split("/"))>1 else urlsplit(str(url)).hostname.lower())}


def observed_compensation(target, listings, min_comparables=5):
    """Describe listed bands for a comparable cohort; never infer hire probabilities."""
    family = _family(target.get("title"))
    seniority = _seniority(target.get("title"))
    region = _region(target.get("location"))
    if not (family and region):
        return {"status": "unscoped", "comparable_count": 0, "reason": "Role family or target geography cannot be established."}
    currency = "EUR" if region in ("spain_eligible", "europe") else None
    seen, observed = set(), []
    for row in listings:
        d = _extract(row)
        if not d: continue
        if d["role_family"] != family or d["seniority"] != seniority: continue
        if d["region"] != region or d["currency"] != currency: continue
        if d["url"] in seen: continue
        seen.add(d["url"])
        observed.append(d)
    count = len(observed)
    employer_count = len({r["employer_key"] for r in observed})
    base = {"status": "insufficient_data", "comparable_count": count, "currency": currency,
            "role_family": family, "seniority": seniority, "region": region, "distinct_employers": employer_count,
            "method": "Public listing bands, same role-family/seniority/geography/currency; one unique source URL per observation.",
            "limitations": "Convenience sample, not a labor-market median. Posting recency, employment structure, benefits, self-selection and actual offers are unverified. No annualization or foreign-exchange assumptions.",
            "source_urls": [r["url"] for r in observed]}
    if count < min_comparables or employer_count < 3:
        base["reason"] = f"Only {count} comparable bands from {employer_count} employers; require at least {min_comparables} listings and 3 independent employers."
        return base
    mids = [r["midpoint"] for r in observed]
    base.update(status="descriptive_only", median_listed_midpoint=median(mids),
                observed_lowest_band_min=min(r["lower"] for r in observed),
                observed_highest_band_max=max(r["upper"] for r in observed),
                recommendation="Do not turn this sample into a salary floor or an acceptance probability; discuss role-specific compensation after confirming legal eligibility and scope.")
    return base
