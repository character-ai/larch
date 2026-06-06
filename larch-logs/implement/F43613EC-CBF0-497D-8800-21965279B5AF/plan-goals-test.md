## Goal
Implement issue #3591: [IMPLEMENTING] [BUG] (URGENT) review-and-fix round commits drop coder-created new files\n\n**Surface**: `skills/review-and-fix/scripts/review-and-fix.sh`.

## Implementation Plan
**Surface**: `skills/review-and-fix/scripts/review-and-fix.sh`

The per-round review-fix commit stages from a coder-delta manifest that is **tracked-files-only**, so files the coder **creates** are silently excluded from the round commit while their (tracked) callers are committed:

- `round_coder_delta_paths()` builds `coder-stage-paths.txt` from `git diff --name-only "$pre_head"` — untracked new files never appear in `git diff` output.
- The fallback `capture_round_tracked_paths()` is `git diff --name-only` + `git diff --name-only --cached` — also tracked-only.
- The commit runs `git-commit.sh --only --pathspec-from-file "$stage_manifest"`, and the refuse-guard `round_tracked_dirty_outside_manifest()` checks **tracked** dirty paths only, so untracked leftovers trip nothing.

**Consequence**: broken-by-construction commits — committed code sources/executes files git does not have. Local checks mask the breakage (the files exist untracked in the worktree), so the defect surfaces only in CI or after a fresh clone, and compounds across rounds.

**Incident evidence** (run `3876DC27-D694-4C99-B942-61A52A2554D7`, PR #3585, issue #3547): round-2 commit `5adcd11` migrated callers (`skills/shared/scripts/render-assessor-prompt.sh`, `scripts/launch-claude-subprocess.sh`, `skills/shared/scripts/render-voter-prompt.sh`, `skills/review/scripts/aggregate-findings.sh`) to source new `scripts/lib-untrusted-block.sh` / `scripts/lib-scope-anchor-handoff.sh`; the libs stayed untracked through rounds 2-4. Round 4 repeated the identical shape with `skills/design/scripts/persist-retally-step3-env.sh` (Makefile target and SKILL.md references committed; helper + harness untracked). Manual stall recovery had to commit them by hand. Note `scripts/lint-fix-loop.sh` already gets this right (`capture_untracked_paths()` participates in its delta) — review-and-fix should match.

**Suggested fix**: include the untracked delta versus the pre-coder snapshot in `collect_round_stage_paths()` (e.g. `git status --porcelain` `??` rows filtered against a pre-coder untracked snapshot), subject to the same submodule/forbidden-path filters as tracked paths; add an untracked-outside-delta refuse-guard sibling to `round_tracked_dirty_outside_manifest()`; harness case in `skills/review-and-fix/scripts/test-review-and-fix.sh`: coder creates a new file and modifies a caller — assert both land in the round commit.

## Test plan
(no test plan section in plan-file)
