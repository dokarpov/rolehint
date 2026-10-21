# RoleHint — exhaustive UX and failure-injection scenario matrix
**Date:** 2026-10-21 · **Status:** acceptance inventory, **NOT** a claim of tests passed. **Cases:** 200.

Read this with [UX_SERVICE_AUDIT_V2_2026-10-21.md](UX_SERVICE_AUDIT_V2_2026-10-21.md), [RELEASE_TEST_MATRIX.md](RELEASE_TEST_MATRIX.md), the product/matching/entitlement specs and the specific implementation SHA.

**Legend:** P0 = privacy, authenticity, core promise, account isolation, unrecoverable flow, financial or significant trust failure; P1 = high-impact user frustration or state inconsistency; P2 = polish/optional future decision. **Required evidence** names the future test, not an observed PASS. Mark every case PASS / FAIL / BLOCKED / UNTESTED, versioned by env + SHA + device + fixture. For cases not implemented, record FAIL/SPECIFIED rather than inventing acceptance.

**Test personas / fixtures:** CV-first senior PM in Spain requiring B2B; role-only seeker; career switcher; student with sparse CV; non-English CV; disabled-email user; returning Telegram/email account; two simultaneous accounts; free exhausted; future paid active/expired; mixed global remote employment. Use synthetic/consented CVs, no private profile committed to Git. Conduct real employer URL checks read-only; use an authorized test form for any submission mechanics.

**Coverage principle:** A scenario is accepted only after successful observable state transition, truthful copy, persistence where promised, privacy guarantees, safe recovery and keyboard/mobile operation. Zero/fewer-than-ten and all-source failures receive dedicated tests. No fake ATS vacancies or payments.

## A. Public site, CTA and version routing

| ID | Scenario / trigger | Expected behavior and recovery | Priority | Required evidence |
|---|---|---|---|---|
| L01 | Landing hero → CTA | Opens actual first-value webapp, not a fictional workspace | P0 | Live navigation + SHA |
| L02 | Two CTAs/header/footer | Same destination and truthful action label; no duplicate demo funnel | P1 | DOM + click |
| L03 | Visitor from Google/search or deep-link | Canonical page, copy and privacy links consistent with release state | P1 | Desktop/mobile links |
| L04 | Legacy /workspace.html shared externally | Clearly illustrative; no fake real jobs, no public signup confusion | P1 | Direct URL test |
| L05 | Old /onboarding.html entered directly | No private upload or contradictory user path to mock jobs | P1 | Direct URL test |
| L06 | Pricing/subscription/install pages visited | Brand, ten-free and not-yet-live paid claims all accurate | P1 | Copy+link diff |
| L07 | Dark-mode OS or PWA home-screen | Readable contrast and no legacy cached green skin | P1 | Device/PWA test |
| L08 | Landing offline / stale service-worker | Clear offline state, no misleading beta CTA or obsolete cached release | P1 | Offline/PWA |
| L09 | Short 320px page, text 200% zoom | Hero, navigation and CTA remain usable without clipping | P1 | Safari+a11y |
| L10 | Marketing animation reduced-motion / pointerless touch | Useful still graphic without control or fake click, respects motion preference | P2 | Animation test |

## B. Entry, progress and navigation

| ID | Scenario / trigger | Expected behavior and recovery | Priority | Required evidence |
|---|---|---|---|---|
| E01 | First visit, no CV or role | Both entry points clearly visible; no auth required | P0 | Browser first viewport |
| E02 | Choose role-only | Immediate search with explicit CV-unassessed state | P0 | Browser + live API |
| E03 | Choose CV first | File handling and privacy notice precede submission | P0 | Browser + network |
| E04 | Upload CV with inferred role | Show extraction and confirm role before jobs; no unexplained auto-jump | P0 | Browser state assertion |
| E05 | CV with no inferred role | Show selectable suggestions and editable role field, no forced default | P0 | Browser |
| E06 | Go back from results | Retain query and valid optional analysis only until expiry | P1 | Browser history |
| E07 | Browser back/forward and reload | Correct route/state or explicit expired-analysis recovery | P1 | Browser |
| E08 | Two fast clicks on Find | Exactly one active search, button disabled/progress, no duplicate charges | P0 | Concurrency |
| E09 | Network drops mid-search | Retry without losing input or charging allowance | P0 | Offline/network |
| E10 | Guest clicks Save vs Alerts vs Apply | Return to intended action after sign-in; no conflation | P1 | Browser + identity |

