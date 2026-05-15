## Goal
Complete larch_quiet_init migration to fix swallowed diagnostics in 98 scripts

## Implementation Plan

### Goal
Complete the larch_quiet_init migration: migrate all raw >&2 diagnostics to larch_err/larch_errf in post-init script sections, add a lint rule to enforce the contract, fix related bugs, and update tests.

### Files to modify

**A. Migration of >&2 → larch_err/larch_errf (98 script files)**
Use a Python transformation script to handle all 560 violations mechanically:
- `echo "MSG" >&2` → `larch_err "MSG"`
- `printf 'fmt\n' arg >&2` → `larch_errf 'fmt\n' arg`  
- Multi-line echo blocks: each line → separate `larch_err` call
- `cat >&2 <<'EOF' ... EOF` heredocs → `while IFS= read -r line; do larch_err "$line"; done <<'EOF' ... EOF`
- Special case `collect-agent-results.sh:273`: `cat "$WAIT_STDERR" >&2` → `while IFS= read -r line || [[ -n "$line" ]]; do larch_err "$line"; done < "$WAIT_STDERR"`
- Do NOT rewrite lines before `larch_quiet_init` (pre-init guards that run before lib is sourced)

**B. Fix `-f` → `-s` in `scripts/collect-agent-results.sh:341`**
Change `if [[ -f "$diag_file" ]]; then` to `if [[ -s "$diag_file" ]]; then`
Add test case to cover empty-diag fallback path.

**C. Fix test-launch-claude-subprocess.sh split assertion**
Change the union grep (lines 46-47) to separate assertions:
- Positive: `grep -Fq 'invalid --prompt-file' "$TMP/err"` must pass
- Negative: `grep -Fq 'invalid --prompt-file' "$TMP/quiet.log"` must fail

**D. New lint rule: scripts/lint-no-raw-stderr-after-quiet-init.py**
Python script implementing S041/no-raw-stderr-after-quiet-init:
- Scope: .sh files under scripts/, skills/*/scripts/, hooks/
- Trigger: file contains unquoted top-level `larch_quiet_init` call (not a function definition)
- Violation: subsequent line with `>&2` and `echo`/`printf`/`cat` without `larch_err`/`larch_errf`
- Wire into .pre-commit-config.yaml as new local hook
- Add test fixtures: known-bad file and known-good file

**E. Update scripts/lib-quiet.md**
Add authoring rule section: after larch_quiet_init, all user-visible diagnostics MUST use larch_err/larch_errf. Note that S041 enforces this.

**F. Register test/md files in agent-lint.toml excludes**
Add entries for the new test and md files.

### Testing strategy
1. Run static check script (TOTAL: 0 required)
2. `bash scripts/test-launch-claude-subprocess.sh` (split assertion passes)
3. `bash scripts/test-collect-agent-bash32.sh` (empty-diag fallback)
4. Pre-commit with new S041 rule fires on bad fixture, passes on good fixture
5. `/relevant-checks` passes

## Test plan
(no test plan section in plan-file)
