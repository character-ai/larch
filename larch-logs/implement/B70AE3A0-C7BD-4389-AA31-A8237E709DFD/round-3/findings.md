### FINDING_1: PR creation resolution is over-layered
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `pr_create` resolution now spans many layered helpers and extra `gh` calls, making the success path slow, hard to reason about, and difficult to maintain.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_2: Volatile cleanup logic is dense and hard to review
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: Volatile-only flush cleanup implements porcelain parsing and git cleanup inline with dense comprehensions, increasing regression risk in future run-log changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_3: Merge convergence lacks full single-cycle regression coverage
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Tests do not fully model the intended one-monitor/one-merge green path, so merge-time flush churn or repeated CI monitor loops could regress without failing tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_4: Unexpected Python exceptions are reported as operational stalls
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `ship.py main()` maps arbitrary uncaught exceptions to STALLED exit 4, causing programming bugs to look like recoverable operational stalls.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] Duplicate CI breadcrumbs are noisy
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-stdio-quiet-output.txt
- **Severity**: nit
- **Concern**: Both `ship.py` and `ci_monitor.py` emit CI poll breadcrumbs, creating redundant progress lines during long waits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, dyn-stdio-quiet-output.txt: Address the concern above.

### FINDING_6: Quiet routing can hide operator-visible breadcrumbs
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-stdio-quiet-output.txt
- **Severity**: important
- **Concern**: `BreadcrumbWriter` treats `LARCH_QUIET_ACTIVE` as sufficient for quiet routing while `LARCH_QUIET_PID` is unused, so breadcrumbs can skip stderr or vanish when FD 4/log-file routing is not actually initialized.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-stdio-quiet-output.txt: Address the concern above.

### FINDING_7: Python 3.11 floor is fragmented across docs, skills, and local checks
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-py311-floor-output.txt
- **Severity**: latent
- **Concern**: The Python 3.11 runtime floor is duplicated or missing across skill prose, docs, report-token surfaces, Makefile/local checks, and relevant-checks, creating drift and unclear operator expectations.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, dyn-py311-floor-output.txt: Address the concern above.

### FINDING_8: `pr_view_current` is duplicated and unsafe as a PR recovery fallback
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `pr_view_current` duplicates `pr_view` parsing and may resolve the checked-out branch’s PR rather than the intended newly created PR head branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_9: Post-create transient network errors become stalls
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `pr_create` can swallow `TransientNetworkError` during post-create PR resolution and return STALLED exit 4 instead of TRANSIENT exit 6, preventing retry behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_10: Python 3.11 shell guard fails outside the JSON protocol
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: The Step 8 Python version guard exits 1 with text only, while Python-path orchestration expects structured JSON outcomes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_11: [OUT_OF_SCOPE] URL recovery rejects GitHub Enterprise hosts
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-gh-create-output.txt
- **Severity**: important
- **Concern**: `_repo_matches_pr_url` requires a `github.com` URL shape, so successful PR creation on GitHub Enterprise hosts can fail recovery.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-gh-create-output.txt: Address the concern above.

### FINDING_12: Force-push recovery compares against stale pre-recovery head state
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-merge-race-output.txt
- **Severity**: important
- **Concern**: After force-push recovery succeeds and refreshed CI/state checks pass, `merge_pr` still compares the refreshed PR head OID to the stale pre-recovery snapshot and returns `CI_NOT_READY` instead of merging in the same call.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-merge-race-output.txt: Address the concern above.

### FINDING_13: [OUT_OF_SCOPE] Step 8 prose still references bash state routing
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Post-invoke text still references `ship-pr-state.sh` for all implementations, which can mislead Python-path orchestration that should rely on JSON-only routing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_14: Volatile-only behavior lacks full publish-path testing
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Tests do not exercise volatile-only cleanup through the full `flush_logs_pre` publish path, so dirty porcelain or spurious commits could escape isolated helper tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_15: Mixed volatile and canonical run-log deltas are untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-git-porcelain-output.txt
- **Severity**: latent
- **Concern**: No regression test proves that a flush containing both refresh sidecars and substantive canonical artifacts still commits rather than being skipped as volatile-only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, dyn-git-porcelain-output.txt: Address the concern above.

