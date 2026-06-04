### FINDING_1: Broad `main()` exception handling hides internal failures
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `python/ship.py` catches broad `Exception` and maps unexpected bugs to `STALLED` JSON/exit 4 with `str(exc)`, losing traceback context, encouraging operational retries, and potentially exposing sensitive exception text.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_2: Duplicate PR JSON parsing in `pr_view_current`
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `python/gh.py` duplicates PullRequest JSON parsing across `pr_view_current`, `pr_view`, and `pr_for_branch`, increasing schema-drift risk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_3: Duplicated post-create PR resolution cascade
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `python/gh.py` duplicates PR recovery logic on conflict and success paths, risking inconsistent fallback behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_4: Large volatile-run-log cleanup block is hard to maintain
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `python/run_logs.py` embeds a large volatile-only porcelain/cleanup block inside `_larch_log_commit`, making future allowlist or git-status changes error-prone.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_5: `head_match` naming obscures merge-state comparison
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `python/merge.py` variable naming obscures stale-state versus updated-state comparison after force-push recovery.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_6: Breadcrumb writer is reallocated per breadcrumb
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `python/ship.py` creates a new `BreadcrumbWriter` for each breadcrumb call, adding minor allocation/noise in long loops.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_7: Python 3.11 ship-driver guard is prose-only
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: `skills/implement/SKILL.md` documents the Python 3.11 guard in prose but not in the executable Invoke fence, so an orchestrator may skip the version probe on the Python ship path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] Mixed breadcrumb APIs in CI monitor
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `python/ci_monitor.py` mixes `_warn_stderr` and `BreadcrumbWriter`, producing inconsistent stderr prefixes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] Duplicate closed-PR checks in merge
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `python/merge.py` calls `_merge_noop_if_pr_closed` redundantly, adding extra `gh` round trips.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_10: Scrubbed volatile sidecars can still be committed
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `python/run_logs.py` requires `violations == 0` for volatile-only skip; scrubbed refresh sidecars can set violations and then get committed instead of restored/cleaned, reviving PR-head divergence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_11: Missing regression test for Python 3.11 selector guard
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: No automated test pins the Python 3.11 ship-driver selector/version-probe behavior, so docs may say 3.11 while `/implement` invokes `ship.py` under Python 3.10 until runtime failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_12: Merge-convergence testing does not prove single CI cycle
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Existing tests only prove `merge_pr` does not call `flush_logs_pre`; they do not catch a `run_ship`-level CI/merge loop regression on a clean green path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_13: Breadcrumb tests do not exercise real `run_ship` phase call sites
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Breadcrumb coverage only exercises `_breadcrumb` via stubbed paths, so removing breadcrumbs from real `run_ship` branches could leave tests green.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_14: CI poll breadcrumb test omits elapsed seconds
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `python/test_ci_monitor.py` does not assert elapsed seconds in poll breadcrumb output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_15: Transcript refresh sidecar volatile skip is untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `session-transcript-refresh.txt` is allowlisted for volatile-only skip but lacks a regression test.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_16: PR URL recovery can bind the wrong PR without validation
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-pr-create-resilience-output.txt
- **Severity**: important
- **Concern**: `python/gh.py` parses PR URLs from `gh` output and fabricates a `PullRequest` without confirming repo, branch/head ref, or open state, so misleading output can target the wrong PR.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From dyn-pr-create-resilience-output.txt: Address the concern above.

### FINDING_17: Raw git porcelain may leak sensitive paths in ShipError detail
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `python/run_logs.py` includes raw git status lines in leftover-porcelain `ShipError` detail, potentially exposing sensitive filenames or paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_18: [OUT_OF_SCOPE] Admission gate fail-opens on blocker-read failures
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `scripts/implement-admission.sh` may proceed during `gh`/API outages despite unknown blockers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_19: Python breadcrumbs ignore quiet-mode routing
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `python/ship.py` and `python/ci_monitor.py` write breadcrumbs directly to stderr, while bash progress honors quiet FD3 routing, causing stderr spam in quiet `/implement` runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_20: `pr_view_current` fallback is insufficiently corroborated
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-pr-create-resilience-output.txt
- **Severity**: latent
- **Concern**: `python/gh.py` accepts `pr_view_current` fallback results based on matching head ref without enough corroboration, including no explicit `--head` retry and no `OPEN` state requirement.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-pr-create-resilience-output.txt: Address the concern above.

