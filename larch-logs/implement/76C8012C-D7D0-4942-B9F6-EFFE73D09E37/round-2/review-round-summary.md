# Review Round 2

- Mode: `diff`
- 8 accepted, 2 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Publish writes a stale difficulty trailer
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-correctness, codex-specialist-edge-cases, codex-specialist-testing
- **Severity**: important
- **Concern**: Publish calibrates difficulty from the raw sidecar for labels and records, but it still writes the original plan text to the issue. A bumped sidecar can therefore leave `/implement` reading a stale `difficulty:` trailer.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Rewrite trailer difficulty to design_rating.adjusted_tier (or rebuild provenance from sidecar) before redact and named-block write.
  - From codex-specialist-correctness: Preserve an existing raw sidecar, make Step 2b/drafter produce the raw rating explicitly, and have publish rewrite or validate the plan trailer.
  - From codex-specialist-edge-cases: Rewrite the plan trailer `difficulty:` line to `design_rating.adjusted_tier` before validation, redaction, and `named-block write`, or fail publication if the trailer cannot be updated safely.
  - From codex-specialist-testing: Before validation/redaction/named-block write, rewrite or replace the trailer `difficulty:` line with `design_rating.adjusted_tier`, and extend the test to assert the named-block content carries `difficulty: MODERATE`.


### FINDING_2: Postplan overwrites richer raw difficulty sidecars
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, dyn-dyn-difficulty-records
- **Severity**: important
- **Concern**: Postplan always synthesizes or overwrites `design-difficulty-rating.raw.json` from the wire tier with fixed medium confidence. That destroys richer raw ratings before publish can consume them.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Require Step 2b to emit full raw JSON; use postplan synthesis only as recovery fallback.
  - From dyn-dyn-difficulty-records: Skip overwrite when an existing sidecar passes `read_rating_file`; only synthesize from wire metadata when the sidecar is absent.


### FINDING_3: Required difficulty validation happens too late
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-testing
- **Severity**: important
- **Concern**: Required difficulty validation is only enabled at publish, so validate, postplan, and clarify paths still accept plans missing difficulty until a late failure. The shared helper is effectively bypassed on the common path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-testing: Set LARCH_REQUIRE_PLAN_DIFFICULTY=1 on non-recovery postplan/clarify validate or call validate_difficulty_metadata with require=True.


### FINDING_4: Difficulty validation must be trailer-scoped
- **Reviewer(s)**: codex-specialist-testing
- **Severity**: important
- **Concern**: Difficulty validation scans the whole plan body instead of only the contiguous metadata trailer. A stray `difficulty:` token in prose can cause false defects even when the final trailer is valid.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: Reuse a trailer-scoped parser that ignores fenced/body content, and add a regression test with an invalid-looking body line plus a valid final trailer.


### FINDING_5: Clarify publish skips difficulty propagation
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, codex-specialist-edge-cases, dyn-dyn-difficulty-records
- **Severity**: important
- **Concern**: Clarify can write the updated plan without difficulty validation, label sync, or the run-level batch. That leaves the issue body and run logs stale after a clarified tier change.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Mirror the Step 5c publish tail: validate/preserve `difficulty:` in the clarify plan block, call `difficulty sync-labels` only after a successful `named-block write`.
  - From cursor-specialist-testing: Address the concern above.
  - From codex-specialist-edge-cases: After a successful clarify plan write, validate the trailer, sync difficulty labels, and write the design difficulty batch before log publish.
  - From dyn-dyn-difficulty-records: Mirror the Step 5c publish tail: validate/preserve `difficulty:` in the clarify plan block, call `difficulty sync-labels` only after a successful `named-block write`.


### FINDING_6: Final flush never recomputes difficulty floors
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, codex-specialist-edge-cases, codex-specialist-testing, dyn-dyn-difficulty-records
- **Severity**: important
- **Concern**: Pre-ship and final flush stages refresh summaries and transcripts, but they do not recompute floor matches from the final changed-path set. Late edits can leave committed `difficulty-rating.json` stale.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From codex-specialist-edge-cases: Add a difficulty refresh during `_stage_pre_commit` that preserves model ratings, recomputes floor matches from final changed paths, only raises `applied_tier` and `floors_applied`.
  - From codex-specialist-testing: Add a flush-stage refresh that preserves the model rating, recomputes floor matches from the final diff paths, and rewrites the `difficulty-rating` batch before final-summary rendering.
  - From dyn-dyn-difficulty-records: During `flush_logs_pre` / final flush, re-read the existing record and changed paths from git, rerun `build_record` with floors-only elevation (`override_source=floor`), and rewrite the `difficulty-rating` batch.


### FINDING_7: Terminal design summaries do not persist the run-level difficulty record
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-testing, codex-specialist-correctness, dyn-dyn-difficulty-records
- **Severity**: important
- **Concern**: Terminal design runs can render a difficulty summary without writing `difficulty-rating.json` when Step 5c did not run. The run directory then lacks the required batch artifact.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From codex-specialist-correctness: Write difficulty-rating.json from plan metadata/sidecar on terminal flush before rendering the summary line.
  - From dyn-dyn-difficulty-records: Before final-summary render, call `difficulty write-record` from plan metadata/sidecar and flush the `difficulty-rating` batch whenever `RUN_ID` is set.


### FINDING_8: Fallback ratings silently upgrade valid TRIVIAL runs
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, codex-specialist-edge-cases
- **Severity**: important
- **Concern**: Fallback ratings are mixed into `model_tier` even when a valid model rating exists, and the default fallback is MODERATE. That can silently upgrade real TRIVIAL runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-correctness: Make fallback opt-in only for documented recovery paths with no valid model rating.
  - From codex-specialist-edge-cases: Make fallback opt-in for named recovery paths only, default `--fallback-tier` to empty, and remove the normal Step 2 fallback args.


