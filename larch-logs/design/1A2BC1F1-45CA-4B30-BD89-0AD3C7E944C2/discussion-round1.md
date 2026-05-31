## Decision 1: Which prompts get the new "override and proceed" option
- **Question**: Only the Step 2b.5 plan-size hard-trigger prompt, or also the pre-plan Step 1c/1d semantic-sprawl prompt?
- **Resolution**: BOTH. (a) Step 2b.5 Hard branch (HARD_TRIGGER_FIRED=true) and (b) the Step 1c/1d semantic-sprawl Split/Cancel prompt. The Step 2b.5 hard handler is also re-invoked from Step 3 plan review (LOOP_STATUS=plan-size-trigger), which inherits the change automatically.
- **Source**: user

## Decision 2: Guard strength on "override and proceed"
- **Question**: Single prominent-warning option, or a second confirmation step?
- **Resolution**: Single option. The anti-recommendation ("quite likely to severely degrade the quality of the reviews and the result; advised against") lives in the option label + description; selecting it proceeds immediately. No second confirmation gate.
- **Source**: user

## Decision 3: Override behavior + audit
- **Question**: Besides proceeding, what does override do?
- **Resolution**: Proceed AND append a Warnings audit entry to $DESIGN_TMPDIR/execution-issues.md recording the override (trigger reason + PLAN_LINES/DIFF_* sizes). Step 2b.5 hard override -> proceed to Step 3 plan review with the current oversized plan (same continuation as the no-trigger branch). Step 1c/1d sprawl override -> continue the normal pre-plan flow (do NOT split, do NOT cancel). Audit-log treatment mirrored on both prompts.
- **Source**: user (audit choice) + codebase (sprawl "proceed" target = continue normal flow)

## Decision 4: Option ordering (next-to-last)
- **Question**: Where does the new option appear in the list?
- **Resolution**: Next-to-last — between the Split option and Cancel. Final order on both prompts: Split / Override-and-proceed / Cancel.
- **Source**: user

## Decision 5: Non-goals / hard constraints preserved
- **Question**: What must NOT change?
- **Resolution**: (1) Hard-trigger thresholds unchanged. (2) --partition flow unchanged — the partition branch routes directly to Split-path with NO AskUserQuestion, so it gains no override option. (3) Soft-advisory (mechanical_churn) behavior unchanged. (4) Existing Split and Cancel option label text preserved verbatim so unrelated structure-test pins keep matching. (5) No new flag — the override is always shown as a choice when the prompt fires; the prominent warning is the only guardrail.
- **Source**: user (issue Out-of-scope) + codebase (partition branch has no AskUserQuestion: SKILL.md Step 2b.5 step 5)
