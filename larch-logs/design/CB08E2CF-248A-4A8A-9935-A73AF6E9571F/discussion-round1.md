# Discussion Round 1 — scope boundaries and hard constraints

Issue #6821 "Step 8 cutover and inline-fallback removal" (partition piece 4 of 4 from #6804).
No user clarifying questions were required: the partition acceptance criteria are explicit and self-consistent, and the one external unknown (Piece 3 dependency) was resolved by tree inspection. All decisions below were resolved from codebase/docs evidence.

## Decision 1: Piece 3 prerequisite infrastructure is present in the tree
- **Question**: Is the bgjob fixer lane that this cutover depends on (blocked-by Piece 3) already present, so the plan targets a real cutover rather than building the lane?
- **Resolution**: Yes. `skills/implement/scripts/step-8-ci-fixer.sh` is a complete dormant bgjob waterfall wrapper (identity-bound per-tier bgjob, stale HEAD/run-id/tier/attempt/fingerprint rejection, `implement.ci_recovery_fixer` waterfall codex→cursor→claude, `--invariant-evidence`, compact `RESULT=reship|retry-next-tool|operator-bail` envelope, `budget-s 5400`). The `python/cli.py ci fixer-lane` command, `_ci_launcher.py`, the `ci_recovery_fixer` role, and `FIXER_LANE_TIMEOUT_SEC=1800` all exist. The wrapper is exercised by `test-step-8-ci-fixer.sh` and `test_implement_dispatch.py` but is NOT yet invoked by the active Step 8 path.
- **Source**: codebase

## Decision 2: Piece 4 = cutover + Step 8 inline-fallback removal (scope IN)
- **Question**: Which of the three original #6804 "Required changes" does this piece own?
- **Resolution**: IN scope — (a) the Step 8 `ci-fix` cutover from the Agent-tool fixer path onto `step-8-ci-fixer.sh` (Required change 1, "cutover" half); (b) removal of the Step 8 post-bail 10-attempt inline main-agent fallback and `fallback-attempts.count` routing (Required change 3.2); (c) the now-dead orchestrator-level `ci distill-log` pre-spawn digest and its BAIL_CLASS routing on the default path, since the lane owns evidence internally (Required change 3.3). `LARCH_CI_FIXER=0` remains the sole sanctioned inline path with its existing 30-attempt budget, unchanged.
- **Source**: codebase (firm headings: `ship-pr-ci-fix.md`, `SKILL.md`, `python/larch/core/config.py`, `python/tests/core/test_config.py`) + acceptance criteria

## Decision 3: Checks-loop timeout + Step 3/5/6 main-agent-edit are OUT of scope (sibling pieces)
- **Question**: Does this piece also resize the checks repair-loop external-lane budget (300s→1800s) and close the Step 3/5/6 `main-agent-edit` leak?
- **Resolution**: No — out of scope. Required change 2 (`_RUN_EXTERNAL_TIMEOUT` in `python/larch/implement/checks_lint_fix.py`) and Required change 3.1 (Step 3/5/6 checks repair-loop) are NOT in this piece's firm headings and belong to sibling partition pieces. `checks_lint_fix.py` is not a firm heading. The plan must not touch the checks repair-loop.
- **Source**: codebase (firm-heading diff vs. original feature context)

## Decision 4: Hard constraint — `LARCH_CI_FIXER=0` kill-switch behavior is frozen
- **Question**: Does the cutover also tighten the `LARCH_CI_FIXER=0` inline path?
- **Resolution**: No. Acceptance states `LARCH_CI_FIXER=0` remains "the sole sanctioned inline path with its existing 30-attempt budget." `CI_FIXER_KILL_SWITCH_INLINE_MAX_ATTEMPTS=30` and the kill-switch inline loop in `ship-pr-ci-fix.md` are preserved verbatim. They are the explicit single exception to "main-agent edits removed."
- **Source**: acceptance criteria

## Decision 5: Hard constraint — remove Agent-tool fixer path, not guard it
- **Question**: Keep the Agent-tool fixer behind a guard, or remove it?
- **Resolution**: Remove. Acceptance lists "Agent dispatch ... main-agent-authored CI-fix commits ... the post-bail 10-attempt loop, and `fallback-attempts.count` routing" as removed. The Agent-tool spawn section, `CI_FIXER_AGENT_MAX_ROUNDS` (if its only consumers are the removed path), and the 10-attempt loop constant `CI_FIXER_MAIN_FALLBACK_MAX_ATTEMPTS` are candidates for removal once their consumers are gone (Step 2b will verify no remaining consumers before deleting).
- **Source**: acceptance criteria