### FINDING_16: Version guard test is tautological
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-py311-floor-output.txt
- **Severity**: latent
- **Concern**: The Python version guard test checks local comparison logic rather than executing or structurally pinning the actual SKILL shell guard.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, dyn-py311-floor-output.txt: Address the concern above.

### FINDING_17: CI breadcrumb elapsed text is not meaningfully tested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The CI poll breadcrumb test uses a fixed zero elapsed clock, so elapsed reporting regressions would not be caught.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_18: [OUT_OF_SCOPE] Direct `ship.py` invocation lacks a version guard
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Scripts or operators invoking `ship.py` directly can bypass the `/implement` Python 3.11 guard.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_19: URL validation uses weak substring matching
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `_repo_matches_pr_url` uses substring containment rather than strict URL parsing, weakening the first validation gate for recovered PR URLs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_20: Unexpected-exception diagnostics bypass quiet routing and may leak details
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-stdio-quiet-output.txt
- **Severity**: latent
- **Concern**: Unexpected exception handling prints raw tracebacks or direct stderr diagnostics, bypassing `BreadcrumbWriter` and potentially leaking stack details or splitting observability channels.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, dyn-stdio-quiet-output.txt: Address the concern above.

### FINDING_21: Volatile cleanup failures expose raw porcelain paths
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Volatile cleanup failure detail includes raw porcelain paths, which can reveal sensitive repository path names in operator-visible JSON.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_22: Volatile cleanup fails closed on unrelated repo dirt
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Volatile-only cleanup requires repo-wide porcelain to be empty after cleanup, so unrelated local edits can stall each CI/rebase refresh iteration.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_23: Staged detection may reset too broadly
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `has_staged` checks only `line[0]`, so unusual porcelain states can trigger broad resets that disturb unrelated staged run-log files.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_24: OID polling shares retry budget with UNKNOWN merge-state polling
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Force-push OID polling and UNKNOWN merge-state polling share the same retry constant, so one concern can consume the other’s budget.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_25: [OUT_OF_SCOPE] Python ship path does not initialize quiet routing like bash
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The Python ship path does not call `larch_quiet_init`, so quiet/progress routing can differ from `ship-pr.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_26: Phase breadcrumb coverage is incomplete
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: The happy-path stage-order test asserts only some breadcrumbs and does not cover every major phase required by the plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_27: [OUT_OF_SCOPE] Volatile classifier implementation matches the plan
- **Reviewer(s)**: dyn-git-porcelain-output.txt
- **Severity**: nit
- **Concern**: Reviewer observed that the volatile classifier and cleanup posture correctly match the plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-git-porcelain-output.txt: Address the concern above.

### FINDING_28: [OUT_OF_SCOPE] ndjson-only substantive delta coverage is absent
- **Reviewer(s)**: dyn-git-porcelain-output.txt
- **Severity**: latent
- **Concern**: Tests cover canonical `token-report.json` commits but not an ndjson-only substantive delta.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-git-porcelain-output.txt: Address the concern above.

### FINDING_29: [OUT_OF_SCOPE] Scrubbed volatile sidecar cleanup is intentional
- **Reviewer(s)**: dyn-git-porcelain-output.txt
- **Severity**: nit
- **Concern**: Reviewer observed that scrubbed refresh sidecars are intentionally restored/cleaned instead of committed and have test coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-git-porcelain-output.txt: Address the concern above.

### FINDING_30: PR creation ignores stderr URLs after invalid stdout URLs
- **Reviewer(s)**: dyn-gh-create-output.txt
- **Severity**: important
- **Concern**: On successful `gh pr create`, stdout URLs are treated as terminal even when validation fails, so a real PR URL present only on stderr is never tried.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-gh-create-output.txt: Address the concern above.

### FINDING_31: List-based post-create recovery is not validated
- **Reviewer(s)**: dyn-gh-create-output.txt
- **Severity**: important
- **Concern**: Immediate `pr_for_branch` recovery after create returns a PR without the same `pr_view` head-ref/state validation used for URL recovery.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-gh-create-output.txt: Address the concern above.

### FINDING_32: [OUT_OF_SCOPE] Missing stdout-invalid/stderr-real URL recovery test
- **Reviewer(s)**: dyn-gh-create-output.txt
- **Severity**: latent
- **Concern**: Tests do not cover the case where stdout contains a regex-matching but invalid PR URL while stderr contains the real PR URL.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-gh-create-output.txt: Address the concern above.

### FINDING_33: [OUT_OF_SCOPE] Recorded gh fixture is not live CLI coverage
- **Reviewer(s)**: dyn-gh-create-output.txt
- **Severity**: nit
- **Concern**: The recorded acceptance gate catches flag reintroduction but not live `gh` CLI drift in unrecorded fields.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-gh-create-output.txt: Address the concern above.

### FINDING_34: [OUT_OF_SCOPE] Closed-PR noop check is duplicated
- **Reviewer(s)**: dyn-merge-race-output.txt
- **Severity**: nit
- **Concern**: `_merge_noop_if_pr_closed` is invoked twice back-to-back before merge logic.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-merge-race-output.txt: Address the concern above.

### FINDING_35: [OUT_OF_SCOPE] Force-push recovery test misses changed-head scenario
- **Reviewer(s)**: dyn-merge-race-output.txt
- **Severity**: latent
- **Concern**: Existing merge recovery tests do not exercise the case where the PR head OID changes from the pre-recovery snapshot.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-merge-race-output.txt: Address the concern above.

### FINDING_36: Run-log secret scrub warnings bypass quiet routing
- **Reviewer(s)**: dyn-stdio-quiet-output.txt
- **Severity**: latent
- **Concern**: `_warn_secret_scrub` writes directly to stderr, so scrub warnings may not reach the same operator-visible quiet channel as ship/CI breadcrumbs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-stdio-quiet-output.txt: Address the concern above.

### FINDING_37: [OUT_OF_SCOPE] Stdout JSON contract appears sound
- **Reviewer(s)**: dyn-stdio-quiet-output.txt
- **Severity**: nit
- **Concern**: Reviewer observed that `emit_result` remains the sole stdout printer and tests assert single-line JSON stdout.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-stdio-quiet-output.txt: Address the concern above.

### FINDING_38: [OUT_OF_SCOPE] Python floor was propagated across many core surfaces
- **Reviewer(s)**: dyn-py311-floor-output.txt
- **Severity**: nit
- **Concern**: Reviewer observed that the 3.11 floor is correctly reflected across core Python config, CI matrices, implement skill guard, and report-token wrapper surfaces.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-py311-floor-output.txt: Address the concern above.

### FINDING_39: [OUT_OF_SCOPE] Runtime already implicitly required Python 3.11
- **Reviewer(s)**: dyn-py311-floor-output.txt
- **Severity**: nit
- **Concern**: Reviewer observed that existing runtime imports already required Python 3.11, so the documented floor aligns with latent import reality.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-py311-floor-output.txt: Address the concern above.

### FINDING_40: [OUT_OF_SCOPE] `run-analysis.sh` version probe lacks a structural pin
- **Reviewer(s)**: dyn-py311-floor-output.txt
- **Severity**: latent
- **Concern**: There is no structural grep equivalent pinning the `run-analysis.sh` Python version probe, so future edits could remove it unnoticed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-py311-floor-output.txt: Address the concern above.