### FINDING_21: `pr_create` over-reports `created=True` on recovery
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `python/gh.py` reports `created=True` on success-path recovery even when an open PR already existed, skewing telemetry.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_22: [OUT_OF_SCOPE] Final-report refresh failures are silently suppressed
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `python/run_logs.py` suppresses `ShipError` around `_write_final_report` in `flush_logs_pre`, silently dropping final-report refresh failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_23: [OUT_OF_SCOPE] Extra ship-level CI breadcrumb duplicates CI monitor output
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `python/ship.py` emits a per-iteration CI breadcrumb that duplicates `ci_monitor` poll stderr lines.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_24: Volatile cleanup misclassifies combined `A*` porcelain states
- **Reviewer(s)**: dyn-git-porcelain-cleanup-output.txt
- **Severity**: important
- **Concern**: `_cleanup_volatile_run_tree` uses `"A" in line[:2]` as an index-added proxy; combined states like `AM`, `AU`, and `AD` can be routed incorrectly, leaving tracked modifications after reset/clean and stalling volatile-only cleanup.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-git-porcelain-cleanup-output.txt: Address the concern above.

### FINDING_25: Quoted git-status paths fail volatile allowlist classification
- **Reviewer(s)**: dyn-git-porcelain-cleanup-output.txt
- **Severity**: latent
- **Concern**: `_status_line_path` does not strip Git porcelain double quotes, so quoted run-log refresh sidecars may fail `rel/` and allowlist checks and get committed instead of skipped.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-git-porcelain-cleanup-output.txt: Address the concern above.

### FINDING_26: Malformed or blank porcelain lines fail open to normal commit
- **Reviewer(s)**: dyn-git-porcelain-cleanup-output.txt
- **Severity**: latent
- **Concern**: `_volatile_file_paths` returns `None` for empty/unparseable paths, aborting volatile-only cleanup and falling through to a normal flush commit rather than failing closed or distinguishing non-volatile paths from parse failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-git-porcelain-cleanup-output.txt: Address the concern above.

### FINDING_27: [OUT_OF_SCOPE] Missing direct tests for status helper parsing
- **Reviewer(s)**: dyn-git-porcelain-cleanup-output.txt
- **Severity**: nit
- **Concern**: There are no direct unit tests for `_status_line_path`, `_volatile_file_paths`, or rename porcelain lines.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-git-porcelain-cleanup-output.txt: Address the concern above.

### FINDING_28: [OUT_OF_SCOPE] Porcelain parsing pattern is not reused from `version_bump.py`
- **Reviewer(s)**: dyn-git-porcelain-cleanup-output.txt
- **Severity**: nit
- **Concern**: `python/version_bump.py` already uses explicit porcelain status-code parsing, but the volatile cleanup path does not reuse that pattern.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-git-porcelain-cleanup-output.txt: Address the concern above.

### FINDING_29: PR success recovery can prefer stderr URL over stdout URL
- **Reviewer(s)**: dyn-pr-create-resilience-output.txt
- **Severity**: important
- **Concern**: `python/gh.py` combines stdout and stderr for post-success URL recovery and selects the last PR URL, so a stderr URL can override the newly created PR URL from stdout.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-pr-create-resilience-output.txt: Address the concern above.

### FINDING_30: [OUT_OF_SCOPE] Post-create exception handling continues recovery chain
- **Reviewer(s)**: dyn-pr-create-resilience-output.txt
- **Severity**: nit
- **Concern**: The reviewer observed that `ShipError`/`TransientNetworkError` from post-create `pr_for_branch` are handled by continuing recovery rather than re-raising.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-pr-create-resilience-output.txt: Address the concern above.

### FINDING_31: [OUT_OF_SCOPE] Success and conflict recovery paths are mutually exclusive
- **Reviewer(s)**: dyn-pr-create-resilience-output.txt
- **Severity**: nit
- **Concern**: The reviewer observed that successful create and conflict recovery paths are separated by return code and do not consume each other’s output in the same call.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-pr-create-resilience-output.txt: Address the concern above.

### FINDING_32: [OUT_OF_SCOPE] Multiple closed-plus-open PR case is normally guarded
- **Reviewer(s)**: dyn-pr-create-resilience-output.txt
- **Severity**: nit
- **Concern**: The reviewer observed that initial `pr_for_branch --state open` and cwd scoping normally guard the multiple closed-plus-open PR case, with residual risk mainly false-negative behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-pr-create-resilience-output.txt: Address the concern above.

### FINDING_33: [OUT_OF_SCOPE] Reviewer considers current `created` semantics correct
- **Reviewer(s)**: dyn-pr-create-resilience-output.txt
- **Severity**: nit
- **Concern**: The reviewer observed that existing/conflict paths return `created=False` and post-success resolution paths return `created=True`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-pr-create-resilience-output.txt: Address the concern above.
