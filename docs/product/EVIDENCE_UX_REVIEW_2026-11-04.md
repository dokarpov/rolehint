# RoleHint Evidence Inbox — UX review and progressive disclosure
**4 November 2026 · staging scope only · PR #13 · production unchanged**

## What was observed

Reviewed live staging at `/webapp/evidence.html`, the user-facing markup, source/review API, current Playwright fixture coverage, and the approved product constraints. This is an expert heuristic audit, not a moderated user study or real iPhone Safari acceptance.

The **underlying usability defect** was the lack of a dominant task: a very large marketing hero, disabled email sign-in, an entire multistep evidence form, a review/empty column, and AI connector instructions were simultaneously presented. On a phone that produced long vertical reading and a false impression that cloud capture was already ready.

### Problems by priority

| Priority | Original issue | User impact | Decision |
|---|---|---|---|
| P0 | Full source and claim form shown before source selected | No clear first action, too much cognitive load | Show only **Step 1: source** until explicit Continue |
| P0 | Failed/unconfigured account login shown before users can start | First-screen dead end, discourages exploration | Explain account restrictions **only at save**; offer a private local draft |
| P0 | Connector setup looked like a main task even when SMTP unavailable | False sense of readiness | Hide under **Connections and permissions**, shown only when signed in |
| P1 | Optional source kind and negative evidence limits shown alongside essentials | Excessive fields and apparent validation burden | Collapse as **Source details and limitations** |
| P1 | Capture and review occupy equal priority even when inbox is empty | Long scroll; review appears usable for guests | Show review only to authenticated users; concise empty state |
| P1 | Two save CTAs offered equal prominence | Confusing and conflicting action | Signed-in: **Save for review**; offline: **Download private draft** |
| P1 | Long technical, privacy and verification explanations repeated | Displaces real task | Short contextual helper by action; detailed explanation only as needed |
| P1 | Review card exposes long source and editing controls | Poor scanning with many items | Card shows claim/status/source; actions in **View source and actions** |
| P2 | Browser regression did not assert form is progressively disclosed | Cosmetic QA missed overload | Assert phase transitions, optional section closure, guest/online CTA states |
| P2 | Repeated status messages and technical terms | Confused state feedback | Separate short inline statuses for source, saving, and reviews |

## Implemented interaction contract

**Screen 1 (default):** text-only brand, compact purpose, visual 1/2/3 progress indicator, **Add a source**. Text passage and optional text file picker are visible. Continue is disabled until the passage has at least eight non-whitespace characters. No claim/source metadata, sign-in wall, empty inbox or connector guide is shown to a guest. This intentionally takes one user action to advance; files are previewed before advancing.

**Step 2 (after Continue):** source collapses into one short editable preview. Show only Project, Your contribution, and Where is this from? Three fields; no forced source-type/limit configuration. **Source details and limitations (optional)** remains collapsed by default; source kind is preserved for imported files.

**Action:** signed-in user saves to a private needs-review inbox, without marking AI-generated statements verified. Guest with configured email can sign in or export. Guest without email sees one primary **Download private draft** CTA and a short contextual staging warning, not a fake cloud save option. Local JSON export is explicit and portable; importing restores a form for review but never uploads automatically.

**Step 3:** after saving, review becomes the active progress state; account-owned items are listed by claim/status/source. Full excerpt, editing, approval, rejection and deletion require opening the item's disclosure. No entries means one short empty line, not a blank scrollable panel.

**Connections:** advanced account setting, collapsed by default. The private MCP URL and revocation are available only after sign-in. The backend's source, OAuth scopes, token/cookie ownership and FTS semantics are unchanged.

## Scenario and corner-case acceptance

- **New visitor / no SMTP:** source step remains usable; no dead-end sign-in above the task; offline draft download works, with explicit privacy warning.
- **Authorized user / no items:** one prominent capture task, concise empty review below, no fake/demo evidence.
- **Authorized user / review backlog:** claim/status/source visible at glance, details optional, approval self-reported only.
- **Duplicate source:** backend returns existing item; user sees a duplicate confirmation, no phantom new candidate.
- **File import:** supported TXT/MD/JSON/CSV up to 1 MB, previews only first 8,000 chars with warning, does not upload; local `rolehint-evidence-draft` JSON restores its original fields.
- **Invalid / oversized source:** file error stays local; Continue disabled until sufficient excerpt; hidden claim step cannot be submitted prematurely.
- **Poor connectivity:** network failure must preserve filled fields and show inline error. No silent retry of evidence approval/deletion.
- **OAuth connection:** existing signed-in, scoped consent remains unchanged. No claim of functional cloud sync if actual account authorization was not end-to-end tested.
- **Mobile/keyboard:** no horizontal overflow at 320/375/390/430/768/1440 px; visible labels/focus, editable source summary, optional details accessible by keyboard, WebKit approximation.
- **Privacy:** raw excerpts stay user-owned; no assistant “verification” claim, no automatic file scanning, no upload on local import.
- **Known open gaps:** real iPhone Safari/VoiceOver, working SMTP, real Claude/ChatGPT E2E, real storage restore, user data deletion policy, PDF/image evidence, validation with users, and inter-page return after sign-in. These remain separate release gates.

## Release decision

Ship this UX only to the existing `rolehint-staging` service after the updated backend + browser regressions pass at the **same exact source SHA**. Do not modify production, approve public launch, or claim real AI authorization simply because the unauthenticated OAuth/MCP health checks pass.
