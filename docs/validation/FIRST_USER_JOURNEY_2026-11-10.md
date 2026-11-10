# First-user journey — 10 November 2026

## Product contract corrected by founder
The candidate brings an existing CV draft (or a professional profile link). Review that source, show relevant vacancies with match/gap badges, adapt the existing CV before applying and write a focused cover letter grounded in actual experience, motivation and an honest explanation of gaps. Telegram is optional after results. Free CV value does not mean creating an unrelated CV from scratch.

## Configuration and deployed checks
- Production Telegram token and internal bot secret are present in Railway. Values were not requested or disclosed. POST /web-api/telegram/begin returned 200 and a bot deep link. This confirms provider lookup and browser challenge initiation, not human receipt of an OTP.
- Production deployment last updated 30 October; staging deployment 4 November, source b607f9c. They are different versions.
- Staging has no Telegram token or internal bot secret; its UI correctly disables sign-in. A browser walk from role entry returned zero Product Manager vacancies in this run, followed by unavailable Telegram sign-in. Empty results are not proof that no relevant jobs exist.
- Earlier GET/503 observations did not establish that Telegram authentication was broken. GET is not the method used to initiate login.

## Implemented on this review branch
- Return extracted CV text to its anonymous browser request with no-store; no account persistence.
- Editable original CV before matching. Corrections feed the next search and the selected-file save path.
- Clear old matching context, result cards and job drafts when a CV is replaced or discarded, including invalid replacement files.
- Visible CV-signal and gap-to-review badges. These are text-overlap signals, not verified qualifications.
- Preparation action per anonymous vacancy; separate tab-local CV versions, motivation, gap explanation, editable starter letter, approval and TXT downloads.
- Employer handoff remains distinct from submission; no fake employer applications were sent.

## Verification
- 13 focused backend tests PASS.
- DOM interaction regression PASS: CV correction → match/gap badges → selected vacancy draft → motivation/gap note → invalid replacement cleanup. DOM tests use fixture responses and do not prove browser rendering.
- Opt-in local backend test PASS with a newly created synthetic account and a real retrieved Ashby vacancy: Industry Product Marketing Manager, OpenAI, https://jobs.ashbyhq.com/openai/0e078d07-fb0b-4893-b90a-f50e413f3e13 . CV correction, confirmation, review, saved pack, Markdown export, manual handoff, logout and same-account resume passed. Login uses a captured local test mailbox, not a real email or Telegram account. The retrieved job was inserted into the isolated test account to exercise downstream behavior; this is NOT proof of automatic discovery-to-account delivery. No external form was submitted.
- Full Python suite: 150 passed, 10 failed, 1 skipped; identical ten failures reproduced on unchanged parent (149 passed). This branch is not a green public-release candidate.
- Chromium test launch in this execution sandbox failed because Unix socket creation is denied. The browser regression file is provided but not marked passed. A separate cloud-browser walk of existing staging was performed as described above.

## Remaining work / release blockers
1. Reconcile the maintained branch and deployed versions, then deploy an accepted staging build with a separate test bot or real email provider. Do not copy production secrets into code or enable login bypasses.
2. Human Telegram delivery/verification and real signed-in browser E2E still required. A bot token cannot create or act as a human Telegram account.
3. Professional-profile URL intake is not implemented here. No claim that a pasted LinkedIn URL has been imported or reviewed.
4. TXT editing/exports and a deterministic letter starter are implemented; professional PDF/DOCX output and the richer writing workflow remain unfinished.
5. Matching is transparent keyword overlap; requirement-level semantic assessment, source-backed eligibility/open-status checks and account delivery continuity still need work.
6. Drafts live only in the current tab; reload recovery and consent-based account synchronization are not implemented.
7. Resolve inherited suite failures before public-release approval.

## Full-suite failures reproduced on unchanged parent
```text
FAILED backend/tests/test_v12.py::V12Tests::test_managed_capabilities_gate_automation
FAILED backend/tests/test_v12.py::V12Tests::test_resolve_verify_changes_job
FAILED backend/tests/test_v12.py::V12Tests::test_user_isolated_notes - TypeEr...
FAILED backend/tests/test_v13.py::V13Tests::test_pack_persists_and_versions
FAILED backend/tests/test_v14.py::V14Tests::test_approval_requires_exact_suggestion_selection
FAILED backend/tests/test_v14.py::V14Tests::test_editing_approved_claim_revokes_approval
FAILED backend/tests/test_v14.py::V14Tests::test_stale_proposal_cannot_approve_downgraded_evidence
FAILED backend/tests/test_v14.py::V14Tests::test_unverified_evidence_cannot_be_approved_into_pack
FAILED backend/tests/test_v17.py::V17Tests::test_breadth_never_overrides_hard_salary_floor
FAILED tests/test_evidence_remote_mcp.py::test_complete_oauth_mcp_capture_review_and_revocation
```
