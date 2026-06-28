### OOS_1: [OUT_OF_SCOPE] Historical implement run dirs lack `plan-review-tally.json`
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: latent
- **Concern**: The fix is forward-looking only. Existing committed implement run dirs that predate this write path still lack `plan-review-tally.json`, so full-history `required-file-presence` scans will keep reporting failures on those dirs until they are backfilled or audits are scoped to post-fix plugin versions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Document the cutoff version in audit tooling, or add a one-time backfill if full-history scans must go green.

### OOS_2: [OUT_OF_SCOPE] `_write_plan_review_tally_batch` ignores `_cli` return code
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: important
- **Concern**: `_write_plan_review_tally_batch` ignores `_cli` return code, so a failed `run-log write` leaves the run without `plan-review-tally.json` and no bootstrap warning; `required-file-presence` would still fail. Same pattern as `_upsert_plan_summary` and the pre-change candidate path; not introduced by this diff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Check return code and log to execution-issues or stderr on non-zero exit.

### OOS_3: [OUT_OF_SCOPE] `step8` reach logic still references `version-bump-reasoning.md`
- **Reviewer(s)**: cursor-specialist-edge-cases, dyn-dyn-runlog-contract-sync
- **Severity**: latent
- **Concern**: `step8` condition logic in `python/larch/issue/audit_runs.py` and `python/larch/report/run_logs.py` still treats `version-bump-reasoning.md` as a reach signal even though it was removed from `docs/run-logs-required-files.tsv`. Backward-compatible for legacy trees and does not break `final-summary.md` gating; leftover drift, not a regression from this diff. No current scan impact because the TSV no longer lists that file.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Align step8 reach logic with the TSV (e.g., `final-summary.md` only) to avoid drift if the file is re-added later.

### OOS_4: [OUT_OF_SCOPE] Plan-review tally stub runs too late for early-bail partial logs
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: important
- **Concern**: `_publish_plan_review_tally` no-ops when `run_id` is invalid and only runs at the end of `_phase_plan`; runs that bail before that point can still miss `plan-review-tally.json` while the TSV `always` condition requires it. Pre-existing tension between `always` and partial logs; this PR fixes the dominant path (normal runs with no upstream tally).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Relax the TSV condition for early-bail partial logs, or emit the stub earlier once `run_id` is known.

### OOS_5: [OUT_OF_SCOPE] Bootstrap unit tests do not prove end-to-end `run-log write` path
- **Reviewer(s)**: dyn-dyn-runlog-contract-sync
- **Severity**: latent
- **Concern**: New tests in `python/test_bootstrap.py` mock `_cli` only, so they do not prove the stub survives the real `run-log write` json-object sanitizer and redaction path end-to-end. The stub shape looks valid, but there is no integration test against `larch_log_write_main` plus default `docs/run-logs-required-files.tsv`.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_6: [OUT_OF_SCOPE] `agent-lint.toml` comment drift on plan-review tally write site
- **Reviewer(s)**: dyn-dyn-runlog-contract-sync
- **Severity**: nit
- **Concern**: Comments in `agent-lint.toml` still say plan-review tally is written from "SKILL.md Step 1"; bootstrap Step 0 (`_phase_plan`) is now the write site per `docs/run-logs.md`. Comment-only drift, no runtime effect.
- **Suggested revisions (informational for voters; coder decides)**:

