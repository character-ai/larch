## Decision 1: Fate of `--design-classification` on assess-plan-round.sh
- **Question**: Once tier no longer gates assessor behavior, keep `--design-classification` as an accepted-but-ignored compat no-op, or remove it entirely?
- **Resolution**: Remove it entirely. Drop the flag, its arg-parsing + validation, the now-orphaned `resolve_design_classification()` tier resolution in `assess-plan-round.sh`, the sole caller arg (`--design-classification "$WORKFLOW_PATH"`) in `design-plan-quality-assessor.sh`, and the flag's validation tests in `test-assess-plan-round.sh`. This diverges from the prior issue plan, which kept it as a no-op.
- **Source**: user

## Decision 2: Dependency / blocker status (issue lists two blockers)
- **Question**: The issue lists "Blocked by the loop-dynamics issue (no auto-apply)" and "Blocked by #3421 (Round II Phase 6 fold)". Are those resolved on current main?
- **Resolution**: Yes, unblocked. #3512 (auto-apply removal) is merged (commit 3a602099a), so plan review is review-only and Gate B is the sole apply point; the assessor compares post-Gate-B `plan.txt` vs `plan.txt-original`. The #3421 SIMPLE sketch-sentinel fold is present in the current SKILL.md Step 2a entry fence. No collision risk remains.
- **Source**: codebase

## Decision 3: Scope held fixed by the issue (not re-litigated)
- **Question**: Confirm the behavioral scope.
- **Resolution**: (a) snapshot `plan.txt-original` on SIMPLE; (b) advance the round cursor on SIMPLE; (c) run Step 3.6 assessor on SIMPLE; (d) anchor the verdict to `plan.txt-original` for BOTH tiers; (e) fire from round 1 (round-1 anchor = `plan.txt-original`); (f) SIMPLE WORSE-majority uses the same operator Continue/Stop gate as HARD. No new files, flags, or abstractions.
- **Source**: issue (fully specified)