## C. CV upload, extraction and consent

| ID | Scenario / trigger | Expected behavior and recovery | Priority | Required evidence |
|---|---|---|---|---|
| C01 | Valid PDF | Extract with traceable sections, maintain order and file provenance | P0 | Fixture + E2E |
| C02 | Valid DOCX, embedded tables | Preserve skills/jobs/dates/metrics in readable order | P0 | Fixture |
| C03 | Valid UTF-8 TXT and non-English CV | Correct Unicode and role/experience parsing | P0 | Fixture |
| C04 | Scanned PDF / image-only | Explain OCR unavailable and offer text/paste correction; no hallucination | P0 | Negative browser |
| C05 | Encrypted PDF or malformed DOCX | Clear retry instruction; no phantom success or stuck spinner | P1 | Fixture |
| C06 | Wrong extension/MIME/polyglot | Reject safely; no parser execution or storage | P0 | Security |
| C07 | Zero-byte or >8 MB | Immediate accessible error; input still editable | P1 | Boundary test |
| C08 | Very long 100k+ or many pages | Bounded parsing time/memory; useful partial or explicit rejection | P1 | Load test |
| C09 | CV with several professions/career gaps | Suggest multiple role families without arbitrary Product Manager default | P0 | Fixture+human |
| C10 | Metric like 30% not linked to personal ownership | Ask what it measures, preserve claim as self-reported | P0 | Evidence audit |
| C11 | Duplicate CV upload or file replacement | Versioned source; derived analyses/pack marked stale | P0 | API + regression |
| C12 | Edit CV text then confirm | Every edit invalidates previous confirmation and recalculates evidence | P0 | API+browser |
| C13 | Discard CV after parsing | Clear file, extracted matching terms, pending jobs and server analysis ID | P0 | Privacy regression |
| C14 | Close tab, analysis expires | No silent persistent CV; clear expiry/restart explanation | P0 | TTL test |
| C15 | Login after anonymous analysis | Explicit one-time consent to attach to *same* user; no cross-account leak | P0 | Two-account E2E |
| C16 | Delete saved CV | Erase source, related proof/cache/derivatives under retention policy | P0 | Deletion graph |
| C17 | Prompt injection or HTML inside CV | Rendered only as escaped data; never drives instructions or script | P0 | Security fixture |

## D. Role input, ambiguity and career switching

| ID | Scenario / trigger | Expected behavior and recovery | Priority | Required evidence |
|---|---|---|---|---|
| R01 | Product Manager vs Project Manager | Distinct occupation intent; no cross-match substitution | P0 | Ranking fixture |
| R02 | Role synonym Product Lead / Principal PM | Explain alias inclusion while preserving seniority/scope | P1 | Ranking fixture |
| R03 | “PM” abbreviation, ambiguous role | Ask concise disambiguation before search | P1 | UX test |
| R04 | Blank/2-character/emoji-only role | Validation message and focus with intact input | P1 | Form test |
| R05 | 120-character role vs backend anonymous 90-char max | Aligned validation; no inexplicable 422 for valid UI input | P0 | API boundary |
| R06 | Accents and multilingual job titles | Unicode-safe validation/synonyms and language choice | P1 | Fixtures |
| R07 | Role autocomplete keyboard/touch | Accessible suggestions and correct committed value | P1 | iPhone/keyboard |
| R08 | Multiple target roles | Saved selection and distinct filters without accidental OR overload | P1 | State test |
| R09 | Role correction after first results | Reset cursor/rank and retain allowed account entitlement accurately | P1 | Browser |
| R10 | Career changer with adjacent skills | Transferability labelled partial, not invented direct experience | P0 | Expert fixture |

