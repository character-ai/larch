## Goal
Fix Codex sandbox to allow writes to repo-root files by adding --add-dir $PWD

## Implementation Plan

### Goal
Fix `sandbox-denied-required-root-files` bail in the Codex implementer by explicitly adding the repo root to the codex exec sandbox via `--add-dir "$PWD"`.

### Root cause
`codex exec --full-auto -C "$PWD" --add-dir "$SESSION_TMPDIR"` uses the `workspace-write` sandbox. The sandbox only grants write access to directories explicitly listed via `--add-dir`; the `-C "$PWD"` flag sets the agent's CWD but does not automatically expand the seatbelt writable-paths list to include `$PWD`. As a result, repo-root files (`Makefile`, `AGENTS.md`) and `.claude/` paths are denied.

### Files to modify

1. **`scripts/launch-codex-implement.sh`** (line ~319)
   - In the `codex exec` command, after `--add-dir "$SESSION_TMPDIR" \`, add `--add-dir "$PWD" \`
   - `$PWD` in the launcher is the repo root per the cwd contract (SKILL.md); no new variable needed

2. **`scripts/launch-codex-implement.md`** (sibling doc)
   - Bullet at line 14 (the `--add-dir "$SESSION_TMPDIR"` invariant): append a sentence noting that `--add-dir "$PWD"` is also passed to explicitly grant write access to the repo root, fixing `sandbox-denied-required-root-files`
   - Bullet at line 21 (the "Codex argv shape" invariant): update `--add-dir "$SESSION_TMPDIR"` mention to include `--add-dir "$PWD"` alongside it

3. **`skills/implement/scripts/test-codex-implementer.sh`** (test 6, lines 382-396)
   - After the existing positional checks for lines 5-6 (`--add-dir` + `$SESSION_TMPDIR`), add two new checks:
     - `[[ "$(sed -n '7p' "$ARGV_FILE")" == "--add-dir" ]]`
     - `[[ "$(sed -n '8p' "$ARGV_FILE")" == "$REPO_ROOT" ]]`
   - Update the fail message to mention the new arg pair

### Testing strategy
Run `make test-codex-implementer` — the updated test harness at test 6 mechanically pins that both `--add-dir "$SESSION_TMPDIR"` and `--add-dir "$REPO_ROOT"` appear in the expected argv positions.

### Failure modes
- The `--add-dir` flag is already accepted by codex exec (it's used in dispatch-plan-voters.sh and check-reviewers.sh); no new flag risk.
- Test assertion is positional (lines 5-8), matching the stable argv prefix order established by the existing test.
- No risk of double-granting: `--add-dir` with the same path twice is idempotent in codex's sandbox implementation.

## Test plan
(no test plan section in plan-file)
