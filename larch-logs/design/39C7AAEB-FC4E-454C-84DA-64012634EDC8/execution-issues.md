### External Reviewer Issues

- **findings aggregator**: merged output failed validation; leaving <TMPDIR>/findings-in-scope.md unchanged. See <TMPDIR>/aggregator-validate.stderr.

- **Step design Step 3 — collect-results cursor NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/plan-review/round-4/cursor-plan-requirements-output.txt|TOOL=cursor|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair

## Reviewer output (<TMPDIR>/plan-review/round-4/cursor-plan-requirements-output.txt)

Reading the plan and verifying it against the feature requirements and referenced codebase paths.
schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	completeness	skills/design/references/design-outline.md:30-38	Early lazy load and outline composition omit parsed guideline entries	Issue requires loading ARCHITECTURAL_GUIDELINES.md early alongside Design Mindset to bias /design like Design Mindset does. Plan adds a Design Mindset pointer and gate deviation notes at Step 1d.7, but design-outline Inputs still list only feature-description, discussion-round1, and brainstorm. Outline is composed before the approval prompt without reading guideline entries, so Round 1 (Steps 1c/1d) and outline drafting are not biased; Step 1d.7 only post-hoc checks deviations after the outline already exists.	Add one early helper read when Design Mindset is processed (or at Step 1d.7 entry before Output). Add parsed entries to design-outline Inputs when present, mirroring brainstorm.md consumption. Keep the helper-only load rule.
2	in_scope	important	correctness	skills/implement/SKILL.md:206-221	/implement Phase A never emits operator-visible warnings	Issue requires /implement to warn on deviations (non-blocking). Phase A persists orchestrator-authored text via write-staged-assessment and defers surfacing to Phase B PR body and final_report.py. The plan does not require printing deviation warnings to chat or appending them to execution-issues.md when assessment completes. A run can finish Phase A with deviations recorded only in tmpdir artifacts that never reach the operator if Phase B pin or ship is skipped (Step 12d bail after 7a, pin failure, or stale note).	At Phase A completion, print clean or deviation warnings to chat (same content as staged assessment) and append a Warnings entry to execution-issues.md. Treat PR/final-summary append as optional durable echo, not the sole warning channel.
3	in_scope	important	architecture	plan.txt:35-63	[SCOPE-REDUCTION] Two-phase HEAD pinning plus PR and final-summary sections exceed issue scope	Issue acceptance requires /implement to warn on deviations only. The plan adds Phase B pin_note_from_staged, HEAD_SHA consumption gates, invalidate on CI-fix drift, ship.py and final_report.py integration, and three post-7a Bash fences (~920 diff_lines). That machinery exists mainly to append a guideline section to PR body and committed final-summary, which the issue never requires.	Slim to minimum: Phase A read, materialize-diff, orchestrator judgment, immediate chat plus execution-issues warnings. Drop pin_note_from_staged, compose_pr_body architectural_guidelines_note, final_report note append, and related HEAD-drift invalidation unless a follow-up issue explicitly requires durable PR/summary surfacing.
4	in_scope	important	correctness	skills/design/references/design-outline.md:78-80	--skip-approve rewrite in design-outline.md is incomplete versus SKILL.md	SKILL.md narrows the Step 1d.7 carve-out to run Output, guideline consultation, and gate presentation before auto-approve. design-outline.md Approval prompt still auto-approves immediately on skip_approve_requested (writes .outline-approved and proceeds without AskUserQuestion) with no Output or guideline step. Plan updates for design-outline.md only add note-print rules, not a rewrite of this branch.	--skip-approve runs outline Output and guideline consultation first, prints the applicable note, then writes .outline-approved and the auto-approval breadcrumb. Update design-outline.md Approval prompt to match SKILL.md explicitly.

## Findings

**1. Early lazy load and outline composition omit parsed guideline entries** (`skills/design/references/design-outline.md:30-38`, completeness)

Issue requires loading `ARCHITECTURAL_GUIDELINES.md` early alongside Design Mindset to bias `/design`. The plan adds a Design Mindset pointer and gate deviation notes at Step 1d.7, but `design-outline.md` Inputs still list only `feature-description.txt`, `discussion-round1.md`, and `brainstorm.md`. Outline is composed before the approval prompt without reading guideline entries, so Round 1 (Steps 1c/1d) and outline drafting are not biased; Step 1d.7 only post-hoc checks deviations after the outline exists.

**Suggested revision:** Add one early helper read when Design Mindset is processed (or at Step 1d.7 entry before Output). Add parsed entries to `design-outline` Inputs when present, mirroring `brainstorm.md` consumption.

**2. `/implement` Phase A never emits operator-visible warnings** (`skills/implement/SKILL.md:206-221`, correctness)

Issue requires `/implement` to warn on deviations (non-blocking). Phase A persists orchestrator-authored text via `write-staged-assessment` and defers surfacing to Phase B PR body and `final_report.py`. The plan does not require printing deviation warnings to chat or appending them to `execution-issues.md` when assessment completes. A run can finish Phase A with deviations recorded only in tmpdir artifacts that never reach the operator if Phase B pin or ship is skipped.

**Suggested revision:** At Phase A completion, print clean or deviation warnings to chat and append a `Warnings` entry to `execution-issues.md`. Treat PR/final-summary append as optional durable echo, not the sole warning channel.

**3. [SCOPE-REDUCTION] Two-phase HEAD pinning plus PR and final-summary sections exceed issue scope** (`plan.txt:35-63`, architecture)

Issue acceptance requires `/implement` to warn on deviations only. The plan adds Phase B `pin_note_from_staged`, `HEAD_SHA` consumption gates, invalidate-on-drift, `ship.py`/`final_report.py` integration, and three post-7a Bash fences (~920 `diff_lines`). That machinery exists mainly to append a guideline section to PR body and committed final-summary, which the issue never requires.

**Suggested revision:** Slim to minimum: Phase A read, `materialize-diff`, orchestrator judgment, immediate chat plus `execution-issues` warnings. Drop `pin_note_from_staged`, `compose_pr_body` note parameter, `final_report` note append, and related HEAD-drift invalidation unless a follow-up issue explicitly requires durable PR/summary surfacing.

**4. `--skip-approve` rewrite in `design-outline.md` is incomplete versus `SKILL.md`** (`skills/design/references/design-outline.md:78-80`, correctness)

`SKILL.md` narrows the Step 1d.7 carve-out to run Output, guideline consultation, and gate presentation before auto-approve. `design-outline.md` Approval prompt still auto-approves immediately on `skip_approve_requested`. Plan updates for `design-outline.md` only add note-print rules, not a rewrite of this branch.

**Suggested revision:** `--skip-approve` runs outline Output and guideline consultation first, prints the applicable note, then writes `.outline-approved` and the auto-approval breadcrumb. Update `design-outline.md` Approval prompt to match `SKILL.md` explicitly.
## Reviewer stderr (<TMPDIR>/plan-review/round-4/cursor-plan-requirements-output.txt.diag)

(empty: <TMPDIR>/plan-review/round-4/cursor-plan-requirements-output.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/plan-review/round-4/cursor-plan-requirements-output.txt.stderr-tail)

(file missing: <TMPDIR>/plan-review/round-4/cursor-plan-requirements-output.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/plan-review/round-4/cursor-plan-requirements-output.txt.launch-stderr)

⏳ cursor agent: still running (1m elapsed)
⏳ cursor agent: still running (2m elapsed)
✓ cursor agent: completed (exit code 0, output 7326 bytes)
  ```