## E. Hard constraints and preferences

| ID | Scenario / trigger | Expected behavior and recovery | Priority | Required evidence |
|---|---|---|---|---|
| P01 | Spain-based full remote employee job | Country-based eligibility checked independently from remote flag | P0 | Real-source fixture |
| P02 | Remote US-only or UK-only job | Explicit Spain disqualification hard-blocked before rank | P0 | Hard negative |
| P03 | “Remote Europe” without allowed countries | Mark work eligibility unknown, not approved | P0 | Eligibility fixture |
| P04 | B2B-only user, employee-only listing | Explicitly exclude; preserve evidence quote | P0 | Negative fixture |
| P05 | B2B-only user, contract model unspecified | Show VERIFY, don't invent B2B support or silently exclude | P0 | Tri-state fixture |
| P06 | Employment + B2B both acceptable | Do not over-filter candidates with either verified model | P1 | Preference matrix |
| P07 | Relocation refused, office attendance | Hard block and explain which source statement caused it | P0 | Negative fixture |
| P08 | Annual EUR floor, listing USD/GBP | Never compare raw numeric value; show conversion uncertainty | P0 | Currency fixture |
| P09 | Hourly/monthly/day-rate, variable bonuses/equity | Normalize only provable units; otherwise unknown | P0 | Salary fixture |
| P10 | No salary published | Keep if other constraints pass; show unknown, no fake €0 | P1 | Results |
| P11 | Country of residence changed while account active | Re-evaluate prior results and saved searches without corrupting history | P1 | Cross-device |
| P12 | Work authorization missing/unknown | Ask only when material; unknown not implicitly pass or fail | P0 | UX+policy test |
| P13 | Multiple remote geographies or “EMEA excluding Spain” | Handle inclusion and exclusion sets, no naive substring logic | P0 | Geo fixture |
| P14 | Full-time/part-time/contract dates unknown | Show conditions explicitly, no unwanted hard reject | P2 | Normalization fixture |
| P15 | Preference changes during search | Cancel stale request and return only results matching latest version | P1 | Race test |

## F. Real providers, normalization and freshness

| ID | Scenario / trigger | Expected behavior and recovery | Priority | Required evidence |
|---|---|---|---|---|
| S01 | Ashby, Lever, Greenhouse, Workable and SmartRecruiters | Preserve original ATS URL + requisition identity | P0 | Per-source live+fixture |
| S02 | Remotive or aggregator duplicate of ATS | Prefer employer ATS canonical URL; one delivery/credit | P0 | Dedupe |
| S03 | Listing redirects to 404/closed/unpublished | Mark closed/quarantine and exclude before debit | P0 | Live recheck |
| S04 | URL 200 is generic careers homepage | Don't call it a verified open requisition | P0 | Live negative |
| S05 | Employer page requires login/captcha/geo | Open status unknown with verification action, not falsely open | P1 | Manual source |
| S06 | One provider times out, others return jobs | Partial response with provider health; don't claim exhaustive zero | P0 | Fault injection |
| S07 | All providers 429 or 503 | Explicit outage and retry/backoff; no quota debit | P0 | Fault injection |
| S08 | Empty but healthy source | Honest zero source candidates; separate zero eligible from unreachable | P0 | Provider fixture |
| S09 | Pagination across upstream job feeds | Fetch more than first 200 when necessary; dedupe across boundaries | P1 | Provider fixture |
| S10 | Employer changes title/location/status | Canonical version update, invalidate old eligibility/pack where needed | P0 | Mutable fixture |
| S11 | Same title company with two requisition IDs | Keep truly distinct positions; no over-deduplication | P0 | Canonical-ID test |
| S12 | Same requisition syndicated in five sources | One record, source history retained | P0 | Canonical-ID test |
| S13 | Job descriptions contain HTML / bad entities | Safe text normalization, source quote fidelity | P1 | HTML fixture |
| S14 | Provider only supports one locale or missing salary | No invented metadata; explicit unknown flags | P1 | Normalization |
| S15 | Large candidate volume or upstream latency | Bounded user wait, async snapshot, progressive accurate status | P1 | Performance E2E |
| S16 | Source unconfigured in staging | Show source unavailable / partial, not success-with-fabricated list | P0 | Staging config |

