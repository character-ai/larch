### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: skills/implement/scripts/step-5-resume.sh:85-90
- **Concern**: Dropping `|| true` without errexit-safe capture leaves `set -e` aborting before `step5` on clean-tree no-op commits. Scenario: `commit-fixes --stage-all` exits non-zero when porcelain is already empty; with `set -euo pipefail` the wrapper dies before `review-and-fix step5`, so MAV/coder resume never re-enters the loop even though the plan treats clean-tree `COMMITTED=false` as success
- **Proposed resolution**: Capture commit-fixes stdout/rc explicitly (disable errexit for that call); re-emit `COMMITTED=`/`ERROR=`/`SHA=`; if porcelain is empty after the call, continue to `step5` regardless of rc; exit non-zero only when porcelain remains dirty and commit failed

### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/review_and_fix.py:453-479
- **Concern**: Pre-lint snapshot commit helper omits pre-dirty unchanged-path exclusion. Scenario: Loop-start HEAD diff includes hunks that were dirty before lint-fix; post-loop commit can land unrelated pre-existing edits on those paths
- **Proposed resolution**: Mirror pre-coder snapshot machinery: capture per-path wt/index patches at lint-loop entry and commit only paths whose diffs diverge from those snapshots (reuse _path_matches_pre_coder_snapshot logic)

### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/review_and_fix.py:2325-2327
- **Concern**: Step 7 --stage-all still uses git add -A plus bare commit. Scenario: Unrelated staged or dirty files at Step 7 can ride into the review-fix commit despite pathspec-only lint-fix goals
- **Proposed resolution**: Change commit_fixes --stage-all to stage via pathspec-from-file built from review deltas only, matching _stage_and_commit_round

### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/SKILL.md:643-647
- **Concern**: Ready-to-commit stall wiring lacks explicit stdout capture contract. Scenario: Background fence output may not be bound before Step 6; resume-handoff-commit-failed routing can be skipped silently
- **Proposed resolution**: Require orchestrator to capture step-5-resume.sh stdout and parse COMMITTED ERROR SHA STEP5_REVIEW_STATUS from that capture before continuing

### FINDING_1:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: blocking
- **Focus area**: risk-integration
- **Location**: skills/implement/scripts/step-5-resume.sh:85-90
- **Concern**: Dropping `|| true` without an rc-tolerant wrapper conflicts with `set -euo pipefail`. Scenario: `review-and-fix commit-fixes --stage-all` returns non-zero on a clean tree (`git commit` with nothing staged after `git add -A`); the script exits before parsing `COMMITTED=` / porcelain and never reaches `review-and-fix step5`, so MAV/coder resume breaks on the common no-op handoff
- **Proposed resolution**: In `step-5-resume.sh`, capture commit-fixes rc without aborting (subshell or `set +e` block), relay KV stdout, then branch: exit non-zero only when porcelain is non-empty after `COMMITTED=false`; otherwise continue to `step5`. Optionally add a matching clean-tree no-op in `commit_fixes` (exit 0, `COMMITTED=false`) and pin it in tests

### FINDING_1:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/review_and_fix.py:144-148
- **Concern**: _lint_fix_snapshot_paths porcelain union rule is underspecified versus the no-unrelated-dirty edge case. Scenario: The second union member says paths lint-fix may have touched without defining that set; a broad porcelain diff against the pre-lint snapshot can stage unrelated pre-existing dirty files or still miss in-place edits, recreating the #4712 ship dirty-tree stall or committing out-of-scope hunks
- **Proposed resolution**: Define commit candidates as paths in delta_paths union (git diff --name-only pre_lint_head) only; drop or tighten the vague porcelain-diff bullet so it cannot include files outside that union

### FINDING_1:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/review_and_fix.py:1143-1186
- **Concern**: The proposed lint-fix snapshot uses only HEAD plus porcelain, which cannot distinguish untouched pre-dirty tracked files from files edited in place by lint-fix. Scenario: A dirty baseline has a.py and b.py modified before lint-fix; lint-fix edits only a.py; git diff --name-only <pre_lint_head> still lists both paths, so the commit can include unrelated b.py changes or the helper cannot safely satisfy its own only paths changed since pre-lint snapshot contract
- **Proposed resolution**: Revise the plan to snapshot pre-lint tracked dirty content, for example reuse the existing pre-coder per-path diff snapshot pattern, then compare after lint-fix and stage only paths whose pre-lint diff changed; add the two-pre-dirty-files test so only the lint-touched path is committed

