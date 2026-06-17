## Proposed Design Outline

### Goals
- Fix 3 non-fatal Python runtime bugs surfaced by one live `/implement` run: truncated OOS URL, rejected `## Round N` tally header, opaque diagram failure.
- Add a forced `[BUG]` title prefix to `/bug`, plus `--urgent` → `[BUG] (URGENT)`.
- Ship each change with a focused regression test.

### Non-goals
- No reimplementation of title-prefix logic in `/bug` (reuse `/issue --title-prefix`).
- No change to the `voting.py` header validator (Item 2 fixed composer-side).
- No change to `/combine-issues` filtering.
- Diagram generation and code-review-tally flush stay non-fatal.

### Approach sketch
- Item 1: replace the fragile regex in `_derive_oos_fields` (`pr_body.py`) with JSON line parsing that reads the `**Filed URL**` field, mirroring `oos_filer._ndjson_filed_evidence`.
- Item 2: change `write_rejected_findings_aggregate` (`review_and_fix.py:820`) to emit `# Review Round N` (validator already allows it).
- Item 3: write redacted subprocess stderr/stdout to `code-flow-diagram.failure.log` and enrich the returned `reason` with exit code + path (`pr_body.py`); it already flows into the Step 7a warning.
- Item 4: pass `--title-prefix "[BUG]"` / `"[BUG] (URGENT)"` from `/bug` to `/issue`; add `--urgent` parsing + docs in `skills/bug/SKILL.md`.

### Surfaces in scope
- `python/pr_body.py`, `python/test_pr_body.py`
- `python/review_and_fix.py`, `python/test_review_and_fix.py`, `python/test_voting.py` (positive case; `voting.py` unchanged)
- `python/step_7a.py`, `python/test_step_7a.py`
- `skills/bug/SKILL.md` (+ `/bug` flag parsing and regression coverage)

### Open questions
- None.