## G. Evidence, scoring and relevance

| ID | Scenario / trigger | Expected behavior and recovery | Priority | Required evidence |
|---|---|---|---|---|
| M01 | No CV role-only results | Clearly “role relevance only; CV fit not assessed” | P0 | Browser |
| M02 | Must-have supported with source evidence | Exact CV span and requirement excerpt shown | P0 | Evidence fixture |
| M03 | Missing CV proof, possible actual skill | Say unsupported evidence, not user unqualified | P0 | Copy review |
| M04 | “Leadership” generic keyword in both texts | No falsely verified managerial tenure | P0 | Negative fixture |
| M05 | Partial transferable skill | Separate partial vs supported vs unknown | P0 | Expert judgement |
| M06 | Requirement changed in employer listing | Invalidate outdated candidate alignment and cached pack | P0 | Version test |
| M07 | Inferred years/domain, school or citizenship | Never invent facts from adjacent CV clues | P0 | Negative fixture |
| M08 | Counterexample CV has contradictory dates/roles | Show unresolved and ask correction rather than confidently rank | P0 | Fixture |
| M09 | Ranking 25 contrasting jobs | Stable top ten with evaluation of precision@10 | P0 | Expert fixture |
| M10 | Near-identical positions from one employer | At most two in top ten unless supply low | P1 | Ranking fixture |
| M11 | Stale but title-perfect vs newer proven fit | Rank evidence/freshness, not just lexical overlap | P0 | Ranking fixture |
| M12 | Uncalibrated percentage/probability | Do not display numeric hiring/fit probability | P0 | UI assertion |
| M13 | Manual override to pursue weak fit | Allowed with transparent risk and recorded reason, not fake good fit | P1 | Decision test |
| M14 | Remote/geography unknown but strong evidence | Keep visible as VERIFY_FIRST, never “eligible” | P0 | Policy fixture |

## H. Results, history and pagination

| ID | Scenario / trigger | Expected behavior and recovery | Priority | Required evidence |
|---|---|---|---|---|
| J01 | Zero valid jobs | Empty state with source status, broaden filter, retry, retained credits | P0 | Browser |
| J02 | Only 4 legitimate matches | Exactly 4, not 10 filler cards | P0 | Live fixture |
| J03 | Results include 10+ / paid pagination | 20 page size default, cursor and accessible Load more | P0 | 120-job fixture |
| J04 | Sort newest vs best fit | Deterministic and explains verified dates; cursor reset | P1 | Sorting fixture |
| J05 | Change geography / salary filter | Reload with latest constraints, no stale duplicate or hidden leak | P0 | Browser |
| J06 | Refresh results from same snapshot | Never debit same vacancy twice | P0 | Quota regression |
| J07 | Duplicate appears across two pages | No duplicate, stable resume/back and selection | P0 | Pagination fixture |
| J08 | Cursor expires while browsing | Clear refresh action; save scroll/context or selection | P1 | Expiry test |
| J09 | Previously applied job reappears | Flag or exclude consistently with override rule | P0 | History fixture |
| J10 | Prior employer rejection on different company spelling | Canonical alias identification, not exact string only | P0 | History fixture |
| J11 | User saved/ignored/skipped role | Status visible and persists, user can undo | P1 | State E2E |
| J12 | Original employer URL is unsafe/broken | Disable with explanation and safe fallback, never silent navigation | P0 | Security + URL |
| J13 | Results loading 30 seconds | Accurate progress, abort/cancel, no indefinite spinner | P1 | Slow-network test |

