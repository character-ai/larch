### FINDING_1: [OUT_OF_SCOPE] Unused `pr_view_current` helpers add dead surface or should be wired into PR recovery
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-gh-cli-contracts-output.txt, dyn-python311-compat-output.txt
- **Severity**: important
- **Concern**: `pr_view_current` / `pr_view_current_read` are newly present but unused. Reviewers disagree whether to remove them or wire them into post-create PR recovery, but the shared risk is dead API surface and unclear intended recovery behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-gh-cli-contracts-output.txt, dyn-python311-compat-output.txt: Address the concern above.

### FINDING_2: Stale `flush_logs_pre` monkeypatches obscure merge behavior tests
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Many `python/test_merge.py` tests still monkeypatch `flush_logs_pre` even though `merge_pr` no longer invokes it, making tests imply obsolete pre-merge flush behavior and weakening regression coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_3: Ship merge loop cap duplicates CI monitor cap without documented layering
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `SHIP_MERGE_LOOP_MAX_ITERATIONS` duplicates `CI_MONITOR_MAX_ITERATIONS` at 50, so future tuning could make one layer stall or bound differently than expected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_4: PR recovery helpers are fragmented across subtle modes
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: PR recovery is split across multiple helpers with subtle `allow_unverified` differences, increasing maintenance risk for future gh CLI or validation changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_5: Volatile-only run-tree wrapper adds pass-through indirection
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `_volatile_only_under_run_tree` only wraps `_volatile_file_paths`, adding no behavior while obscuring the classifier entry point.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_6: Merge polling helpers duplicate retry-loop structure
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `_poll_head_oid_match` and `_retry_unknown` duplicate poll/sleep/retry logic that can drift if timing or caps change.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_7: `_ensure_head_matches_pr` return annotation conflicts with caller guard
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `_ensure_head_matches_pr` is annotated as returning `None` but callers check for a non-`None` value, making the control flow and typing misleading.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_8: `_breadcrumb` allocates a writer on every call
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `_breadcrumb` creates a new `BreadcrumbWriter` each time, adding minor allocation noise and diverging from tests that reuse a writer.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] CI monitor rebase/evaluate path consumes two loop iterations
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `monitor()` handles `rebase_then_evaluate` in two steps instead of bash’s atomic rebase+evaluate behavior, potentially consuming extra loop iterations before fixers run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_10: Post-create URL recovery can fabricate or bind the wrong PR when verification fails
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-gh-cli-contracts-output.txt
- **Severity**: important
- **Concern**: Post-create recovery can use URL-derived candidates with `allow_unverified=True` after `pr_view` failure, returning a synthetic OPEN PR without confirming existence, state, or branch match.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-gh-cli-contracts-output.txt: Address the concern above.

### FINDING_11: Breadcrumb diagnostics may disappear from operator-visible stderr under lib-quiet
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-stdout-protocol-output.txt
- **Severity**: important
- **Concern**: `BreadcrumbWriter` honors quiet routing, so ship/CI progress and warning breadcrumbs can go to quiet logs instead of captured stderr during `/implement`, reducing operator-visible progress.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-stdout-protocol-output.txt: Address the concern above.

### FINDING_12: Refresh-only run-log updates can skip NDJSON regeneration
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `_render_token_timing_batches` can return early when only refresh sidecars exist, skipping `tokens.scrape_run` and leaving canonical NDJSON/timing batches stale or absent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_13: Strict head-ref equality can reject `owner:branch` values
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: PR validation compares `headRefName` directly to the local branch, so `owner:feat` versus `feat` can fail after an otherwise successful `pr view`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_14: [OUT_OF_SCOPE] `--no-logs-commit` parity can diverge across Python ship paths
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: `--no-logs-commit` is not consistently forwarded/read across Python invoke and pre-rebase flush paths, so state-file side effects and `ctx.no_logs_commit` can diverge.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_15: Missing run-level test for single-cycle green merge convergence
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Tests only cover mocked merge/monitor pieces, not a `run_ship` green path that proves no pre-merge flush churn and only one CI-monitor pass occur.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_16: Volatile cleanup tests do not prove successful staged reset ordering
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-python311-compat-output.txt
- **Severity**: important
- **Concern**: Volatile cleanup tests cover reset failure but not the successful `git reset HEAD -- rel` before restore path; one fixture may also consume mocked responses out of order and pass without validating the reset sequence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, dyn-python311-compat-output.txt: Address the concern above.

