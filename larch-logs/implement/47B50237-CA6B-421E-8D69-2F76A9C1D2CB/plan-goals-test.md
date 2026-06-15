## Goal
Implement issue #4341: [IMPLEMENTING] [BUG] Codex plan-review slots fail with "Not inside a trusted directory" because run_legacy_script overrides CWD to plugin root.

## Implementation Plan
## Plan

## Context

- `approach-synthesis.txt` is `NO_SKETCHES`, so this plan uses direct repo inspection only.
- `design-outline.md` is non-empty and `.outline-approved` exists, so its Goals, Non-goals, and Surfaces are binding.
- No `discussion-round1.md` or `brainstorm.md` exists in the active design tmpdir.
- Accepted finding FINDING_1: resolving workdir from `Path.cwd()` alone is insufficient when `run_legacy_script` forces CWD to the managed plugin-cache directory (not a git root). Resolution must mirror `scripts/run-relevant-checks-captured.sh` / `scripts/block-submodule-edit.sh` and recover the consumer repo from session keepalive metadata when CWD is wrong.
- Accepted finding FINDING_2: the keepalive workdir test must unset `CLAUDE_PROJECT_DIR` before launch so tier 3 (`CLONE_PATH` recovery) is actually exercised; inherited `CLAUDE_PROJECT_DIR` would let tier 1 pass without testing keepalive parsing.
- Accepted finding FINDING_2 (reviewer): `_run_external_agent_with_auth_retries` must evaluate the unclassified empty exit-1 predicate **before** any auth-budget exhaustion return, and the one-shot retry must not be gated by the auth attempt budget.
- Accepted finding FINDING_3: `_review_run_with_retries` must track an explicit `unclassified_empty_retried` one-shot guard so the unclassified branch cannot repeat until `max_auth` is exhausted.
- Accepted finding FINDING_1 (loop shape): bounded-loop `continue` cannot grant a bonus launch when `LARCH_EXTERNAL_AUTH_RETRIES=1`. Both retry helpers must use a loop shape that permits exactly one extra runner call outside the auth budget.

## Approach

- Keep the fix in `python/agents.py`.
- Replace naive `workdir = str(Path.cwd())` with a tiered resolver that returns a git-validated consumer repo toplevel when possible.
- Pass the resolved path to both `codex exec -C` and `_trust_config_arg`.
- Leave `run_legacy_script(..., cwd=str(_REPO_ROOT))` unchanged.
- Leave Cursor `--workspace str(Path.cwd())` unchanged.
- Add one blind retry for `external_auth_verdict(...) == "unclassified"` with exit code `1` and empty sidecars.
- Apply that retry to both review and generic external-agent retry paths, because `_review_launch_codex` uses `_review_run_with_retries`.
- **Replace auth-bounded `for` / `while auth_attempt <= max_auth` loops** in both retry helpers with `while True` loops that separate:
  - **auth-budget iterations** (`auth_attempt` / `max_auth`), and
  - **one bonus unclassified-empty launch** (`unclassified_empty_retried`), which may `continue` without consuming or being blocked by the auth budget.

### Workdir resolution order

1. **`CLAUDE_PROJECT_DIR`** — when set and non-empty, run `git -C <dir> rev-parse --show-toplevel` (same validation pattern as `scripts/block-submodule-edit.sh`). Use the toplevel on success.
2. **`git -C <cwd> rev-parse --show-toplevel`** — use the first non-empty stdout line on success.
3. **Session keepalive `CLONE_PATH`** — only when step 2 fails or cwd is not inside a git worktree:
   - If `DESIGN_TMPDIR` or `SESSION_TMPDIR` is set, read `<tmpdir>/.larch-keepalive` and parse `CLONE_PATH=` (same key grammar as `python/progress_report.py` `_kv_value` / `session_env.py` `_write_session_identity`).
   - Otherwise walk parents from `cwd` upward looking for `.larch-keepalive`, parse `CLONE_PATH`, stop at filesystem root.
   - For any non-empty `CLONE_PATH`, run `git -C <clone_path> rev-parse --show-toplevel` and use the toplevel on success.
4. **Fallback** — return the original `cwd` unchanged.

All `git` calls go through the existing `proc.run` seam with a short timeout. Any failure, timeout, missing git, or empty stdout at a tier continues to the next tier.

### Unclassified empty exit-1 retry contract (shared)