## I. Identity and user continuity

| ID | Scenario / trigger | Expected behavior and recovery | Priority | Required evidence |
|---|---|---|---|---|
| A01 | Guest receives results | No forced login/payment or Telegram wall before first value | P0 | Browser |
| A02 | Telegram provider missing | No dead CTA; clear beta limitation and another operational option | P0 | Staging test |
| A03 | Telegram OTP correct/incorrect/expired | Secure correct session, 5 attempts limit, recovery and accessible errors | P0 | Live + negative |
| A04 | Telegram opens new app on iPhone | Return to same browser challenge and desired post-login intent | P0 | Actual iPhone |
| A05 | Email SMTP unconfigured | Disabled and labelled, not pretend sent | P0 | Config+browser |
| A06 | Email link valid/expired/reused | One-time sign-in with correct redirect, no token leak | P0 | Auth tests |
| A07 | Session expires during CV edit | Preserve unsaved edits safely; sign in then resume | P0 | E2E |
| A08 | /me returns 503, timeout or network down | Do not show logged-out state or imply loss of saved data | P0 | Fault injection |
| A09 | Logout while edit/download pending | Revoke session, clear sensitive transient UI and prevent unauthorized actions | P0 | Cross-tab E2E |
| A10 | Two tabs same user / separate browsers | Consistent preferences, history and delivery counting | P0 | Race tests |
| A11 | Telegram + email are same person | No implicit merge or silent duplicate identity, verified optional linking | P1 | Identity model |
| A12 | Login to wrong account after guest CV | Never attach guest CV automatically; require account confirmation | P0 | Two-account test |
| A13 | Cookie/storage blocking/private Safari | Graceful sign-in failure and recovery; no loop | P1 | iPhone Safari |
| A14 | Account deleted or revoked | No orphaned sessions, CV, pack or subscription data | P0 | Delete cascade |

## K. Entitlement, plans and payment boundaries

| ID | Scenario / trigger | Expected behavior and recovery | Priority | Required evidence |
|---|---|---|---|---|
| Q01 | Free 10 across 3 searches | Exactly ten distinct qualifying delivered records lifetime | P0 | DB transaction |
| Q02 | 11th candidate after quota exhausted | Never deliver new credit-consuming job; previously delivered still visible | P0 | Free E2E |
| Q03 | Duplicate/closed/stale/hard-ineligible listing | No entitlement decrement | P0 | DB fixture |
| Q04 | Two devices request 10th simultaneously | Atomic unique ledger; count never 11 | P0 | Concurrency test |
| Q05 | Anonymous repeated previews / IP changes | Explicit separate preview policy, no false cross-device lifetime promise | P1 | Policy/E2E |
| Q06 | Paid 120 matching jobs across 7 pages | All available unique jobs retrievable; no product quota | P0 | 120+ fixture |
| Q07 | Paid only 4 matching jobs | Exactly four, no made-up listings | P0 | Fixture |
| Q08 | Unrelated active Telegram Stars SKU | Must not grant unlimited subscriber discovery | P0 | Entitlement test |
| Q09 | Payment past_due / canceled / expired | New delivery falls back to free rules; paid history not erased | P0 | Webhook test future |
| Q10 | Upgrade during active search | Server-authoritative entitlement updated consistently; no client paid flag | P0 | Entitlement race |
| Q11 | Trial renewal and card collection not configured | No fake checkout, countdown or auto-debit copy | P0 | Public copy audit |
| Q12 | Provider webhook repeated/out of order | Idempotent, signed, audit status; never double-charge/unlock | P0 | Future billing |

## L. Saved searches and autopilot

