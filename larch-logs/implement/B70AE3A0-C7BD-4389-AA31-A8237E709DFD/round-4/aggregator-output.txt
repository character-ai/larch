### FINDING_1: Breadcrumbs can disappear or bypass expected stderr visibility under quiet mode
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-stream-protocol-output.txt
- **Severity**: important
- **Concern**: BreadcrumbWriter/lib-quiet routing can hide ship-phase and CI poll progress from the operator, especially when `LARCH_QUIET_ACTIVE` is set or FD/log routing is unavailable; tests also miss quiet-active breadcrumb coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-stream-protocol-output.txt: Address the concern above.

### FINDING_2: [OUT_OF_SCOPE] `pr_view_current` helpers are unused dead code
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-gh-cli-output.txt
- **Severity**: important
- **Concern**: `pr_view_current` / `pr_view_current_read` are never called, adding misleading PR-resolution API surface and future maintenance risk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-gh-cli-output.txt: Address the concern above.

### FINDING_3: `pr_for_branch` duplicates PullRequest JSON parsing
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `pr_for_branch` parses PullRequest JSON separately after `_pull_request_from_json`, so list/view parsing can drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_4: PR URL recovery stack is overly complex
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Multiple overlapping PR URL recovery entrypoints make conflict/success recovery ordering harder to reason about.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_5: Volatile-only skip uses a magic `CommandResult.argv` sentinel
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Callers must know the special `("larch-log-volatile-only",)` tuple contract instead of consuming an explicit outcome/metadata field.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_6: `_volatile_only_under_run_tree` is a no-op wrapper
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The helper adds indirection without behavior beyond an empty check.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_7: Python-path failure contracts are split
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The orchestrator must special-case Python version guard `STALLED` exit 4 versus driver bug `INTERNAL_ERROR` exit 1 without a shared emitter.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_8: `_ensure_head_matches_pr` return type has stale `None` handling
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: A redundant `head_match is not None` branch obscures merge control flow.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] Bash larch-log path lacks volatile-only skip
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-git-porcelain-output.txt
- **Severity**: latent
- **Concern**: Bash ship/log commit flow can still commit refresh-only churn because the Python volatile-only classifier has not been ported to bash.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, dyn-git-porcelain-output.txt: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] Python version floor probes and tests can drift
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, dyn-py311-compat-output.txt
- **Severity**: latent
- **Concern**: Python 3.11 floor enforcement is duplicated across skill/wrapper/test surfaces, and the current test helper does not exercise the documented shell guard or verify all enforcement surfaces.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, dyn-py311-compat-output.txt: Address the concern above.

### FINDING_11: PR URL validation is too strict for repo case and GHES hosts
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-gh-cli-output.txt
- **Severity**: important
- **Concern**: `_repo_matches_pr_url` can reject real PR URLs because it compares repo slugs case-sensitively and hardcodes `github.com`, breaking mixed-case repos or GitHub Enterprise hosts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-gh-cli-output.txt: Address the concern above.

### FINDING_12: Python ship ignores `--no-logs-commit` during pre-rebase flush
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `/implement --no-logs-commit` with `LARCH_SHIP_PR_IMPL=python` can still run `flush_logs_pre` on CI rebase because the flag/state is not propagated or honored.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_13: Post-recovery merge forces another CI loop after successful OID sync
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: After flush recovery verifies the refreshed PR head OID/checks, merge still returns `CI_NOT_READY` when the OID changed, contradicting the plan’s single-cycle convergence expectation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_14: [OUT_OF_SCOPE] INTERNAL_ERROR diagnostics hide exception detail
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Broad exception handling reports generic `INTERNAL_ERROR`, slowing triage by omitting redacted exception class/message from operator-visible diagnostics or journals.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_15: Missing regression test for single-CI-cycle merge convergence
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Tests assert `merge_pr` does not call `flush_logs_pre`, but do not bound CI/check iterations on a clean green path, so churn causing multiple CI cycles could regress unnoticed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_16: Refresh sidecar pipeline can still dirty non-volatile batch files
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-git-porcelain-output.txt
- **Severity**: important
- **Concern**: `flush_logs_pre` renders token/timing batch NDJSON before volatile classification, so live refresh-only sidecars can still produce non-volatile commits and diverge HEAD from the green PR OID.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, dyn-git-porcelain-output.txt: Address the concern above.

### FINDING_17: Breadcrumb exception details are not redacted
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Breadcrumbs can emit raw `str(exc)` to stderr/quiet sinks without `redact_outbound`, leaking paths or secret-shaped substrings outside the redacted JSON contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_18: Quiet log file path is not bounded
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `LARCH_QUIET_LOG_FILE` can direct quiet-mode breadcrumbs to arbitrary filesystem paths without session-root/path-boundary checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_19: PR identity recovery trusts `gh` output too readily
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: URL-based PR recovery validates URLs but can still bind shipping to an unintended PR if `gh` output is adversarial/buggy while APIs lag.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_20: Merge loop lacks an iteration ceiling
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Repeated `CI_NOT_READY` after force-push can spin indefinitely without returning `STALLED` JSON.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_21: Empty untracked run dir bypasses volatile-only skip
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: An empty untracked run tree can still be added/committed, diverging HEAD from the green PR head.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_22: [OUT_OF_SCOPE] Bash merge loop also lacks iteration cap
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The bash driver shares the unbounded merge-loop family, but hardening it is marked as a separate scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_23: URL fallback requires an immediate successful `pr_view`
- **Reviewer(s)**: dyn-gh-cli-output.txt
- **Severity**: important
- **Concern**: Post-create URL recovery can fail if `pr_view` transiently reports not found while stdout already contains a valid PR URL and `pr list` is still lagging.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-gh-cli-output.txt: Address the concern above.