- Predicate helper `_is_unclassified_empty_startup_failure(exit_code: int, verdict: str) -> bool` returns true only for `exit_code == 1` and `verdict == "unclassified"`.
- Both retry helpers initialize `unclassified_empty_retried = False`.
- Exactly **one** extra launch attempt is allowed for this predicate, **outside** the auth retry budget.
- The bonus attempt may increment telemetry counters but must not be blocked by `auth_attempt >= max_auth` or `attempt >= _auth_retry_limit()`.

### Loop shape (ordering-critical)

Both helpers use `while True` instead of a fixed-range `for` or `while auth_attempt <= max_auth`.

**Per-iteration order (both helpers):**

1. Run the external agent (`run_external_agent` or `_review_run_wrapper_attempt`).
2. If `exit_code == 0`, return immediately.
3. Compute `verdict = external_auth_verdict(...)` once.
4. **Unclassified one-shot (bonus slot):** when `not unclassified_empty_retried` and `_is_unclassified_empty_startup_failure(exit_code, verdict)` and the failure is not an explicit auth/quota failure (review helper only), set `unclassified_empty_retried = True`, reset retry artifacts where applicable, optionally bump telemetry (`auth_attempt` in review helper), and `continue`. This branch does **not** check auth-budget exhaustion.
5. **Auth-budget gate:** if explicit auth failure and auth budget remains (`auth_attempt < max_auth` in review helper; equivalent check in generic helper), increment the auth counter and `continue`.
6. **Terminal return:** return the current failed result.

With `LARCH_EXTERNAL_AUTH_RETRIES=1`, step 4 still runs a second launch; step 5 allows zero explicit-auth retries because `auth_attempt` is already at the budget after the first auth-classified failure.

## Files to modify/create

### UPDATED: `python/agents.py`

- Add `_git_toplevel(path: str) -> str | None` near `_trust_config_arg`:

  - Run `git -C <path> rev-parse --show-toplevel` through `proc.run`.
  - Use a short timeout.
  - Return the first non-empty stdout line on success; otherwise `None`.

- Add `_read_keepalive_clone_path(keepalive: Path) -> str | None`:

  - Read the file when present.
  - Parse `CLONE_PATH=<value>` from `KEY=value` lines (ignore `#` comment lines).
  - Return the first non-empty value; otherwise `None`.
  - Keep parsing local to `agents.py` (do not import `progress_report`).

- Add `_clone_path_from_session_tmpdir() -> str | None`:

  - For each of `DESIGN_TMPDIR`, `SESSION_TMPDIR` (in that order), when the env var is set read `<tmpdir>/.larch-keepalive` via `_read_keepalive_clone_path`.
  - Return the first non-empty `CLONE_PATH`.

- Add `_clone_path_from_parent_walk(start: Path) -> str | None`:

  - Walk `start`, `start.parent`, … up to filesystem root.
  - At each directory, if `.larch-keepalive` exists, call `_read_keepalive_clone_path`.
  - Return the first non-empty `CLONE_PATH`.

- Add `_resolve_review_codex_workdir(cwd: str) -> str`:

  - Bind `start = Path(cwd)`.
  - **Tier 1:** if `os.environ.get("CLAUDE_PROJECT_DIR")` is non-empty, `_git_toplevel(project_dir)`; return on success.
  - **Tier 2:** `_git_toplevel(str(start))`; return on success.
  - **Tier 3:** `clone = _clone_path_from_session_tmpdir() or _clone_path_from_parent_walk(start)`; when `clone` is set, `_git_toplevel(clone)`; return on success.
  - **Tier 4:** return the original `cwd`.

- Add `_is_unclassified_empty_startup_failure(exit_code: int, verdict: str) -> bool`:

  - Return true only for `exit_code == 1` and `verdict == "unclassified"`.

- In `_review_launch_codex`:

  - Replace `workdir = str(Path.cwd())` with `workdir = _resolve_review_codex_workdir(str(Path.cwd()))`.
  - Keep the same `workdir` for `-C` and `_trust_config_arg(workdir)`.

- In `_run_external_agent_with_auth_retries`:

  - Replace the bounded `for attempt in range(...)` loop with a `while True` loop plus `unclassified_empty_retried = False` guard.
  - Evaluate `verdict = external_auth_verdict(...)` once per iteration.
  - Unclassified bonus branch (before auth-budget check): when predicate fires and flag is False, set flag, `continue`.
  - Auth-budget branch: when `verdict == "auth"` and budget remains, increment counter, `continue`.
  - Terminal return otherwise.

