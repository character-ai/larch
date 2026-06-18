### External Reviewer Issues

- **Step design Step 3 — collect-results cursor NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/cursor-plan-requirements-output.txt|TOOL=cursor|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair

## Reviewer output (<TMPDIR>/cursor-plan-requirements-output.txt)

Reviewing the plan against the issue scope and verifying it against the codebase.
{"no_issues_found": true}
## Reviewer stderr (<TMPDIR>/cursor-plan-requirements-output.txt.diag)

(empty: <TMPDIR>/cursor-plan-requirements-output.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/cursor-plan-requirements-output.txt.stderr-tail)

(file missing: <TMPDIR>/cursor-plan-requirements-output.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/cursor-plan-requirements-output.txt.launch-stderr)

⏳ cursor agent: still running (1m elapsed)
⏳ cursor agent: still running (2m elapsed)
✓ cursor agent: completed (exit code 0, output 426 bytes)
  ```

- **Step design Step 3 — collect-results cursor NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/cursor-plan-requirements-output.txt|TOOL=cursor|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair

## Reviewer output (<TMPDIR>/cursor-plan-requirements-output.txt)

schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	requirements	skills/design/SKILL.md:631-631	The plan lists Anti-pattern #4 and Step 3 post-loop branch edits but omits the duplicated Task tool notification boundary blocks that still require waiting for a second original-task notification after a premature one.	Those blocks still say the orchestrator MUST still wait for the original design-step3-review.sh notification and must not advance from .completed/step-3 alone. That is the prose path that drove foreground ps polling in the reported incident. If only the post-loop matrix is updated, contradictory instructions remain and recovery can stay blocked.	Add explicit plan steps to rewrite skills/design/SKILL.md:631 and the duplicate resume prose at :688 (and any other copies of MUST still wait for the original) to match the new contract: after a premature empty notification, use the one-shot terminal-sentinel foreground probe when the background recovery waiter is killed or unsuitable; when the terminal sentinel is present, proceed to normal post-notification parsing without waiting for a second notification.
1	in_scope	important	requirements	skills/design/SKILL.md:351-365	The hook and AGENTS.md/orchestrator-never updates whitelist .completed/step-final-summary for foreground recovery, but the plan does not update the Final summary block immediate-background guidance for design-step-final-summary.sh.	Approved outline scoped all three guarded immediate-background fences (step-3, step-5c, final-summary). Final summary block prose still treats notification as the only resume trigger and forbids tmpdir reads before it, with no killed-waiter or premature-notification fallback. The same premature-notification plus blocked-sentinel-check failure mode can recur on cancellation and terminal-summary paths.	Add a brief Final summary block subsection mirroring Step 5c: primary background recovery waiter when viable; otherwise one foreground probe of .completed/step-final-summary per recovery turn; proceed to marker or Read fallback when present; yield without ps polling when absent; do not wait for a second notification after a premature one.
## Reviewer stderr (<TMPDIR>/cursor-plan-requirements-output.txt.diag)

(empty: <TMPDIR>/cursor-plan-requirements-output.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/cursor-plan-requirements-output.txt.stderr-tail)

(file missing: <TMPDIR>/cursor-plan-requirements-output.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/cursor-plan-requirements-output.txt.launch-stderr)

⏳ cursor agent: still running (1m elapsed)
✓ cursor agent: completed (exit code 0, output 2562 bytes)
  ```

- **findings aggregator**: merged output failed validation; leaving <TMPDIR>/findings-in-scope.md unchanged. See <TMPDIR>/aggregator-validate.stderr.

- **Step design Step 3 — collect-results cursor NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/cursor-plan-innovation-output.txt|TOOL=cursor|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair

## Reviewer output (<TMPDIR>/cursor-plan-innovation-output.txt)