### FINDING_17: Python 3.11 ship guard lacks failure-path harness coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The Python 3.11 guard is checked mostly by static grep, so breaking the runtime failure path could allow unsupported interpreters to run `ship.py` without CI catching it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_18: [OUT_OF_SCOPE] `gh pr create` no-`--json` coverage is incomplete
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-gh-cli-contracts-output.txt
- **Severity**: nit
- **Concern**: Only some `pr_create` paths assert absence of `--json`, and recorded fixtures do not catch host-specific output drift beyond the fixture.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, dyn-gh-cli-contracts-output.txt: Address the concern above.

### FINDING_19: Volatile cleanup errors can expose raw porcelain paths in JSON
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `ShipError` details for volatile cleanup can include raw porcelain paths surfaced in STALLED JSON and downstream logs, potentially leaking sensitive filenames.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_20: Unexpected exceptions lose traceback detail
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `main()` converts all unexpected exceptions to generic `INTERNAL_ERROR` JSON without traceback logging, slowing soak/debug cycles.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_21: Duplicate closed-PR noop checks add redundant gh calls
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Two consecutive identical `_merge_noop_if_pr_closed` calls remain where pre-merge flush used to sit, doubling gh traffic and complicating test stubs with no functional gain.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_22: Create-conflict recovery is stricter than bash when list/view both fail
- **Reviewer(s)**: dyn-gh-cli-contracts-output.txt
- **Severity**: important
- **Concern**: On an “already exists” create conflict, Python can raise if both `pr list` and verified `pr view` fail, even when conflict output contains a valid PR URL that bash would recover from.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-gh-cli-contracts-output.txt: Address the concern above.

### FINDING_23: Quiet stdout redirection can break ship.py JSON stdout protocol
- **Reviewer(s)**: dyn-stdout-protocol-output.txt
- **Severity**: important
- **Concern**: The Python invoke fence runs `ship.py` without restoring caller streams, so under inherited lib-quiet stdout redirection the single JSON result could land in the quiet log instead of orchestrator-visible stdout.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-stdout-protocol-output.txt: Address the concern above.

### FINDING_24: [OUT_OF_SCOPE] `emit_result` lacks explicit flush
- **Reviewer(s)**: dyn-stdout-protocol-output.txt
- **Severity**: nit
- **Concern**: `emit_result` does not use `flush=True`; safe today because the process exits immediately, but potentially brittle for future streaming readers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-stdout-protocol-output.txt: Address the concern above.

### FINDING_25: [OUT_OF_SCOPE] Step 8+ prose still references state-file routing on Python path
- **Reviewer(s)**: dyn-stdout-protocol-output.txt
- **Severity**: latent
- **Concern**: Step 8+ documentation still routes several branches through `ship-pr-state.sh` even though the Python selector says not to use that file for Python-path routing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-stdout-protocol-output.txt: Address the concern above.

### FINDING_26: [OUT_OF_SCOPE] Normal stdout protocol path was verified OK
- **Reviewer(s)**: dyn-stdout-protocol-output.txt
- **Severity**: nit
- **Concern**: Under default invocation without lib-quiet stdout redirect, stdout carries exactly one JSON object and subprocess output does not leak into driver stdout.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-stdout-protocol-output.txt: Address the concern above.

### FINDING_27: [OUT_OF_SCOPE] Local Python floor helper test provides little regression value
- **Reviewer(s)**: dyn-python311-compat-output.txt
- **Severity**: nit
- **Concern**: `test_python_ship_driver_version_guard_probe` tests a local helper rather than the runtime probe expression, so it cannot catch drift in the actual guard.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-python311-compat-output.txt: Address the concern above.
