### External Reviewer Issues

- **Step design Step 3 — collect-agent-results.sh cursor FAILED failed (exit 2)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/cursor-plan-arch-output-phase3.txt|TOOL=cursor|STATUS=FAILED|EXIT_CODE=2|FAILURE_REASON=Process failed with exit code 2

## Reviewer output (<TMPDIR>/cursor-plan-arch-output-phase3.txt)

(file missing: <TMPDIR>/cursor-plan-arch-output-phase3.txt)

## Reviewer stderr (<TMPDIR>/cursor-plan-arch-output-phase3.txt.diag)

(file missing: <TMPDIR>/cursor-plan-arch-output-phase3.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh codex SENTINEL_TIMEOUT failed (exit 124)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-edge-output.txt|TOOL=codex|STATUS=SENTINEL_TIMEOUT|EXIT_CODE=124|FAILURE_REASON=Process did not complete (sentinel file missing — possible crash or system kill)

## Reviewer output (<TMPDIR>/codex-primary-plan-edge-output.txt)

schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	security	SECURITY.md:234	Plan omits SECURITY.md sync while removing clock-fatal exit, per-entry find fail-closed, and depth-5 activity scan	Auditors/operators still read depth-5 / date-fatal / per-entry skip guarantees; trust model diverges from post-change cleanup (including silent global find no-op)	Add SECURITY.md to Files to modify: replace depth-5 and date-fatal prose with top-level mtime via find -mtime, document exit 0 on enumeration failure, keep symlink and dangling-reap bullets
1	in_scope	important	correctness	plan.txt:73-83	Acceptance requires make test-cleanup but plan does not wire the harness into Makefile	Repo has skills/cleanup/scripts/test-cleanup.sh and docs/linting.md documents make test-cleanup, yet Makefile has no test-cleanup target and test-harnesses-12 does not invoke it; PR can pass relevant-checks while new cases never run in CI	Add Makefile step: test-cleanup target, .PHONY entry, and test-harnesses-12 prerequisite (or fix acceptance to bash skills/cleanup/scripts/test-cleanup.sh and align docs)

1. **[security]** `SECURITY.md:234` — Plan omits `SECURITY.md` while dropping clock-fatal exit, per-entry find fail-closed, and the depth-5 scan. The security paragraph still documents those behaviors; post-change cleanup can exit 0 with zero removals when enumeration `find` fails (stderr swallowed). **Suggested revision:** Add `SECURITY.md` to the plan file list and rewrite the `/cleanup` retention bullet for top-level `find -mtime`, no `date +%s` gate, and enumeration-failure behavior.

2. **[correctness]** `plan.txt:73-83` (acceptance / testing strategy) — Acceptance criterion and testing strategy require `make test-cleanup`, but the plan’s file list does not touch `Makefile`. There is no `test-cleanup` target today; `test-harnesses-12` runs `test-cleanup-tmpdir` only. Updated harness cases would not run under `make lint` unless wired. **Suggested revision:** Add a minimal Makefile subsection (target + shard) or change acceptance to invoke `bash skills/cleanup/scripts/test-cleanup.sh` explicitly and fix `docs/linting.md` if the target is intentionally absent.

## Reviewer stderr (<TMPDIR>/codex-primary-plan-edge-output.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-edge-output.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh codex SENTINEL_TIMEOUT failed (exit 124)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-innovation-output.txt|TOOL=codex|STATUS=SENTINEL_TIMEOUT|EXIT_CODE=124|FAILURE_REASON=Process did not complete (sentinel file missing — possible crash or system kill)

## Reviewer output (<TMPDIR>/codex-primary-plan-innovation-output.txt)

schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	security	SECURITY.md:234	Plan omits SECURITY.md while retention semantics change	Paragraph still documents depth-5 newest-activity scan per-entry find fail-closed skip date +%s fatal exit and -L guard; post-PR code uses top-level find -mtime no clock-fatal path and ! -type l — auditors and operators read stale trust-boundary text	Add ### UPDATED: SECURITY.md:234 — replace depth-5/date/per-entry-scan sentences with top-level mtime via find -mtime +N note tmp entries use ! -type l (not -L on glob) and drop date-fatal / per-entry activity-scan failure bullets; add SECURITY.md to cleanup.md Edit-in-sync list

1. **[security]** `SECURITY.md:234` — The plan updates `cleanup.md`, `SKILL.md`, and three `docs/*` files but not `SECURITY.md`, even though AGENTS.md requires a security-doc sync when retention/deletion semantics change. The existing paragraph still describes depth-5 newest activity, per-entry find fail-closed skips, and `date +%s` fatal refusal — all removed or replaced in the proposed `cleanup.sh`. **Suggested revision:** Add a `### UPDATED: SECURITY.md` step (same minimal wording as the other doc edits) and list `SECURITY.md` in `cleanup.md` Edit-in-sync.

## Reviewer stderr (<TMPDIR>/codex-primary-plan-innovation-output.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-innovation-output.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh codex SENTINEL_TIMEOUT failed (exit 124)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-pragmatic-output.txt|TOOL=codex|STATUS=SENTINEL_TIMEOUT|EXIT_CODE=124|FAILURE_REASON=Process did not complete (sentinel file missing — possible crash or system kill)

## Reviewer output (<TMPDIR>/codex-primary-plan-pragmatic-output.txt)

schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	security	SECURITY.md:234	Plan omits SECURITY.md sync while retention semantics and fail-closed behavior change	After landing, SECURITY.md still documents depth-5 newest-activity, fatal `date +%s` refusal, per-entry scan fail-closed skips, and `-L` guards — contradicting the new top-level `find -mtime` model and silent `find` error swallowing; auditors and operators misread deletion guarantees	Add SECURITY.md to the file list: rewrite the `/cleanup` paragraph for top-level mtime eligibility, drop clock-fatal and per-entry activity-scan failure claims, note `! -type l` symlink skip and accepted top-level-stale/deep-fresh deletion; add SECURITY.md to cleanup.md Edit-in-sync if that list is touched

**1. [security]** `SECURITY.md:234` — The plan updates `skills/cleanup/SKILL.md`, `cleanup.md`, and three docs files but not `SECURITY.md`, even though `AGENTS.md` requires updating it when security-relevant behavior changes. The existing paragraph still describes depth-5 newest activity, fatal exit when `date +%s` fails, and per-entry `find` failures that warn and skip deletion — all removed or inverted in the proposed script. **Suggested revision:** Add an `### UPDATED: SECURITY.md` step that rewrites the `/cleanup` trust-boundary paragraph to match top-level `find -mtime`, documents the intentional deep-fresh/top-level-stale tradeoff, and drops obsolete fail-closed claims.

## Reviewer stderr (<TMPDIR>/codex-primary-plan-pragmatic-output.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-pragmatic-output.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh codex SENTINEL_TIMEOUT failed (exit 124)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-requirements-output.txt|TOOL=codex|STATUS=SENTINEL_TIMEOUT|EXIT_CODE=124|FAILURE_REASON=Process did not complete (sentinel file missing — possible crash or system kill)

## Reviewer output (<TMPDIR>/codex-primary-plan-requirements-output.txt)

schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	security	SECURITY.md:234	Plan omits SECURITY.md while retention semantics change	SECURITY.md still documents depth-5 newest-activity, per-entry find fail-closed skip, and clock-fatal refusal; auditors and operators get the wrong /cleanup trust model after top-level-mtime rewrite	Add SECURITY.md to Files to modify: replace depth-5/clock/fail-closed bullets with top-level mtime via find -mtime, note accepted deep-only staleness (decision #2), and keep symlink-skip plus dangling reap language aligned with cleanup.md

1. **[security]** `SECURITY.md:234` — Plan omits `SECURITY.md` while retention semantics change. **Concern:** `SECURITY.md` still documents depth-5 newest-activity, per-entry find fail-closed skip, and clock-fatal refusal. **Suggested revision:** Add `SECURITY.md` to the file list; align the `/cleanup` paragraph with the proposed top-level-mtime contract (drop clock-fatal and descendant-scan bullets; document decision #2).

## Reviewer stderr (<TMPDIR>/codex-primary-plan-requirements-output.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-requirements-output.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh cursor FAILED failed (exit 2)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/cursor-plan-dyn-shell-compat-output-phase3.txt|TOOL=cursor|STATUS=FAILED|EXIT_CODE=2|FAILURE_REASON=Process failed with exit code 2

## Reviewer output (<TMPDIR>/cursor-plan-dyn-shell-compat-output-phase3.txt)

(file missing: <TMPDIR>/cursor-plan-dyn-shell-compat-output-phase3.txt)

## Reviewer stderr (<TMPDIR>/cursor-plan-dyn-shell-compat-output-phase3.txt.diag)

(file missing: <TMPDIR>/cursor-plan-dyn-shell-compat-output-phase3.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh codex FAILED failed (exit 2)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-dyn-shell-compat-output-phase3.txt|TOOL=codex|STATUS=FAILED|EXIT_CODE=2|FAILURE_REASON=Process failed with exit code 2

## Reviewer output (<TMPDIR>/codex-primary-plan-dyn-shell-compat-output-phase3.txt)

(file missing: <TMPDIR>/codex-primary-plan-dyn-shell-compat-output-phase3.txt)

## Reviewer stderr (<TMPDIR>/codex-primary-plan-dyn-shell-compat-output-phase3.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-dyn-shell-compat-output-phase3.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh cursor FAILED failed (exit 2)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/cursor-plan-dyn-contract-drift-output-phase3.txt|TOOL=cursor|STATUS=FAILED|EXIT_CODE=2|FAILURE_REASON=Process failed with exit code 2

## Reviewer output (<TMPDIR>/cursor-plan-dyn-contract-drift-output-phase3.txt)

(file missing: <TMPDIR>/cursor-plan-dyn-contract-drift-output-phase3.txt)

## Reviewer stderr (<TMPDIR>/cursor-plan-dyn-contract-drift-output-phase3.txt.diag)

(file missing: <TMPDIR>/cursor-plan-dyn-contract-drift-output-phase3.txt.diag)

  ```

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

- **Step design Step 3 — collect-agent-results.sh codex SENTINEL_TIMEOUT failed (exit 124)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-pragmatic-output.txt|TOOL=codex|STATUS=SENTINEL_TIMEOUT|EXIT_CODE=124|FAILURE_REASON=Process did not complete (sentinel file missing — possible crash or system kill)

## Reviewer output (<TMPDIR>/codex-primary-plan-pragmatic-output.txt)

{"no_issues_found": true}

## Reviewer stderr (<TMPDIR>/codex-primary-plan-pragmatic-output.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-pragmatic-output.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh cursor FAILED failed (exit 2)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/cursor-plan-requirements-output-phase3.txt|TOOL=cursor|STATUS=FAILED|EXIT_CODE=2|FAILURE_REASON=Process failed with exit code 2

## Reviewer output (<TMPDIR>/cursor-plan-requirements-output-phase3.txt)

(file missing: <TMPDIR>/cursor-plan-requirements-output-phase3.txt)

## Reviewer stderr (<TMPDIR>/cursor-plan-requirements-output-phase3.txt.diag)

(file missing: <TMPDIR>/cursor-plan-requirements-output-phase3.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh codex SENTINEL_TIMEOUT failed (exit 124)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-dyn-find-portability-output.txt|TOOL=codex|STATUS=SENTINEL_TIMEOUT|EXIT_CODE=124|FAILURE_REASON=Process did not complete (sentinel file missing — possible crash or system kill)

## Reviewer output (<TMPDIR>/codex-primary-plan-dyn-find-portability-output.txt)

{"no_issues_found": true}

## Reviewer stderr (<TMPDIR>/codex-primary-plan-dyn-find-portability-output.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-dyn-find-portability-output.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh codex SENTINEL_TIMEOUT failed (exit 124)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-dyn-doc-drift-output.txt|TOOL=codex|STATUS=SENTINEL_TIMEOUT|EXIT_CODE=124|FAILURE_REASON=Process did not complete (sentinel file missing — possible crash or system kill)

## Reviewer output (<TMPDIR>/codex-primary-plan-dyn-doc-drift-output.txt)

{"no_issues_found": true}

## Reviewer stderr (<TMPDIR>/codex-primary-plan-dyn-doc-drift-output.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-dyn-doc-drift-output.txt.diag)

  ```

### Warnings

- **Step design Step 3 — plan-review-loop.sh (degraded panel) failed (exit 0)**:
  ```
Step 3 — plan-review panel degraded: Codex unavailable + Cursor cost-fallback; ~7/14 reviewer slots returned empty/unparseable structured rows across 2 rounds. Round 1 accepted 2 important findings (Makefile test-cleanup wiring + SECURITY.md); round 2 zero-findings-degraded-panel.
  ```
