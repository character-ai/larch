## Goal
Skip gh release edit when release is already promoted (isPrerelease=false AND isLatest=true)

## Implementation Plan

Goal: Make `promote-latest-release.sh` a no-op when the release is already properly tagged (isPrerelease=false AND isLatest=true).

### Files to modify

1. `.claude/skills/release/scripts/promote-latest-release.sh`
   - After the dry-run early-exit block (line 82), insert a check:
     ```bash
     if [[ "$was_prerelease" == "false" && "$was_latest" == "true" ]]; then
       echo 'RELEASE_ALREADY_LATEST=true'
       exit 0
     fi
     echo 'RELEASE_ALREADY_LATEST=false'
     ```
   - This places the guard between the dry-run exit and the `gh release edit` call so:
     - Dry-run output is unchanged (exits at line 82 before reaching this block)
     - Live run when already promoted prints `RELEASE_ALREADY_LATEST=true` and exits 0
     - Live run when promotion needed prints `RELEASE_ALREADY_LATEST=false` and continues

2. `.claude/skills/release/scripts/promote-latest-release.md`
   - Add `RELEASE_ALREADY_LATEST` to the output key list
   - Document the skip-if-already-promoted behavior in the Behavior section

3. `.claude/skills/release/SKILL.md`
   - Update Step 1 instruction: mention that when `RELEASE_ALREADY_LATEST=true` is printed, the script exits without editing (no `RELEASE_IS_PRERELEASE`/`RELEASE_IS_LATEST` lines emitted)

### Edge cases / invariants
- Dry-run path is unaffected (the guard runs after the dry-run exit)
- The `gh release edit` + verification block only runs when `was_prerelease=true OR was_latest=false`
- `RELEASE_ALREADY_LATEST` is NOT printed on the dry-run path (backward compat)

### Testing strategy
- Run `/relevant-checks` after edits (pre-commit + agent-lint)
- Verify the script syntax with `bash -n`

## Test plan
(no test plan section in plan-file)