| ID | Scenario / trigger | Expected behavior and recovery | Priority | Required evidence |
|---|---|---|---|---|
| T01 | Save first role preference | Restore from server after logout/device change | P0 | Account E2E |
| T02 | Try fourth search profile | Explain actual plan limit before submit or remove undocumented cap | P1 | API 409 + UX |
| T03 | Rename/edit/pause/delete search | Dedicated controls, preserved history, clear states | P1 | Persistence test |
| T04 | Search reruns after 2-minute throttle | Explain cooldown and existing results; no mysterious 429 | P1 | Browser |
| T05 | Background worker and manual discover at same time | One canonical delivery, idempotent quota + notifications | P0 | Race test |
| T06 | No connectors set | Role-only first value still works; autopilot opt-in later | P0 | Onboarding E2E |
| T07 | Saved-search notification on new matching vacancy | Notify once per canonical ID and only with consent | P1 | Scheduler fixture |
| T08 | Source status changes on background rerun | Show as new/updated/expired without losing previous action history | P1 | Lifecycle test |
| T09 | Switch result scope to history-only | Review applied/rejected without consuming free credit | P1 | UX test |

## N. Job review and truthful application pack

| ID | Scenario / trigger | Expected behavior and recovery | Priority | Required evidence |
|---|---|---|---|---|
| F01 | Open real job detail | Requirements, exact source quotes, hard unknowns and recommended action visible | P0 | Human E2E |
| F02 | Job detail source changed since scan | Status stale; recalculate or warn before use | P0 | Version test |
| F03 | Open detail for previously submitted job | Read-only review; no hidden re-ingestion or counter increment | P0 | API side-effect test |
| F04 | Build draft with self-reported claim | Label unverified; never promote without provenance | P0 | Claim gate fixture |
| F05 | Claim missing metric/date/ownership | Ask edit or omit; no generated invention | P0 | Content regression |
| F06 | Copy has source-backed approved evidence | Apply only selected facts and track what was changed | P0 | Diff regression |
| F07 | Job-specific cover letter + screening answers | User review, unanswered legal/EEO questions stay unanswered | P0 | Fixture + UX |
| F08 | Tailored CV export PDF/DOCX | Actual truthful file and preview if implemented; never mislabel .md pack | P0 | Output contract |
| F09 | Edit positioning after export | New version, explicit re-export; stale download not silently current | P1 | Version test |
| F10 | Delete CV used in an old pack | Invalidate/remove derived claims; don't leak original CV into exports | P0 | Deletion regression |
| F11 | Two tabs edit same pack | Version conflict resolution, no silent overwrite | P1 | Optimistic locking |
| F12 | Long accents/Cyrillic, lists, emojis | Correct editor, escaping and exported filename/content | P1 | Unicode test |
| F13 | Open pack before CV confirmed | Honest role-only pack state, no “verified” claim | P0 | Negative test |

## O. Employer handoff and application lifecycle

| ID | Scenario / trigger | Expected behavior and recovery | Priority | Required evidence |
|---|---|---|---|---|
| H01 | User clicks apply without reviewed pack | Explicit review gate; no external navigation/submit claim | P0 | Browser |
| H02 | Review approved but URL expired | Block/verify and preserve draft, no erroneous submitted state | P0 | Live URL |
| H03 | Popup blocked on Safari | Provide direct employer link/copy; never claim form opened | P0 | Browser |
| H04 | Employer requires external login / iframe restrictions | Honest manual handoff; preserve source CV/pack for user | P1 | Real source |
| H05 | Link opens new tab then user returns | Show “Handoff opened”, not “Applied”; accessible return path | P0 | Browser |
| H06 | User abandons or fails submission | Record not submitted / unknown, allow later retry | P0 | State test |
| H07 | User actually submits authorized test form | Only explicit confirmation marks user-reported submitted | P0 | Safe E2E |
| H08 | Double-click confirm or reload | Idempotent single submission record | P0 | Race test |
| H09 | Employer form changes question after prep | Show needs-revision; do not send invented old answers | P1 | Fixture |
| H10 | Job submitted previously from other source | History flag, override distinct requisition only | P0 | Canonical employer |

