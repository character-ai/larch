## Goal
Change coder dispatch from codex-first to cursor-first in review-and-fix.sh and lint-fix-loop.sh

## Implementation Plan

Change coder dispatch ordering from codex-first to cursor-first in `review-and-fix.sh` and `lint-fix-loop.sh`, and update their sibling `.md` contract files.

### Files to modify

1. `skills/review-and-fix/scripts/review-and-fix.sh` — `run_coder_dispatch()` lines 236-273
2. `scripts/lint-fix-loop.sh` — if/elif dispatch block lines 258-263
3. `skills/review-and-fix/scripts/review-and-fix.md` — line 27 ordering description
4. `scripts/lint-fix-loop.md` — step 5 ordering description

### Approach

**review-and-fix.sh `run_coder_dispatch()`**:
- Replace codex-first try with cursor-first: wrap cursor auth setup in an if-guard; on success, acquire cursor serial lock, dispatch cursor; on success return 0
- After the cursor block (whether cursor auth failed or cursor dispatch failed), reset `_SERIAL_LOCK=""`, acquire codex serial lock, dispatch codex; on success return 0
- Final fallback: emit error breadcrumb and return 1

**lint-fix-loop.sh dispatch block**:
- Swap `if [[ "$CODEX_PRESENT" == "true" ]]` and `elif [[ "$CURSOR_PRESENT" == "true" ]]` branches
- Cursor check and `run_cursor` become the primary branch; codex becomes the elif fallback

**Sibling .md files**:
- `review-and-fix.md` line 27: "dispatching Codex, then Cursor" → "dispatching Cursor, then Codex"
- `lint-fix-loop.md` step 5: swap "Dispatch Codex first" to "Dispatch Cursor first … Codex … fallback"

### Edge cases

- When cursor auth setup fails (`cursor_launcher_load_model_args` or `cursor_launcher_setup_auth_argv` returns non-zero), the cursor block is skipped silently and codex is tried — no error breadcrumb until both fail. This matches the existing `ship-pr.sh` cursor-first pattern.
- `test-review-and-fix.sh` `codex-success` case: cursor auth succeeds (CURSOR_API_KEY is set), cursor stub returns 1 (default case for `codex-success:cursor`), codex succeeds → `CODER_TOOL=codex` unchanged.
- `test-lint-fix-loop.sh` cases all use `CURSOR_PRESENT=false` → cursor branch is skipped, codex branch runs as before.


## Test plan

Run `/relevant-checks` which includes:
- `test-review-structure.sh` — checks both `--tool codex` and `--tool cursor` are present in review-and-fix.sh
- `test-review-and-fix.sh` — the full dispatch harness including codex-success, cursor-success, all-fail
- `test-lint-fix-loop.sh` — verifies the dispatch ordering
