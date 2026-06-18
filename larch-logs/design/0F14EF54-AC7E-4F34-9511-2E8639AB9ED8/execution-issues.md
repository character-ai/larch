### External Reviewer Issues

- **Step design Step 3 — collect-results cursor NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/cursor-plan-pragmatic-output.txt|TOOL=cursor|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair

## Reviewer output (<TMPDIR>/cursor-plan-pragmatic-output.txt)

schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	completeness	Makefile:519-520	The embedded prune-nit rewrite guard test is not wired into any `make lint` harness shard	The plan adds `test_embedded_plan_review_prune_nit_uses_review_cli` but only lists a manual `pytest -k embedded_plan_review_prune_nit` run. `test-review-design-step3-loop` still filters with `embedded_review or embedded_run_step3_review or embedded_waterfall or reviewer_prune or run_legacy`, which does not match `embedded_plan_review_prune_nit`. CI can merge a broken `_rewrite_prune_asset` and deleted shell without catching rc 127 / fail-open ballot drift on `/design` plan-review.	Extend `test-review-design-step3-loop` `-k` to include `embedded_plan_review_prune_nit` or `prune_nit` (mirror how `reviewer_prune` selects the reviewer-prune guard), and mention that harness in Testing strategy.
2	in_scope	important	risk-integration	python/plan_review.py:880-906	The plan tells `_rewrite_prune_asset` to mirror reviewer-prune string replace while also preserving `LARCH_PLAN_REVIEW_PRUNE_NITS_SH`	Embedded `plan-review-loop.sh` binds `PLAN_REVIEW_PRUNE_NITS_SH="${LARCH_PLAN_REVIEW_PRUNE_NITS_SH:-…/prune-nit-findings.sh}"` and invokes it as a single executable. The reviewer-prune rewrite drops `${VAR:-default}` and swaps to a multi-token CLI array. A literal mirror leaves either a deleted default path or a one-string `python3 … review prune-nit-findings` invocation that cannot run.	Specify rewrite as: if `LARCH_PLAN_REVIEW_PRUNE_NITS_SH` is set, keep a one-entry command array from that override; else default to `(python3 "$PLUGIN_ROOT/python/cli.py" review prune-nit-findings)`; invoke with `"${PLAN_REVIEW_PRUNE_NITS_CMD[@]}"` on both decoded assets.

**1. completeness — `Makefile:519-520`**

The plan adds `test_embedded_plan_review_prune_nit_uses_review_cli` but does not attach it to a lint harness. `test-review-design-step3-loop` (shard 16) will not select that test name. A missed `_rewrite_prune_asset` edit can ship with green `make lint`.

**Suggested revision:** Extend the `test-review-design-step3-loop` `-k` filter and document it under Testing strategy.

**2. risk-integration — `python/plan_review.py:880-906`**

The plan mixes “mirror reviewer-prune rewrite” with “preserve `LARCH_PLAN_REVIEW_PRUNE_NITS_SH`”. The embedded loop uses a single-path default plus override; the CLI default is multi-argument. Literal string replace is not enough.

**Suggested revision:** Add an explicit override branch and array invocation contract in the `python/plan_review.py` plan section, not only in Failure modes.
## Reviewer stderr (<TMPDIR>/cursor-plan-pragmatic-output.txt.diag)

(empty: <TMPDIR>/cursor-plan-pragmatic-output.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/cursor-plan-pragmatic-output.txt.stderr-tail)

(file missing: <TMPDIR>/cursor-plan-pragmatic-output.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/cursor-plan-pragmatic-output.txt.launch-stderr)

⏳ cursor agent: still running (1m elapsed)
⏳ cursor agent: still running (2m elapsed)
⏳ cursor agent: still running (3m elapsed)
✓ cursor agent: completed (exit code 0, output 3036 bytes)
  ```

- **Step design Step 3 — collect-results codex NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-plan-generic-output.txt|TOOL=codex|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair

## Reviewer output (<TMPDIR>/codex-plan-generic-output.txt)

schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	safety	skills/review/scripts/prune-nit-findings.sh:195-205	Plan omits plan-mode rollback for two-file prune writes	If the Python port replaces findings.md and then the OOS file replace fails, fail-open can leave the nit removed from in-scope without an OOS copy. The shell restores the original findings file before returning skipped.	Add an explicit plan step for prune_nit_findings plan mode to preserve the original findings and OOS state on any write or replace failure before emitting STATUS=skipped.
1	in_scope	important	requirements	docs/python-migration.md:18	Plan leaves the migration playbook G1 facade note stale	After deleting review_legacy.py and python/legacy_review_shell, docs/python-migration.md would still say review_aggregate.py, review_tally.py, and compose_review.py remain facades for retained shell bodies. That conflicts with the sh-to-py definition of done.	Add docs/python-migration.md to the plan and update or supersede the G1 note to state that G2 ports aggregate, tally, emit, compose, log-phase, and prune in Python and removes the legacy review shell facade.
## Reviewer stderr (<TMPDIR>/codex-plan-generic-output.txt.diag)

(file missing: <TMPDIR>/codex-plan-generic-output.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/codex-plan-generic-output.txt.stderr-tail)

(file missing: <TMPDIR>/codex-plan-generic-output.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/codex-plan-generic-output.txt.launch-stderr)

⏳ codex agent: still running (1m elapsed)
⏳ codex agent: still running (2m elapsed)
⏳ codex agent: still running (3m elapsed)
⏳ codex agent: still running (4m elapsed)
✓ codex agent: completed (exit code 0, output 1202 bytes)
  ```