## P. Tracking, CRM-like history and analytics

| ID | Scenario / trigger | Expected behavior and recovery | Priority | Required evidence |
|---|---|---|---|---|
| K01 | User marks awaiting / interview / rejected / offer | Valid state transition and timestamp persists after reload | P0 | E2E |
| K02 | Outcome edit on job never submitted | Blocked with explanation and correct next step | P1 | API test |
| K03 | Recruiter reply arrives via connected Gmail | Link to correct employer/requisition or ask user to resolve ambiguity | P1 | Matching fixture |
| K04 | Same recruiter email refers to two roles | Never attribute blindly; confidence and manual choice | P0 | Negative fixture |
| K05 | Rejected employer changes brand/corporate name | Canonical employer alias; no unsafe blanket exclusion | P1 | History fixture |
| K06 | Applications initiated outside RoleHint | Allow manually recorded imported status with provenance | P1 | Workflow UX |
| K07 | Withdrawn/ghosted/offer declined statuses | Specify legal transitions; don't force user into inaccurate option | P2 | State spec |
| K08 | Funnel conversion counts | Distinct searches → valid jobs → review → prepared → handed off → confirmed submission → observed outcome | P1 | Analytics invariant |
| K09 | Source/channel effectiveness | Capture origin and funnel with denominator and date, no fake ROI/probability | P1 | Analytics fixture |
| K10 | User exports/deletes history | Private export, correct deletion and event linkage | P0 | Privacy test |

## U. Connected integrations, Mini App and notifications

| ID | Scenario / trigger | Expected behavior and recovery | Priority | Required evidence |
|---|---|---|---|---|
| U01 | Connect Google with permission denied | Skip without breaking first-value flow; no phantom connected badge | P1 | OAuth fault |
| U02 | Google refresh token revoked/expired | Prompt reconnect, retain history, no leaked tokens | P0 | Integration test |
| U03 | GitHub account/profile evidence imported | Repo ownership self-reported/linked, not proof of job qualification | P1 | Evidence audit |
| U04 | Gmail notification duplicated/out-of-order | Idempotent processing; don't duplicate employer response | P0 | Queue fixture |
| U05 | Telegram bot down while website works | No broken alerts/sign-in promises; role-only discovery available | P0 | Outage E2E |
| U06 | User unsubscribes from alerts | Stop pushes, preserve saved jobs, explicit channel permissions | P1 | Consent test |
| U07 | Worker sync reports zero while live sources down | Source unavailable state, not absence of demand | P0 | Outage fixture |
| U08 | Mini App user opens web version | No automatic history merge; explicit identity link or warning | P1 | Cross-channel test |
| U09 | Autopilot pace options / background rate | Do not silently overwrite user policy or imply success counts | P1 | Scheduler/UI contract |

## V. Security, privacy, accessibility and release gates

