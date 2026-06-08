## Decision 1: New flag surface
- **Question**: What is the new flag and its short form?
- **Resolution**: Add public boolean flag `--skip-approve` with short alias `-s` (default false). `-s` is free (existing short flags: `-p`/--partition only; `-m` was removed). When set, /design auto-approves two operator gates: Step 1d.7 outline-approval and Step 4b Gate C final-plan approval.
- **Source**: user

## Decision 2: Scope of the skip
- **Question**: Exactly which prompts are skipped?
- **Resolution**: ONLY the two approval AskUserQuestion gates — Step 1d.7 outline-approval (Approve/Refine/Cancel) and Step 4b Gate C final approval (Approve/See full plan/Discuss further/Re-run). All other AskUserQuestion calls the model may raise (Step 1c clarifying, Step 1d round-1, degraded-tools gate, plan-size hard/drift brakes, dirty-tree recovery, validator escalation, decomposition panel) still fire normally.
- **Source**: user

## Decision 3: Visibility under --skip-approve
- **Question**: Does the outline / final plan still print when the prompt is skipped?
- **Resolution**: Yes. Print the proposed outline (1d.7) and the Gate C final-plan preview as usual, each followed by an auto-approve breadcrumb (`⏩ ... auto-approved (--skip-approve)`). Skip only the AskUserQuestion; keep the full audit trail in chat.
- **Source**: user

## Decision 4: Rename existing --approve flag
- **Question**: The new --skip-approve sits next to the existing --approve (restore per-round Gate B apply prompt). How to disambiguate?
- **Resolution**: Rename public flag `--approve` → `--per-round-approval`. The two flags are orthogonal (different gates; may co-occur). Internal binding/persisted key `approve_requested` is UNCHANGED (only the public token + docs change) to keep churn minimal.
- **Source**: user

## Decision 5: Backward-compat of the rename
- **Question**: How should the old `--approve` spelling behave post-rename?
- **Resolution**: Hard cutover — `--approve` becomes an unknown public flag (hard error before Step 0), matching the removed `--manual`/`-m` precedent. No deprecated alias. Mutual-exclusion ("at most one ... duplicate is a hard error") now applies to `--per-round-approval`.
- **Source**: user

## Decision 6: Sequencing
- **Question**: Overlap with in-flight issues?
- **Resolution**: Proceed now. #3619 [DESIGNING] edits SKILL.md only in the Step 3 dispatch region (disjoint from the flag-table / 1d.7 / Gate C regions here) and shares no scripts. Native blocked-by edges already wired: #3735 blocks #3681 and #3668 (py-migration ports of design lifecycle + session/state).
- **Source**: user
