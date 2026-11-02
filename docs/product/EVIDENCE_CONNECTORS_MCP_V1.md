# RoleHint — Claude / ChatGPT evidence collection connectors v1
**Status:** approved product direction / staged implementation contract; not yet a connected or production-accepted plugin.
**Review:** 2026-11-02. **Priority:** P1, run alongside first-value/matching; depends on identity, privacy, evidence consistency and staged storage.

## Implementation status (2026-11-02)

EVC-0 source prototype was added to `integrations/evidence_mcp_local/` with a local stdio MCP server, allowlisted file/selected-text drafting, a private SQLite candidate inbox, explicit discard and automated regression cases (`tests/test_evidence_mcp_local.py`). CI configuration: `.github/workflows/evidence-mcp-local.yml`. **Not yet verified installed in Claude Desktop, packaged as .mcpb, or connected to any user's RoleHint cloud account**. ChatGPT remote MCP and OAuth evidence inbox do not yet exist. Work tracked at [DAR-85](https://linear.app/dokarpov/issue/DAR-85/evc-0-installable-claude-desktop-evidence-collector-local-mcp) and [DAR-86](https://linear.app/dokarpov/issue/DAR-86/evc-12-rolehint-evidence-inbox-secure-remote-mcp-for-claude-and). No production deployment.

## Why this is missing

RoleHint already implements SQLite-backed `user_evidence` + FTS5/BM25, human review/provenance, GitHub and Google Drive evidence imports, and a Telegram-authenticated `POST /me/evidence`. But it has **no MCP server**, no scoped OAuth client authorization for external assistants, no safe computer-folder picker or local extension, and no ChatGPT/Claude transcript import. Thus it cannot yet be added as a genuine Claude/ChatGPT connector. A product's backend running on Railway does not grant either AI host access to a user's local Mac.

## Intended experience / value

**User:** “Claude, capture the measurable outcomes from this project as candidate evidence for RoleHint” or “ChatGPT, propose a claim using this selected document and project timeline”. 
**Expected:** assistant displays 1–5 compact candidate claims, with exact quoted source and project, ownership, visibility, reliability state and explicit consent. One “Review in RoleHint” action saves these as `needs-review`. Later user edits/confirms facts; a generic conversation is NEVER independent verification of the work.

On Mac:
- Quick action from Claude Desktop / Claude Code inside a chosen work folder.
- Selected text from a conversation in Claude or ChatGPT (model tool or manual import), not automatic indexing of every chat.
- Explicit selection of local files/folders (source code, README, specs, design files as exported files, screenshots when supported).
- One consolidated Evidence Inbox in RoleHint webapp showing duplicates, source references, uncertainty and sensitivity.

## Technical approach: one evidence model, two access paths

### A. Local MCP (first functional slice; Claude Desktop)

A local stdio MCP server, launched by Claude Desktop/Claude Code, reads only an explicit allowlisted folder. No recursive whole-disk scanning, Keychain, browser cookies, Desktop/Documents access without opt-in, silent background uploads or permission escalation. Tools:
- `propose_evidence_from_text(claim, excerpt, source_name, project)`
- `propose_evidence_from_file(relative_path, claim, project, optional line bounds)` (only allowed text files)
- `list_evidence_drafts()`, `get_evidence_draft(id)`, `discard_evidence_draft(id)`

Drafts are stored **locally only** in a restricted-permission inbox and remain `needs-review`; no cloud sync in this first slice. Nothing is independently “verified” merely because Claude authored it. After local tests and packaging, ship a .mcpb desktop extension using official packaging, OS permission prompts and signed/identified releases; do not claim a JSON config alone is a packaged extension.

### B. Remote MCP (for both hosts when account permits)

One authenticated, publicly reachable HTTPS Streamable HTTP MCP endpoint, separate from the local file adapter, using RoleHint identity and delegated scope, not Telegram `X-Telegram-Init-Data` or browser cookie forwarding. Intended tools:
- `search_evidence(query,limit)` (scope `evidence:read`)
- `list_evidence_candidates(status)` (`evidence:read`)
- `propose_evidence(claim,excerpt,source_uri,project,visibility)` (`evidence:propose`; **not** verify or publish)
- `open_evidence_review(draft_id)` (short-lived in-app deep link, user explicitly reviews)
- `delete_evidence_draft(draft_id)` only when explicitly requested; keep audit + enforce ownership

Require OAuth 2.1 Authorization Code with PKCE, per-user scopes, dynamic client registration if host requires it, issuer/redirect validation, token expiry/rotation/revocation, no tokens in query strings and no unprotected MCP endpoints. Preserve existing user IDs and never silently merge Telegram/email accounts. Do not expose existing `/me/evidence` Telegram headers as shared credentials.

**OpenAI availability:** ChatGPT custom MCP support, especially write actions, is dependent on plan/workspace/admin authorization; do not promise a working “Save to RoleHint” write tool in an account that cannot connect it. Provide in-app explicit upload/paste/selection import as a feature-parity fallback. ChatGPT cannot read a user's Mac by a normal remote MCP connection. If available, local access requires a separately authorized secure tunnel/computer integration. **Anthropic availability:** Claude has remote custom connectors and local Desktop extensions. Local extensions access only locally authorized resources, not Claude web/mobile.