| ID | Scenario / trigger | Expected behavior and recovery | Priority | Required evidence |
|---|---|---|---|---|
| X01 | Foreign user's CV/job ID in URL | 404/403, no cross-user profile/pack/history | P0 | IDOR matrix |
| X02 | Anonymous CV in GET/query/analytics/logs | No raw/private CV data in URL, provider request or log | P0 | Network+log |
| X03 | SSRF via employer/source URL | Safe HTTPS destination policy, redirect/IP checks and timeouts | P0 | Security |
| X04 | Malformed JSON/file upload or 10 parallel uploads | Bounded memory/CPU, rate limit and error recovery | P0 | Load/security |
| X05 | Long Unicode/XSS in job description or user CV | Escaped text, CSP, no script execution | P0 | XSS fixture |
| X06 | Auth 401 vs 403 vs 429 vs 500/offline | Distinct actionable messages; safe retry; preserve work | P0 | Failure injection |
| X07 | Screen readers, VoiceOver, tab and Escape | Labels, roles, focus transfers and status announce correctly | P0 | Manual a11y |
| X08 | 320/375/390/430/768/1440 widths & 200%-400% zoom | No clipping, overflow or hidden critical actions | P0 | Visual E2E |
| X09 | Reduced motion/low bandwidth | Content readable and actionable without animations | P1 | Device |
| X10 | Safari file picker + return from Telegram popup | Flow resumes, no lost pending state or broken focus | P0 | iPhone E2E |
| X11 | Webapp change deployed to wrong service/branch | Immutable SHA recorded; staging/prod separation guaranteed | P0 | Release check |
| X12 | Staging restart loses SQLite state | Dedicated persisted test volume or deliberate ephemeral reset, no false cross-device claims | P0 | Restart drill |
| X13 | Main/staging browser tests expect removed UI | CI tests current semantics; old demo assertions retired | P0 | CI QA |
| X14 | Production rollback following schema migration | Backward-compatible migration, backup restore, no jobs/quota loss | P0 | Rollback drill |
| X15 | Logs of failures include secrets/PII | Redacted traces, retention defined and access audited | P0 | Log review |
| X16 | New feature behind unavailable integration | Hide/degrade without blocking core CV/role-to-jobs path | P1 | Feature toggle |
| X17 | Payment data + webhooks once authorized | Signed idempotent backend events; no raw card storage | P0 | Future release gate |
| X18 | Accessibility copy statuses only in color | Text/icon+color, WCAG AA on every contrast mode | P1 | Accessibility audit |

## Critical cross-feature journeys (must pass as uninterrupted E2E)

1. **CV-first:** landing → privacy → parse → correct/confirm role → supplied geography/B2B → real sourced list → job evidence/unknowns → optional save → restore after login. Inject scanned CV, slow network, discard, invalid session.
2. **Role-only:** direct role → results (no CV fit claim) → explain eligibility unknown → original listing → optional later CV → rerank with approval. Inject ambiguous abbreviation, source outage and duplicate.
3. **Free exhaustion:** 3 searches / 2 devices / multiple tabs → 10 unique qualifying deliveries total; one duplicate, stale and blocked never charged; 11th blocked with history intact.
4. **Paid pagination:** active SKU-specific entitlement → 120 canonical fixture jobs in 7+ pages with stable cursor → cancel/expire → saved history preserved and new delivery obeys free rule. No live billing until separately approved.
5. **Application:** real ATS job → actual requirement snippets and user evidence → truthful editable pack → export compares to preview → explicit approval → external handoff → authorized form submit → user confirmation → distinct status history. Inject popup block and changed job requirements.
6. **Account recovery:** email or Telegram sign-in (only configured method offered) → edited CV/roles/saved jobs → logout → second device resume → delete → no remnants/foreign data. Inject token expiry, wrong code, network and 503.
7. **Operations:** one ATS/provider 429 with others healthy → partial results + status; all down → outage not zero; background worker collides with manual search → one canonical job/delivery; restart staging and production rollback without data loss.
8. **Research audit:** moderated task observation for first useful job, time-on-task, eligibility trust, wrong-fit frustration, proof editing, and return rate; compare against actual manual job-search baseline without forecasting conversion uplift as fact.

## Acceptance logging template

ID: __ · Owner: __ · Priority: __ · Environment: __ · Full deployed SHA: __ · Device/OS/browser: __ · Persona/fixture: __ · Preconditions: __ · Steps: __ · Expected: __ · Observed: __ · Status PASS/FAIL/BLOCKED/UNTESTED: __ · Screenshot/video or redacted log: __ · Issue link: __ · Fix SHA: __ · Regression: __ · Founder sign-off: __.

**Release prohibition:** do not merge/deploy the unfinished staging web app to production based on this matrix, green health check or fixture-only tests. Each P0 requires full evidence for the promised tier, including iPhone Safari, real-source validation and owner approval.