Reading the plan and validating it against the hook guard and related code.
schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	completeness	python/plan_review.py:615-615	Plan updates live review-design-step3-loop.sh but omits _LEGACY_ASSETS regeneration	pytest test_embedded_review_design_step3_loop_matches_live_script fails on every CI run after the live loop edit	Add ### UPDATED: python/plan_review.py with decode/re-encode of review-design-step3-loop.sh; keep test_embedded_review_design_step3_loop_matches_live_script green
2	in_scope	important	correctness	skills/design/scripts/design-step1e-reentry.sh:85-85	Gate B/C re-entry clears step-3 but not new step-3-terminal	Stale step-3-terminal lets marker_step_completed and foreground probes report DONE while a fresh Step 3 background run is in flight	Add .completed/step-3-terminal to the rm -f list (and mirror in embedded design-step3-state.sh direct-review/auto-continuation rm blocks)
3	in_scope	important	correctness	python/plan_review.py:106-106	Embedded design-step3-state.sh rm lists omit step-3-terminal	auto-continuation-entry and direct-review-entry clear step-3/3.5/3b but leave step-3-terminal; next Step 3 launch inherits a false terminal sentinel	Regenerate the design-step3-state.sh blob so every rm -f ... step-3 ... block also removes step-3-terminal
4	in_scope	important	risk-integration	scripts/test-implement-anti-polling-rule.sh:119-129	Anti-polling harness pins old .completed/step-3 recovery literals in skills/design/SKILL.md	After SKILL anti-pattern/Step 3 edits to step-3-terminal, make test-implement-anti-polling-rule (make lint prerequisite) fails	Update pinned strings to step-3-terminal for recovery waiters; keep separate pins for Step 3b routing on step-3
5	in_scope	important	correctness	scripts/hook-bg-poll-guard.sh:341-356	Foreground terminal probe must bypass bash_has_probe_verb before the per-dir deny loop	test -f ... forms match _PROBE_VERB_RE and stay blocked if the helper is wired after the deny loop	Wire bash_is_terminal_sentinel_foreground_probe with exit 0 immediately after bash_is_step3_recovery_waiter and before the bash_has_probe_verb loop (as planned)
6	out_of_scope	latent	architecture	plan.txt:12-12	[SCOPE-REDUCTION] step-3-terminal split is broader than the approved outline hook-only fix	The split is justified for envelope ordering but adds loop/wrapper/docs surface beyond the original hook+probe sketch	Keep the split; no action unless implementer wants a follow-up to document why loop changes are load-bearing vs hook-only
7	out_of_scope	nit	code-quality	scripts/hook-bg-poll-guard.sh:84-84	Issue scope still treats step-5c-terminal mismatch as open; repo already ships step-5c-terminal in hook and design-step5c.sh	Plan Step 5c regression adds test value only; no functional hook fix left for #4450	Accept as regression coverage only; do not re-open the resolved mismatch narrative

### Finding 1 — Embedded loop asset drift

The plan edits `review-design-step3-loop.sh` on disk, but `python/test_plan_review.py` requires byte parity with the gzip blob in `python/plan_review.py` (`test_embedded_review_design_step3_loop_matches_live_script`). Without re-encoding, `make py-test` fails even if hook changes pass.

### Finding 2 — Re-entry sentinel hygiene

`design-step1e-reentry.sh` removes `.completed/step-3` but not the new terminal sentinel. After Gate B/C discussion re-entry, a leftover `step-3-terminal` from a prior Step 3 run can satisfy `marker_step_completed` and the foreground probe while a new review is starting.

### Finding 3 — Embedded step3-state cleanup

Decoded `design-step3-state.sh` (embedded only) rm's `step-3`, `step-3.5`, and `step-3b` on `--auto-continuation-entry` and `--direct-review-entry`, but not `step-3-terminal`. The plan does not list this blob; auto-continuation re-runs inherit the same stale-terminal risk.

### Finding 4 — CI literal pins

`scripts/test-implement-anti-polling-rule.sh` hard-pins `.completed/step-3` in three `skills/design/SKILL.md` strings. The plan rewrites those to `step-3-terminal` but omits the harness file.

### Finding 5 — Probe helper ordering

`_PROBE_VERB_RE` includes `test`, so `test -f ...` probes hit the deny loop unless the new helper short-circuits first. Placement before `bash_has_probe_verb` is load-bearing; the plan states it correctly and implementers should treat it as blocking.

### Out of scope

The `step-3-terminal` split exceeds the original outline’s minimum surface, but it addresses a real ordering bug: `step3_loop_write_completed_step3` runs before `step3_loop_persist_envelope` on cap-hit and failure paths (`review-design-step3-loop.sh:690-699`), so hook release on `.completed/step-3` alone can precede a durable `.step3-review-result.env`. The split is proportionate.

The step-5c-terminal “mismatch” in the issue anchor is already fixed in tree (`hook-bg-poll-guard.sh:84`, `design-step5c.sh:295`); planned Step 5c tests are regression-only.
## Reviewer stderr (<TMPDIR>/cursor-plan-innovation-output.txt.diag)

(empty: <TMPDIR>/cursor-plan-innovation-output.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/cursor-plan-innovation-output.txt.stderr-tail)

(file missing: <TMPDIR>/cursor-plan-innovation-output.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/cursor-plan-innovation-output.txt.launch-stderr)

⏳ cursor agent: still running (1m elapsed)
⏳ cursor agent: still running (2m elapsed)
⏳ cursor agent: still running (3m elapsed)
⏳ cursor agent: still running (4m elapsed)
✓ cursor agent: completed (exit code 0, output 5450 bytes)
  ```