### FINDING_24: Real-CLI transcript coverage for `gh pr create` is too thin
- **Reviewer(s)**: dyn-gh-cli-output.txt
- **Severity**: latent
- **Concern**: The test for dropping unsupported `--json` uses a one-line fixture and does not exercise realistic gh stdout/stderr prose or real binary argv behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-gh-cli-output.txt: Address the concern above.

### FINDING_25: [OUT_OF_SCOPE] Python `ensure_pr` omits explicit base branch
- **Reviewer(s)**: dyn-gh-cli-output.txt
- **Severity**: latent
- **Concern**: `ensure_pr` calls `gh.pr_create` without `--base`, unlike bash, leaving a parity gap for repositories whose default branch is not `main`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-gh-cli-output.txt: Address the concern above.

### FINDING_26: Volatile cleanup resets too broad a run-tree prefix
- **Reviewer(s)**: dyn-git-porcelain-output.txt
- **Severity**: latent
- **Concern**: `_cleanup_volatile_run_tree` runs `git reset HEAD -- <rel>` for the entire run directory instead of only volatile paths, creating a wider blast radius if classification is broadened or wrong.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-git-porcelain-output.txt: Address the concern above.

### FINDING_27: [OUT_OF_SCOPE] Volatile cleanup test does not assert staged reset behavior
- **Reviewer(s)**: dyn-git-porcelain-output.txt
- **Severity**: nit
- **Concern**: The AM porcelain test does not assert that `git reset HEAD -- <rel>` runs when the index column is non-space.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-git-porcelain-output.txt: Address the concern above.

### FINDING_28: Secret scrub warnings bypass quiet routing
- **Reviewer(s)**: dyn-stream-protocol-output.txt
- **Severity**: latent
- **Concern**: `_warn_secret_scrub` writes directly to stderr instead of the BreadcrumbWriter/lib-quiet channel, so credential-rotation warnings can be missed in quiet sessions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-stream-protocol-output.txt: Address the concern above.

### FINDING_29: [OUT_OF_SCOPE] Early argparse exits may violate JSON stdout contract
- **Reviewer(s)**: dyn-stream-protocol-output.txt
- **Severity**: latent
- **Concern**: `ship.py main()` catches broad exceptions, but argparse failures and other early exits can still produce non-JSON stdout/non-contract exit codes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-stream-protocol-output.txt: Address the concern above.

### FINDING_30: [OUT_OF_SCOPE] `version_bump.py` warning uses raw stderr
- **Reviewer(s)**: dyn-stream-protocol-output.txt
- **Severity**: nit
- **Concern**: `python/version_bump.py` has the same direct-stderr quiet-routing gap as scrub warnings, but is pre-existing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-stream-protocol-output.txt: Address the concern above.

### FINDING_31: [OUT_OF_SCOPE] Positive stdout/stderr contract observation
- **Reviewer(s)**: dyn-stream-protocol-output.txt
- **Severity**: nit
- **Concern**: Reviewer observed no issue: stdout JSON remains isolated through `emit_result`, subprocess output is captured, and tests/SKILL guard preserve the machine contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-stream-protocol-output.txt: Address the concern above.

### FINDING_32: [OUT_OF_SCOPE] Positive Python floor-lowering coverage observation
- **Reviewer(s)**: dyn-py311-compat-output.txt
- **Severity**: nit
- **Concern**: Reviewer observed the Python 3.11 floor-lowering appears complete across planned surfaces, with remaining 3.12 pins matching the contributor/runtime split.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-py311-compat-output.txt: Address the concern above.

### FINDING_33: [OUT_OF_SCOPE] Positive Python 3.11 syntax observation
- **Reviewer(s)**: dyn-py311-compat-output.txt
- **Severity**: nit
- **Concern**: Reviewer observed changed Python code uses 3.11-safe syntax and no 3.12-only constructs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-py311-compat-output.txt: Address the concern above.

### FINDING_34: [OUT_OF_SCOPE] `datetime.UTC` import matches declared 3.11 floor
- **Reviewer(s)**: dyn-py311-compat-output.txt
- **Severity**: nit
- **Concern**: Reviewer observed `from datetime import UTC` hard-requires 3.11+, matching the declared floor and guarded paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-py311-compat-output.txt: Address the concern above.

### FINDING_35: [OUT_OF_SCOPE] `docs/linting.md` does not mention new Python CI matrix
- **Reviewer(s)**: dyn-py311-compat-output.txt
- **Severity**: nit
- **Concern**: `docs/linting.md` still describes `python-lint`/`python-tests` as single jobs rather than the new `["3.11", "3.12"]` matrix.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-py311-compat-output.txt: Address the concern above.
