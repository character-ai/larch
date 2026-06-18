## Decision 1: Clean the working tree on every failed applier attempt
- **Question**: When a coder (Cursor/Codex) apply fails, what should happen to the staged/modified changes it left behind?
- **Resolution**: Delete the failed applier's changes so the tree returns to its pre-coder state: `git reset --hard HEAD` to discard tracked edits and staging, plus precise removal of the applier's new untracked files via the existing pre-coder snapshot delta (`_round_coder_untracked_delta_paths`). Preserve unrelated untracked files (no blunt `git clean -fd`). This unblocks the subsequent rebase and gives the next applier a clean start.
- **Source**: user (requirement 1) + codebase

## Decision 2: Extend the coder waterfall to cover commit failures
- **Question**: Today only an edit failure falls through Cursor -> Codex; a commit failure returns rc=2 "coder-failed" and stalls. Should commit failures also waterfall?
- **Resolution**: Yes. Each coder attempt is edit + stage + commit. Any failure (edit OR commit) cleans the tree (Decision 1) and falls through to the next coder. When all coders are exhausted, return rc=4 main-agent-required. Commit failures no longer produce the rc=2 "coder-failed" stall.
- **Source**: user (requirement 2)

## Decision 3: Main-agent apply then autonomous resume at the next round
- **Question**: After the whole waterfall fails and bails to the main agent, who runs the subsequent review rounds?
- **Resolution**: Preserve the existing design. On rc=4 (coder-main-agent-required) the loop hands off; the main agent applies that round's findings via Edit/Write and commits; `step-5-resume.sh` re-invokes `review-and-fix step5 --starting-round N+1`. The autonomous python loop runs the remaining rounds. The main agent never drives the review loop. This fix must route commit failures into this existing path and ensure the tree is clean before the main agent applies.
- **Source**: user (requirement 3) + codebase (already implemented)

## Decision 4: Submodule-violation stays a terminal stall
- **Question**: When a coder edits a forbidden submodule path (submodule-violation, currently terminal rc=3), should it waterfall or stall?
- **Resolution**: Keep it terminal. Clean the tree (so the rebase is not broken) but still return rc=3 submodule-violation and stall for operator review. Behavior is otherwise unchanged; only the leftover dirty tree is fixed. Submodule-targeting findings are pre-scrubbed, so this path is rare.
- **Source**: user

## Scope boundaries and hard constraints
- **In-scope**: failure-path tree cleanup + waterfall restructure in `apply_findings_with_coder` (`python/review_and_fix.py`); regression tests in `python/test_review_and_fix.py`; minor doc fix (the `coder-main-agent-required` branch text says "Codex -> Cursor"; the code waterfall is Cursor -> Codex).
- **Out-of-scope**: changing the main-agent apply + autonomous-resume mechanism (already exists); changing `no-changes` (rc=0) semantics; resolving persistent pre-commit-hook commit failures beyond leaving a clean tree (flagged as a known risk, not fixed here).
- **Hard constraints**: do not break the existing `coder-main-agent-required` -> main-agent-apply -> resume-at-N+1 flow; preserve the pre-coder snapshot machinery; respect the submodule edit guard; keep the rc/status contract consumed by the Step 5 loop and the `/implement` orchestrator coherent across all callers of `apply_findings_with_coder` (loop `_run_round`, `mav-apply`, `apply_findings`).
