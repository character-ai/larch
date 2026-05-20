## Goal
Add auto-resolve CHANGELOG conflicts and reduce vendor timeout in run_rebase_rebump

## Implementation Plan

Goal: Prevent run_rebase_rebump in ship-pr.sh from launching a 30-minute vendor agent for
CHANGELOG-only conflicts by (1) adding a deterministic pre-pass auto-resolver, (2) passing
remaining conflict file context to the vendor prompt, and (3) lowering the resolve-conflict
timeout to 600s.

### Files to create/modify

**NEW scripts/auto-resolve-changelog.sh** (~35 lines)
- Takes one arg: conflicted CHANGELOG file (e.g., CHANGELOG.md)
- During a git rebase: stage 2 (`:2:`) = upstream/main, stage 3 (`:3:`) = feature branch
- Reads both sides from git object store; no external tool needed
- If both sides have the same first heading (e.g., `## Unreleased`): concat unique entry
  lines from both sides under that heading, then append the tail of the upstream version
  (everything from the second heading onward)
- If heading is absent or sides don't share the same first heading: exit 1 (let vendor handle)
- Writes result to the working-tree file
- Bash 3.2 compatible, set -euo pipefail

**NEW scripts/auto-resolve-changelog.md** (sibling doc per script-md-siblings rule)

**NEW scripts/test-auto-resolve-changelog.sh** (regression harness)
- Tests: two distinct entries → merged; same entry in both → deduped; no heading → exit 1;
  multi-section CHANGELOG → only first section merged, tail preserved

**NEW scripts/test-auto-resolve-changelog.md** (harness stub)

**MODIFY scripts/ship-pr.sh — run_rebase_rebump, around line 1302**
After rebase_rc=1 (conflict) and record_failure, before launching vendor:
1. Parse CONFLICT_FILES from rebase_out (rebase-push.sh already emits this as comma-list)
2. Auto-resolve pre-pass: split on commas, for each file:
   - CHANGELOG.md / CHANGELOG.rst / CHANGELOG → call auto-resolve-changelog.sh + git add
   - .claude-plugin/plugin.json / version.go / go.sum → git checkout --ours + git add
   - anything else → mark needs_vendor=true, add to remaining_conflicts
3. If needs_vendor=false (all resolved): GIT_EDITOR=true git rebase --continue, skip vendor
4. If needs_vendor=true: pass --conflict-files "$remaining_conflicts" to vendor launchers
   and use --timeout 600 (down from 1800)
5. Even when ALL files went to vendor (no auto-resolve), use --timeout 600

**MODIFY scripts/launch-cursor-ci.sh**
- Add CONFLICT_FILES="" variable and --conflict-files flag parsing
- When ROLE=resolve-conflict and CONFLICT_FILES non-empty: append conflict context block to
  prompt (list of files, instruction to stage each resolved file + run git rebase --continue)
- Update sibling .md

**MODIFY scripts/launch-codex-ci.sh** — same changes for parity
- Update sibling .md

**MODIFY scripts/test-ship-pr.sh** — add regression tests:
- Pure CHANGELOG conflict → auto-resolved, zero vendor launcher calls
- Mixed CHANGELOG + non-trivial file → vendor called with --conflict-files for non-trivial
  file only AND --timeout 600
- Non-trivial-only conflict → vendor called with --conflict-files AND --timeout 600

**MODIFY scripts/test-launch-cursor-ci.sh** — add --conflict-files accept/usage test


## Test plan
- make lint (includes bash32 check, lint-bash32)
- Run test-auto-resolve-changelog.sh
- Run test-ship-pr.sh