- In `_review_run_with_retries`:

  - Replace `while auth_attempt <= max_auth` with `while True`; add `unclassified_empty_retried = False`.
  - Store `verdict = external_auth_verdict(tool, *auth_sidecars)` once per iteration.
  - Unclassified bonus branch (after transient handling, before auth retry): when predicate fires, flag is False, and not auth/quota: set flag, bump `auth_attempt` for telemetry, call `_review_reset_retry_artifacts`, `continue`.
  - Keep existing auth retry branch.
  - Terminal return replaces fallthrough.

### UPDATED: `python/test_launch_review.py`

- `test_codex_launch_resolves_workdir_to_git_root`: monkeypatch `chdir` to a subdirectory inside a temp git repo; assert `-C` equals the git toplevel.
- `test_codex_launch_resolves_workdir_from_plugin_cache_via_keepalive`: chdir to non-git plugin-cache dir, set `DESIGN_TMPDIR` with `.larch-keepalive`, **unset `CLAUDE_PROJECT_DIR`**; assert `-C` equals consumer git toplevel.
- `test_codex_launch_resolves_workdir_from_claude_project_dir`: chdir to non-git dir, set `CLAUDE_PROJECT_DIR` to consumer git repo; assert `-C` equals consumer toplevel.
- `test_codex_retry_unclassified_empty_exit_one`: empty sidecar + exit-1 triggers exactly one retry in `_review_run_with_retries`; `auth_attempt == 2`.
- `test_codex_retry_unclassified_empty_exit_one_respects_auth_retry_limit_one`: `LARCH_EXTERNAL_AUTH_RETRIES=1`, exit-1 empty sidecars; two total wrapper calls, bonus retry fires outside auth budget.

### UPDATED: `python/test_agents.py`

- `test_unclassified_empty_exit_one`: `_run_external_agent_with_auth_retries` with exit-1 empty sidecars calls runner twice, returns second result.
- `test_unclassified_empty_exit_one_respects_auth_retry_limit_one`: `_auth_retry_limit=1`, exit-1 empty sidecars; runner called twice (bonus retry outside auth budget).

## Edge cases

- `git` unavailable at every tier: falls back to original cwd.
- cwd already equals consumer repo root: tier 2 returns it unchanged.
- cwd outside any git worktree, no keepalive, no `CLAUDE_PROJECT_DIR`: fallback to original cwd.
- Plugin cache is the active git worktree (local plugin dev): tier 2 returns plugin repo root (correct).
- Valid `DESIGN_TMPDIR/.larch-keepalive` in managed cache: tier 3 recovers consumer repo.
- First empty exit-1 is deterministic: only one extra attempt in either retry helper.
- Pytest inherits `CLAUDE_PROJECT_DIR`: keepalive test clears it so tier 3 is the path under test.
- `LARCH_EXTERNAL_AUTH_RETRIES=1`: bonus retry still fires; bounded `for/range` loop would not allow this.

## Failure modes

- Stale or missing `.larch-keepalive`: tier 3 ineffective; tier 4 preserves current failure mode.
- Wrong `CLONE_PATH` in keepalive: `git -C` validation catches it; falls through to cwd fallback.
- Retrying every unclassified failure hides deterministic config errors: limit to one attempt.
- Keepalive test leaving `CLAUDE_PROJECT_DIR` set: can mask a broken tier 3 via tier 1 pass.
- Unclassified check after `auth_attempt >= max_auth` guard: bonus launch blocked when auth retries = 1.

## Testing strategy

- `python3 -m pytest python/test_launch_review.py -k 'codex_launch_resolves_workdir or codex_retry_unclassified_empty_exit_one'`
- `python3 -m pytest python/test_agents.py -k 'unclassified_empty_exit_one'`
- `python3 -m pytest python/test_launch_review.py python/test_agents.py`
- `bash scripts/relevant-checks.sh`

## Acceptance

- `_review_launch_codex` no longer uses `Path.cwd()` directly; it calls `_resolve_review_codex_workdir`.
- `_resolve_review_codex_workdir` returns a git-validated toplevel when `CLAUDE_PROJECT_DIR` is set, when cwd is inside a git worktree, or when `.larch-keepalive` provides a valid `CLONE_PATH`; falls back to cwd.
- Both `_run_external_agent_with_auth_retries` and `_review_run_with_retries` perform exactly one bonus launch on `unclassified` + exit-1 regardless of `LARCH_EXTERNAL_AUTH_RETRIES`.
- All new tests pass.

diff_lines: 242

## Test plan
(no test plan section in plan-file)
