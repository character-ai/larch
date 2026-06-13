### External Reviewer Issues

- **Step design Step 3 — collect-agent-results.sh cursor NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/cursor-plan-requirements-output.txt|TOOL=cursor|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair

## Reviewer output (<TMPDIR>/cursor-plan-requirements-output.txt)

schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	completeness	skills/design/scripts/test-design-step3-state.sh	Acceptance requires extending test-design-step3-state.sh but the plan has no UPDATED entry for it	Goals and acceptance both name test-design-step3-state.sh extension; the plan only lists it under run targeted tests, so implementers can treat harness work as done after pause-resume changes alone	Add an UPDATED test-design-step3-state.sh subsection (minimal direct-review-entry / --reentry interaction cases) or an explicit plan note that pause-resume coverage satisfies the acceptance item and step3-state modes are unchanged
2	in_scope	important	correctness	skills/design/SKILL.md:549-624	Canonical Step 3 entry and resume Bash fences still show bare wrapper calls without new flags	The post-loop matrix replaces separate raw state writes plus design-step3-review.sh --starting-round only, but lines 549-552 and 618-624 still instruct prompt-side .step3-reentry creation and a resume fence with --starting-round alone; following that leaves migrated state on prompt-side paths or omits --phase / --findings-file / --postplan-operator-continue on the launcher call	Update Step 3 entry prose and fence to use design-step3-entry.sh --reentry on Gate A / Gate C re-entry (no separate set instruction); update the Step 3 resume fence and branch bullets to a single design-step3-review.sh invocation that combines --starting-round with the branch-specific flag instead of write-then-resume
3	in_scope	important	completeness	skills/design/SKILL.md:673-677	Legacy continuation still documents a prompt-side .step3-entry-plan-printed clear before the wrapper call	Plan assigns preview cleanup to design-step3-continuation-entry.sh, but SKILL.md line 673 still says clear then run continuation-entry; grep acceptance would still find a raw clear instruction for that sentinel	Remove the clear line from legacy continuation prose; state that design-step3-continuation-entry.sh owns the clear before pause-save

### FINDING_1
**focus_area**: correctness  
**location**: `skills/design/scripts/test-design-step3-state.sh`  
**what**: Acceptance and goals require extending `test-design-step3-state.sh`, but the plan never lists that file under Files to modify/create.  
**scenario_or_breakage**: Implementers can mark the acceptance item done after only `test-design-pause-resume.sh` changes, leaving the named harness without planned coverage for re-entry marker ownership.  
**suggested_fix**: Add an `UPDATED: test-design-step3-state.sh` subsection with minimal cases, or document that pause-resume fully satisfies the acceptance criterion because no new `design-step3-state.sh` modes are added.

### FINDING_2
**focus_area**: correctness  
**location**: `skills/design/SKILL.md:549-624`  
**what**: Canonical Step 3 entry and resume Bash fences still model pre-wrapper prompt-side state writes.  
**scenario_or_breakage**: The plan moves resume state into `design-step3-review.sh`, but SKILL still shows creating `.step3-reentry` before Step 3 and a resume fence with only `--starting-round`. A literal migration leaves raw writes or drops required `--phase` / `--findings-file` / `--postplan-operator-continue` flags.  
**suggested_fix**: Change Step 3 entry to `design-step3-entry.sh --reentry` on re-entry paths; change the resume fence and branch bullets to one wrapper call that passes the branch flag with `--starting-round`.

### FINDING_3
**focus_area**: completeness  
**location**: `skills/design/SKILL.md:673-677`  
**what**: Legacy `--mode single` continuation prose still instructs a prompt-side `.step3-entry-plan-printed` clear.  
**scenario_or_breakage**: Plan migration and the final grep gate target zero raw prompt-side writes for that sentinel; leaving line 673 violates the stated acceptance criterion.  
**suggested_fix**: Delete the clear instruction; say `design-step3-continuation-entry.sh` clears the sentinel before pause-save.

### [OUT_OF_SCOPE]_1
**location**: `skills/design/scripts/design-step3-entry.md`, `skills/design/scripts/design-step2b-postplan.md`  
**what**: Wrapper contract stubs are not listed for flag documentation updates.  
**scenario_or_breakage**: Low risk; contracts are minimal and grep verification does not include them.  
**suggested_fix**: Optional follow-up issue to document new flags in sibling `.md` contracts after script changes land.

## Reviewer stderr (<TMPDIR>/cursor-plan-requirements-output.txt.diag)

(empty: <TMPDIR>/cursor-plan-requirements-output.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/cursor-plan-requirements-output.txt.stderr-tail)

(file missing: <TMPDIR>/cursor-plan-requirements-output.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/cursor-plan-requirements-output.txt.launch-stderr)

timing: WARNING: unknown task-kind: cursor-phase1-cursor-plan-requirements
  ```
### Warnings

- **Step design Step 2b.5 — python plan check-size (drift) failed (exit 0)**:
  ```
**⚠ 2b.5: plan-size — drift advisory: plan grew PLAN_LINES=521 (baseline 260, ratio 2) / DIFF_LINES=1115 (baseline 600, ratio 1.86) ≥ ×2, under absolute limits; proceeding.**
  ```
