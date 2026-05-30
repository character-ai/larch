### External Reviewer Issues

- **Step design Step 3 — collect-agent-results.sh codex SENTINEL_TIMEOUT failed (exit 124)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-arch-output.txt|TOOL=codex|STATUS=SENTINEL_TIMEOUT|EXIT_CODE=124|FAILURE_REASON=Process did not complete (sentinel file missing — possible crash or system kill)

## Reviewer output (<TMPDIR>/codex-primary-plan-arch-output.txt)

{"no_issues_found": true}

## Reviewer stderr (<TMPDIR>/codex-primary-plan-arch-output.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-arch-output.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh codex SENTINEL_TIMEOUT failed (exit 124)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-edge-output.txt|TOOL=codex|STATUS=SENTINEL_TIMEOUT|EXIT_CODE=124|FAILURE_REASON=Process did not complete (sentinel file missing — possible crash or system kill)

## Reviewer output (<TMPDIR>/codex-primary-plan-edge-output.txt)

{"no_issues_found": true}

## Reviewer stderr (<TMPDIR>/codex-primary-plan-edge-output.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-edge-output.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh codex SENTINEL_TIMEOUT failed (exit 124)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-innovation-output.txt|TOOL=codex|STATUS=SENTINEL_TIMEOUT|EXIT_CODE=124|FAILURE_REASON=Process did not complete (sentinel file missing — possible crash or system kill)

## Reviewer output (<TMPDIR>/codex-primary-plan-innovation-output.txt)

{"no_issues_found": true}

## Reviewer stderr (<TMPDIR>/codex-primary-plan-innovation-output.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-innovation-output.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh cursor FAILED failed (exit 2)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/cursor-plan-pragmatic-output-phase3.txt|TOOL=cursor|STATUS=FAILED|EXIT_CODE=2|FAILURE_REASON=Process failed with exit code 2

## Reviewer output (<TMPDIR>/cursor-plan-pragmatic-output-phase3.txt)

(file missing: <TMPDIR>/cursor-plan-pragmatic-output-phase3.txt)

## Reviewer stderr (<TMPDIR>/cursor-plan-pragmatic-output-phase3.txt.diag)

(file missing: <TMPDIR>/cursor-plan-pragmatic-output-phase3.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh codex SENTINEL_TIMEOUT failed (exit 124)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-requirements-output.txt|TOOL=codex|STATUS=SENTINEL_TIMEOUT|EXIT_CODE=124|FAILURE_REASON=Process did not complete (sentinel file missing — possible crash or system kill)

## Reviewer output (<TMPDIR>/codex-primary-plan-requirements-output.txt)

{"no_issues_found": true}

## Reviewer stderr (<TMPDIR>/codex-primary-plan-requirements-output.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-requirements-output.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh cursor FAILED failed (exit 2)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/cursor-plan-dyn-commit-guard-collision-output-phase3.txt|TOOL=cursor|STATUS=FAILED|EXIT_CODE=2|FAILURE_REASON=Process failed with exit code 2

## Reviewer output (<TMPDIR>/cursor-plan-dyn-commit-guard-collision-output-phase3.txt)

(file missing: <TMPDIR>/cursor-plan-dyn-commit-guard-collision-output-phase3.txt)

## Reviewer stderr (<TMPDIR>/cursor-plan-dyn-commit-guard-collision-output-phase3.txt.diag)

(file missing: <TMPDIR>/cursor-plan-dyn-commit-guard-collision-output-phase3.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh cursor FAILED failed (exit 2)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/cursor-plan-dyn-line-target-accuracy-output-phase3.txt|TOOL=cursor|STATUS=FAILED|EXIT_CODE=2|FAILURE_REASON=Process failed with exit code 2

## Reviewer output (<TMPDIR>/cursor-plan-dyn-line-target-accuracy-output-phase3.txt)

(file missing: <TMPDIR>/cursor-plan-dyn-line-target-accuracy-output-phase3.txt)

## Reviewer stderr (<TMPDIR>/cursor-plan-dyn-line-target-accuracy-output-phase3.txt.diag)

(file missing: <TMPDIR>/cursor-plan-dyn-line-target-accuracy-output-phase3.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh codex FAILED failed (exit 2)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-dyn-line-target-accuracy-output-phase3.txt|TOOL=codex|STATUS=FAILED|EXIT_CODE=2|FAILURE_REASON=Process failed with exit code 2

## Reviewer output (<TMPDIR>/codex-primary-plan-dyn-line-target-accuracy-output-phase3.txt)

(file missing: <TMPDIR>/codex-primary-plan-dyn-line-target-accuracy-output-phase3.txt)

## Reviewer stderr (<TMPDIR>/codex-primary-plan-dyn-line-target-accuracy-output-phase3.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-dyn-line-target-accuracy-output-phase3.txt.diag)

  ```

### Warnings

- **Step design Step 3 (degraded-aggregator salvage) — plan-review-loop.sh zero-findings-degraded-panel failed (exit 0)**:
  ```
Step 3 plan-review panel ran DEGRADED (Codex unavailable + cost-fallback-exceeded-threshold blocked the Claude fallback tier; COLLECT_OK_COUNT=6, COLLECT_FAILURE_COUNT=8). LOOP_STATUS=zero-findings-degraded-panel and AGGREGATOR_STATUS=skipped-empty-input, so the formal voting/aggregation did not run.

8 of 10 static reviewers genuinely returned {"no_issues_found": true}. Three slots produced substantive reviewer output that the empty-input aggregator dropped:
- cursor-plan-pragmatic (important, correctness)
- cursor-plan-dyn-line-target-accuracy (important + nit, correctness)
- codex-primary-plan-dyn-line-target-accuracy phase2 (important, correctness; agrees with cursor-dyn)

Main agent verified all three against the source and applied them directly to plan.txt (degraded-aggregator salvage, not formal Gate B):
1. Option B follow-up commit: require set -euo pipefail-safe `if ... && ...; then ... else larch_err; fi` guards (review-and-fix.sh is set -e at line 4); bare commands would abort the script and skip warn-and-continue.
2. Option B insertion anchor corrected: after commit_sha (line 460), before the `fi` at line 461 that closes the round_num>0 branch — NOT line 464 (shared/success block outside the branch; would break Decision 5 round-mode-only scope).
3. test-review-and-fix.sh anchor corrected: use run_orchestrator_case / run_review_and_fix --round-num 1 (~336–361), not a direct apply_findings_with_coder call or the findings-mode setup (303–324).

Plan re-emitted (DIFF_LINES=190) and re-validated (VALIDATE_STATUS=ok) after the salvage.
  ```
