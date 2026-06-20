## Proposed Design Outline

### Goals
- Item 1: make the `/implement` vs `/design` sentinel-probe asymmetry explicitly non-contradictory in the implement NEVER wording.
- Item 2: remove the duplicated self-review tally logic behind one shared `python/` helper used by both callers.
- Item 3: guarantee every secret-scrub/redact path fails closed on scrub error or secret survival, locked by regression tests.

### Non-goals
- No change to `code-review-tally.json` schema or to either caller's output record shape.
- No change to success-case rotation warnings (a secret found AND successfully scrubbed stays a warning).
- No full rewrite of the NEVER lists; no refactor of unrelated scrub/redact logic.

### Approach sketch
- Item 1: add a short cross-reference clause to implement SKILL.md NEVER #8; pin the clause in `scripts/test-implement-anti-polling-rule.sh`.
- Item 2: new `python/self_review_tally.py` owns the drift-prone constants (`mode==self-review`, `accepted_count`/`rejected_count`, `SELF_REVIEW_*` prefixes); both callers import it; `fluff-analysis.py` gains a guarded `sys.path` bootstrap.
- Item 3: audit every scrub/redact callsite; convert any genuine warn-on-error gap to abort; add fail-closed parity tests; update `SECURITY.md`.

### Surfaces in scope
- `skills/implement/SKILL.md`, `scripts/test-implement-anti-polling-rule.{sh,md}`
- `python/self_review_tally.py` (+ test), `python/audit_runs.py`, `skills/fluff-analysis/scripts/fluff-analysis.py`
- `python/run_logs.py`, `python/design_publish.py`, `python/design_log_publish_flow.py` (+ tests), `SECURITY.md`

### Open questions
- None.
