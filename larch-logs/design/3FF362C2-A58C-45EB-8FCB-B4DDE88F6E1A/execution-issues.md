### External Reviewer Issues

- **Step design Step 3 — collect-results cursor NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/cursor-plan-requirements-output.txt|TOOL=cursor|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair

## Reviewer output (<TMPDIR>/cursor-plan-requirements-output.txt)

Reviewing the plan against the issue scope and tracing the cited code paths.
schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	completeness	skills/implement/SKILL.md:580-584	Rejected tally count has no mandated mechanical pre-tally read of rejected-findings.md	Approved outline required a Bash probe for rejected headings; the plan only adds prose guidance. The orchestrator can still pass --rejected 0 while ### [Code Review] Self-review headings exist, recreating under-reporting for the rejected side.	Before Step 5 item 9, require an in-turn Read or Grep of $IMPLEMENT_TMPDIR/rejected-findings.md, count exact ### [Code Review] Self-review headings, and substitute that integer into --rejected. Do not add a new Bash fence.
2	in_scope	important	risk-integration	docs/run-logs.md:317-322	Plan omits reconciling self-review semantics with the cumulative JSONL-derived tally paragraph	The general code-review-tally section states accepted_count/rejected_count are cumulative and derived from review-findings-full.jsonl. Self-review uses rounds=1, prompt-side counts, and an empty JSONL sentinel. Docs-only bullets without carving out panel vs self-review leave contradictory semantics.	When updating mode: self-review, explicitly carve out panel review: keep cumulative/JSONL wording for panel runs; state self-review counts come from inline orchestrator accounting and JSONL may stay empty.
3	out_of_scope	latent	risk-integration	python/review_and_fix.py:2445-2514	Plan does not note #4617 merge-order dependency from the issue	Issue suggested landing #4617 first because both touch python/test_review_and_fix.py tally paths. Parallel work risks merge conflicts but does not break the tally-only SKILL fix itself.	Record in plan Approach or Edge cases that implementation should rebase after #4617 when both touch test_review_and_fix.py.

1. **completeness** `skills/implement/SKILL.md:580-584` — Rejected tally count has no mandated mechanical pre-tally read of `rejected-findings.md`. The approved outline called for a Bash probe; the plan only adds prose guidance, so `--rejected 0` can still be passed when self-review headings exist. **Suggested revision:** Before Step 5 item 9, require an in-turn Read or Grep of `$IMPLEMENT_TMPDIR/rejected-findings.md`, count exact `### [Code Review] Self-review` headings, and substitute that integer into `--rejected` (no new Bash fence).

2. **risk-integration** `docs/run-logs.md:317-322` — The plan documents self-review semantics but does not reconcile them with the general paragraph that tallies are cumulative and JSONL-derived. **Suggested revision:** Carve out panel vs self-review: panel keeps cumulative/JSONL wording; self-review documents prompt-side counts and empty JSONL sentinel.

3. **[OUT_OF_SCOPE] risk-integration** `python/review_and_fix.py:2445-2514` — The plan does not note the issue’s #4617 merge-order dependency. **Suggested revision:** Add a short note to rebase after #4617 when both touch `test_review_and_fix.py`.
## Reviewer stderr (<TMPDIR>/cursor-plan-requirements-output.txt.diag)

(empty: <TMPDIR>/cursor-plan-requirements-output.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/cursor-plan-requirements-output.txt.stderr-tail)

(file missing: <TMPDIR>/cursor-plan-requirements-output.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/cursor-plan-requirements-output.txt.launch-stderr)

⏳ cursor agent: still running (1m elapsed)
✓ cursor agent: completed (exit code 0, output 3411 bytes)
  ```

- **Step design Step 3 — collect-results cursor NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/cursor-plan-arch-output.txt|TOOL=cursor|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair

## Reviewer output (<TMPDIR>/cursor-plan-arch-output.txt)

Reviewing the plan against the codebase and reading the cited files.
{"no_issues_found": true}
## Reviewer stderr (<TMPDIR>/cursor-plan-arch-output.txt.diag)

(empty: <TMPDIR>/cursor-plan-arch-output.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/cursor-plan-arch-output.txt.stderr-tail)

(file missing: <TMPDIR>/cursor-plan-arch-output.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/cursor-plan-arch-output.txt.launch-stderr)

⏳ cursor agent: still running (1m elapsed)
⏳ cursor agent: still running (2m elapsed)
⏳ cursor agent: still running (3m elapsed)
✓ cursor agent: completed (exit code 0, output 413 bytes)
  ```

- **Step design Step 3 — collect-results codex NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-plan-generic-output.txt|TOOL=codex|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair

## Reviewer output (<TMPDIR>/codex-plan-generic-output.txt)

schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	out_of_scope	latent	requirements	python/audit_runs.py:804-809; skills/fluff-analysis/scripts/fluff-analysis.py:337-350	[OUT_OF_SCOPE] The approved tally-only scope leaves JSONL-only analysis surfaces blind to nonzero self-review findings	A self-review run with accepted_count > 0 and an empty review-findings-full.jsonl will show correct tally/final-summary, but audit category-stats and fluff-analysis still read zero structured findings	Track a follow-up to either populate self-review JSONL records or teach these consumers an explicit self-review tally-only path.
## Reviewer stderr (<TMPDIR>/codex-plan-generic-output.txt.diag)

(file missing: <TMPDIR>/codex-plan-generic-output.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/codex-plan-generic-output.txt.stderr-tail)

(file missing: <TMPDIR>/codex-plan-generic-output.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/codex-plan-generic-output.txt.launch-stderr)

⏳ codex agent: still running (1m elapsed)
⏳ codex agent: still running (2m elapsed)
⏳ codex agent: still running (3m elapsed)
✓ codex agent: completed (exit code 0, output 659 bytes)
  ```
