# Architecture

## Source map

The backend uses **Python/FastAPI**. Its modules have different responsibilities:

| Path | Responsibility |
| --- | --- |
| `backend/app/main.py` | Application composition and legacy routes (pending gradual extraction) |
| `backend/app/http_boundary.py` | HTTP entry allowlist, separate from user authentication |
| `backend/app/web_identity.py` | Web login, sessions and browser identity |
| `backend/app/services/product_state/` | User-scoped product state |
| `backend/app/services/job_search/` | ATS provider adapters |
| `backend/app/services/auto_match/` | Matching and constraint analysis |
| `tests/test_http_boundary.py` | Unit check for path boundaries |
| `tests/test_public_beta.py` | Signed-in and anonymous API regressions |

The Evidence Inbox feature PR has additional OAuth/MCP endpoints. Its route
contracts must be reconciled with the guard before integration. The current
default-deny middleware does not itself validate identities on allowed paths.

## Product objects

```text
Vacancy
  └── Requirement[]
        └── EvidenceMatch[]
              ├── verified
              ├── needs_review
              └── missing

verified → ProofCard[]
needs_review → HumanReviewQueue
missing → GapMap
```

## Why the review queue exists

Career evidence is unusually easy for generative systems to overstate.

The dangerous failure is not a malformed sentence.

It is a plausible-sounding claim that subtly upgrades:

- team outcome → personal outcome;
- adjacent experience → direct experience;
- modeled impact → measured result;
- design contribution → engineering ownership.

So ambiguity is a product state, not a prompt failure.

## Replaceable adapters

The current implementation is deliberately deterministic.

Production adapters could replace:

- parser → LLM structured extraction;
- retrieval → embeddings / hybrid search;
- matcher → LLM rubric + deterministic guardrails.

The contracts and human-review boundary should remain.