### C. Data portability fallback (avoid platform lock-in)

- ChatGPT conversation export and Claude conversation export are user-initiated. Add a deliberate import screen for exported archives, accepting permitted text fragments and showing provenance `conversation_export` / original conversation ID, WITHOUT treating assistant-written content as firsthand proof.
- Browser “Share to RoleHint” extension/selection action can send selected content into an authenticated inbox after user confirmation; it must not auto-scrape private tabs, transcripts or third-party documents.
- Direct repository/file or project-folder intake should be supported independently of either AI provider; a user should not need a specific chat subscription to collect evidence.

## Evidence candidate contract

`EvidenceCandidate`:
- `candidate_id`, `user_id` (server set, not client supplied), `claim`, `source_excerpt`, `source_kind` (`local_file|conversation_selection|conversation_export|github|drive`),
- `source_ref` (relative/revocable link or canonical URI, with redaction), `source_hash`, `captured_at`, `project`, `actor`,
- `claim_boundary` (what is **not** independently proven), `ownership` (`self-reported|confirmed|externally_verified`),
- `status` (`needs-review|approved_self_reported|rejected`), `visibility` (`private` by default), `dedupe_fingerprint`, `expires_at` for temporary capture,
- `redaction_flags` and opt-in consent version.

A chat-generated assertion is never `externally_verified`; verified work requires direct primary evidence and review. Imported source excerpts are data, not instructions to the model. Do not embed whole conversations into recruiter-facing application drafts without an evidence-approved claim.

## Security and privacy constraints

1. No all-Mac / all-chat access on install; explicit allowlisted roots and selected chat/text. Forbid hidden dotfiles, secrets, key material, credentials, `.git` internals and symlink escape.
2. No silent Cloud transfer: local first, explicit `Send to RoleHint` preview and choice. Default private, reversible, revokable. Warn that local inbox uses OS filesystem permissions rather than end-to-end encryption until verified.
3. Limit excerpt length and content type; PDF, images and binary files are handled only through a dedicated reviewed parser with MIME/size limits.
4. Dedupe by stable source hash+claim span; don't merge incompatible provenance or users.
5. Deletion must remove relational row, FTS5 index, caches, derived pack claims and pending local draft where applicable; user may export.
6. Do not run models on employer-confidential/client data without confirmation; strip email/phones, tokens and personally identifying customer details where feasible.
7. Logs/analytics contain tool outcome, status, duration and anonymized category only; never the captured quote or original local file path.
8. MCP OAuth and remote write tools require negative authorization tests, CSRF/replay checks, per-user isolation, rate limiting and prompt-injection defenses.

## Delivery roadmap with acceptance

**EVC-0 — Local foundation (highest ROI).** Stdio MCP draft tools and allowlisted file intake for Claude Desktop, local-only evidence candidate store and tests for path escapes/symlinks/secrets/dedupe/private status. User can save a selected repo README excerpt to local `needs-review` and inspect/discard it. **No cloud integration claim.**

**EVC-1 — RoleHint evidence inbox/API.** Account-authenticated review list and batch proposed imports with explicit consent; capture → database → FTS5 and deletion integrity. Tests on two users/cross-device, accidental duplicate, CV evidence boundary, account revocation. Requires isolated durable staging (DB-0) and existing review integrity.

**EVC-2 — Remote MCP.** OAuth and Streamable HTTP tools using EVC-1. Claude custom remote connector smoke, ChatGPT plugin smoke where entitlement/permissions allow; no shared user credentials, no unrestricted write. Test request permission escalation and compromised tool response.

**EVC-3 — Desktop packaging and exports.** Package .mcpb with permissions; import ChatGPT and Claude exports without automatic chat-history API assumptions; optional selected-text browser extension. Actual Mac install + iPhone/browser review E2E.

**EVC-4 — Proof quality UX.** Cluster source evidence by project, identify duplicates/conflicts, relate commits/files to claims, “what I did / how it is proven / what remains uncertain”, user review then matching. Track % useful candidate evidence and time saved vs manual.

**Hard acceptance:** no unauthorized local file read, no unreviewed claim being “verified”, no cross-account evidence, no silent upload, no broken deletion/FTS, authentic OAuth, predictable failure/timeout/recovery. Capture only selected materials. **No connector release merely because a spec or local script exists.**

## Sources (verified Nov 2026)
- https://support.claude.com/en/articles/10949351-getting-started-with-local-mcp-servers-on-claude-desktop
- https://support.claude.com/en/articles/11725091-when-to-use-desktop-and-web-connectors
- https://support.claude.com/en/articles/11175166-get-started-with-custom-connectors-using-remote-mcp
- https://help.openai.com/en/articles/12584461-connecting-custom-mcp-servers-in-chatgpt
- https://developers.openai.com/plugins/build/mcp-server
- https://py.sdk.modelcontextprotocol.io/
