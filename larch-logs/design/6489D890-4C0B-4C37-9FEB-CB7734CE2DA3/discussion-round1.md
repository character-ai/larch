## Decision 1: Item 1 — fix approach for `_derive_oos_fields`
- **Question**: Minimal regex fix vs robust JSON parse of `oos-issues.ndjson`?
- **Resolution**: Robust JSON parse. Parse each ndjson line as JSON, read the filed-URL out of the record `body` field directly (mirror the existing `oos_filer._ndjson_filed_evidence` pattern). Do not keep the fragile character-class regex.
- **Source**: user

## Decision 2: Item 1 — sibling call sites
- **Question**: Are there other call sites copy-pasting the buggy `[^\"\\s>)]` URL-scrape class?
- **Resolution**: None. `pr_body.py:850` is the only occurrence. Scope stays `python/pr_body.py` + `python/test_pr_body.py`.
- **Source**: codebase

## Decision 3: Item 2 — fix side and canonical round header
- **Question**: Fix the validator (`voting.py`) or the composer (`review_and_fix.py`)?
- **Resolution**: Composer side. Change `write_rejected_findings_aggregate` (`review_and_fix.py:820`) to emit the already-allowed `# Review Round N` instead of `## Round N`. The validator stays unchanged; it already accepts `^# Review Round [0-9]+$`. Blast radius is only the aggregate output and its test (sole emitter + sole validator confirmed by grep). Cosmetic note: `# Review Round N` is h1 under the `# Rejected Findings` h1.
- **Source**: user + codebase

## Decision 4: Item 3 — where diagram-failure detail lands
- **Question**: In-tmpdir failure log only, committed run log, or both?
- **Resolution**: In-tmpdir `code-flow-diagram.failure.log` (redacted stderr/stdout) + exit code and failure-log path surfaced in the returned `reason` (which flows into the committed `_append_diagram_warning`). No raw stderr in the committed run log.
- **Source**: user

## Decision 5: Scope and hard constraints
- **Question**: What is in-scope, and what must not break?
- **Resolution**: All 4 items in scope, each a surgical change plus regression test. Hard constraints: keep diagram generation and code-review-tally flush **non-fatal** (best-effort); reuse `/issue --title-prefix` for Item 4 (do NOT reimplement title-prefix logic in `/bug`); `--urgent` **replaces** the prefix with `[BUG] (URGENT)` (single `--title-prefix` value, no stacking); no change to `/combine-issues` filtering. Item 2 validator (`voting.py`) is left untouched.
- **Source**: issue + user
