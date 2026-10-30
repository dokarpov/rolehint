"""Authenticated application command center built from RoleHint's own records.

Inspired by the *workflow* of Dossier, not a copy of AGPL source code.
Never infer submission from a saved draft or an opened employer form.
"""
from __future__ import annotations
from datetime import datetime, timezone

STAGE_LABELS = {
    "review": "To review",
    "draft": "Draft ready",
    "handoff": "Employer form opened",
    "awaiting_response": "Awaiting reply",
    "interview": "Recruiter / interview",
    "offer": "Offer",
    "rejected": "Rejected",
    "not_eligible": "Not eligible",
}
STAGE_ORDER = {name: i for i, name in enumerate(
    ("interview", "offer", "handoff", "awaiting_response", "draft", "review", "rejected", "not_eligible")
)}
SUBMISSION_STAGE = {
    "submitted": "awaiting_response",
    "awaiting_response": "awaiting_response",
    "recruiter_or_interview": "interview",
    "offer_candidate": "offer",
    "offer_confirmed": "offer",
    "rejected": "rejected",
}


def _date(epoch):
    if epoch is None:
        return None
    try:
        return datetime.fromtimestamp(float(epoch), timezone.utc).isoformat()
    except (TypeError, ValueError, OverflowError):
        return None


def build_application_board(jobs, submissions, handoffs, packs):
    """Pure projection of one user's records. Caller must scope each input to that user.

    Priorities: confirmed application > approved handoff > saved draft > review.
    A model's suggested APPLY decision is *not* a submission, and opening
    the employer's form is *not* a confirmed application.
    """
    latest = {}
    for submission in submissions:
        jid = submission.get("job_id")
        if not jid:
            continue
        if jid not in latest or float(submission.get("submitted_at") or 0) > float(
            latest[jid].get("submitted_at") or 0
        ):
            latest[jid] = submission
    rows = []
    for job in jobs:
        jid = job.get("job_id")
        if not jid:
            continue
        submission = latest.get(jid)
        handoff = handoffs.get(jid)
        pack = packs.get(jid)
        decision = str(job.get("decision") or "").upper().replace(" ", "_")
        if submission:
            response = str(submission.get("response_state") or "submitted")
            stage = SUBMISSION_STAGE.get(response, "awaiting_response")
        elif handoff:
            response = None
            stage = "handoff"
        elif pack:
            response = None
            stage = "draft"
        elif decision in {"DO_NOT_APPLY", "ALREADY_APPLIED"}:
            response = None
            stage = "not_eligible"
        else:
            response = None
            stage = "review"
        rows.append({
            "job_id": jid,
            "company": job.get("company") or "Unknown employer",
            "title": job.get("title") or "Untitled role",
            "location": job.get("location"),
            "source_url": job.get("source_url"),
            "stage": stage,
            "stage_label": STAGE_LABELS[stage],
            "decision": decision,
            "evidence_gaps": max(0, int(job.get("evidence_gaps") or 0)),
            "submitted_at": _date(submission.get("submitted_at")) if submission else None,
            "response_state": response,
            "pack_version": int(pack.get("version") or 1) if pack else None,
            "handoff_at": _date(handoff.get("approved_at")) if handoff else None,
        })
    rows.sort(key=lambda x: (
        STAGE_ORDER[x["stage"]],
        -(next((float(latest.get(x["job_id"], {}).get("submitted_at") or 0)), 0)),
        x["company"].casefold(),
    ))
    counts = {stage: 0 for stage in STAGE_LABELS}
    for row in rows:
        counts[row["stage"]] += 1
    return {
        "items": rows,
        "counts": counts,
        "summary": {
            "opportunities": len(rows),
            "confirmed_submitted": sum(1 for row in rows if row["submitted_at"] is not None),
            "awaiting_reply": counts["awaiting_response"],
            "interviews": counts["interview"],
            "offers": counts["offer"],
        },
        "source": "Saved authenticated RoleHint records only. Employer forms are never treated as submitted until you confirm.",
    }