- **Step design Step 3 — collect-results cursor NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/cursor-plan-arch-output.txt|TOOL=cursor|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair

## Reviewer output (<TMPDIR>/cursor-plan-arch-output.txt)

Reading the plan and tracing the cited codebase paths to validate the proposed port.
{"no_issues_found": true}
## Reviewer stderr (<TMPDIR>/cursor-plan-arch-output.txt.diag)

(empty: <TMPDIR>/cursor-plan-arch-output.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/cursor-plan-arch-output.txt.stderr-tail)

(file missing: <TMPDIR>/cursor-plan-arch-output.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/cursor-plan-arch-output.txt.launch-stderr)

⏳ cursor agent: still running (1m elapsed)
⏳ cursor agent: still running (2m elapsed)
⏳ cursor agent: still running (3m elapsed)
⏳ cursor agent: still running (4m elapsed)
⏳ cursor agent: still running (5m elapsed)
⏳ cursor agent: still running (6m elapsed)
⏳ cursor agent: still running (7m elapsed)
⏳ cursor agent: still running (8m elapsed)
⏳ cursor agent: still running (9m elapsed)
⏳ cursor agent: still running (10m elapsed)
⏳ cursor agent: still running (11m elapsed)
✓ cursor agent: completed (exit code 0, output 430 bytes)
  ```

- **Step design Step 3 — collect-results codex NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-plan-generic-output.txt|TOOL=codex|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair

## Reviewer output (<TMPDIR>/codex-plan-generic-output.txt)

schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	requirements/completeness	python/migrated-scripts.tsv:992	Deleted python/review_legacy.py is missing from the retired-path manifest plan	The plan deletes python/review_legacy.py, but the migrated-scripts.tsv append list omits it, so the sh-to-py retirement manifest is incomplete and retired-reference lint will not guard the deleted facade	Add python/review_legacy.py with the G2 issue number to the migrated-scripts.tsv append list
1	in_scope	important	requirements/completeness	docs/python-migration.md:18	Plan leaves the migration playbook status stale	After this PR deletes the retained aggregate tally emit compose log-phase shell bodies, docs/python-migration.md would still say review_aggregate.py, review_tally.py, and compose_review.py remain CLI facades for retained shell bodies under python/legacy_review_shell	Add docs/python-migration.md to the plan and update the G1 review pipeline status to reflect the G2 in-process ports and removal of the retained shell bodies
## Reviewer stderr (<TMPDIR>/codex-plan-generic-output.txt.diag)

(file missing: <TMPDIR>/codex-plan-generic-output.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/codex-plan-generic-output.txt.stderr-tail)

(file missing: <TMPDIR>/codex-plan-generic-output.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/codex-plan-generic-output.txt.launch-stderr)

⏳ codex agent: still running (1m elapsed)
⏳ codex agent: still running (2m elapsed)
⏳ codex agent: still running (3m elapsed)
⏳ codex agent: still running (4m elapsed)
✓ codex agent: completed (exit code 0, output 1092 bytes)
  ```

- **Step design Step 3 — collect-results cursor NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/cursor-plan-requirements-output.txt|TOOL=cursor|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair

## Reviewer output (<TMPDIR>/cursor-plan-requirements-output.txt)

Reviewing the plan against the issue scope and validating cited paths in the codebase.
{"no_issues_found": true}
## Reviewer stderr (<TMPDIR>/cursor-plan-requirements-output.txt.diag)

(empty: <TMPDIR>/cursor-plan-requirements-output.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/cursor-plan-requirements-output.txt.stderr-tail)

(file missing: <TMPDIR>/cursor-plan-requirements-output.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/cursor-plan-requirements-output.txt.launch-stderr)

⏳ cursor agent: still running (1m elapsed)
⏳ cursor agent: still running (2m elapsed)
⏳ cursor agent: still running (3m elapsed)
✓ cursor agent: completed (exit code 0, output 431 bytes)
  ```
