## Proposed Design Outline

### Goals
- Maintain a per-invocation `findings-ledger.tsv` of every prior-round suggestion (accepted / neutral / rejected / oos).
- Reviewers read the ledger and skip duplicates; judges read it and short-circuit duplicates to NO.
- Build it deterministically in the tally path: a plain file append, no agent, no LLM, no extra barrier.

### Non-goals
- v2 embedding auto-suppression at aggregation (deferred to a follow-up; unresolved threshold + location-changed guard).
- Human-readable markdown ledger (TSV only).
- Cross-invocation persistence.
- Committing the ledger to git, or any change to the per-round `findings-classification.tsv` flush.

### Approach sketch
- New shared writer (e.g. `python/findings_ledger.py`) projects each round's classified findings into an ephemeral, anonymized `findings-ledger.tsv` at the review tmpdir root.
- Call the writer at end of each round inside both tally paths: `review_tally.py` (code review) and `plan_review_tally.py` (plan review).
- Inject the ledger path into reviewer and judge prompts in `python/rendering.py` (code-review `render_specialist` / `render_reviewer` / `render_voter`, plan-review `render_plan_review` and the plan-review voter renderer); inject only from round 2 onward.
- Duplicate policy: rejected + neutral suppress (neutral behind one knob); accepted annotated, not suppressed; oos suppress re-raise.
- Ledger is ephemeral: never committed. Per-round `findings-classification.tsv` (with authorship) stays the committed record, unchanged. Exclude the ledger basename from `/design` log-publish.

### Surfaces in scope
- `python/findings_ledger.py` (new), `python/review_tally.py`, `python/plan_review_tally.py`, `python/rendering.py`, `python/design_log_publish_flow.py` (one exclusion), tests.

### Open questions
- Exact plan-review voter renderer to inject (confirm in `python/rendering.py` / `plan_review_round.py`).
- Neutral-duplicate knob surface: env var vs module constant (default suppress).
