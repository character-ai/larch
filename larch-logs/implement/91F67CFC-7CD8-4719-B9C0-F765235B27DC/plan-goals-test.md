## Goal
Implement issue #6796: [IMPLEMENTING] [BUG] step0-abort-cleanup: false 'unhealthy' banner + leaves PID session-env residuals.

## Implementation Plan
## Plan

## Approach

Implement the approved narrow fix with two reviewer-driven corrections: use a single `Path.home()/.cache/larch/sessions` path helper for all three PID residuals (write and reap must match), and document/thread abort reason attribution at every `step0-abort-cleanup` call site.

- Keep `cleanup_tmpdir_main` dir-only.
- Add optional `--reason` and `--tool` wrapper flags with backward-compatible degraded-tools defaults.
- Print the supplied abort reason in `step0_abort_cleanup_main`.
- Log the supplied tool in the existing `Warnings` entry.
- Add `session_env.reap_pid_residuals(claude_pid: str) -> None` that unlinks exactly three PID-keyed cache files via the same `Path.home()`-based helpers used at write time.
- Do **not** use `cleanup_cache_sessions_root()` for the parsed-env reap target; that root honors `XDG_CACHE_HOME` while `_parsed_cache_path` / the write path hardcode `Path.home()/.cache/larch/sessions`.
- Call the reaper after successful tmpdir cleanup in Step 0 abort and Step 6 cleanup only.
- Do not change Step 6 eligibility or preservation gates.
- Update `skills/design/SKILL.md` so non-degraded abort/postpone fences pass explicit `--reason` / `--tool`, and the degraded-tools **Abort** branch documents (or explicitly passes) the degraded-tools strings.

## Files to modify/create

### UPDATED: python/larch/state/session_env.py

Add `_step0_parsed_env_path(pid: str) -> Path` beside `_design_symlink_path` and `_design_run_path`:

```python
Path.home() / ".cache" / "larch" / "sessions" / f"step0-parsed-{pid}.env"
```

Add `reap_pid_residuals(claude_pid: str) -> None`:

- Validate `claude_pid` with `_validate_claude_pid`.
- Build reap targets only from:
  - `_design_symlink_path(claude_pid)`
  - `_design_run_path(claude_pid)`
  - `_step0_parsed_env_path(claude_pid)`
- Unlink each exact path; suppress `FileNotFoundError`.
- Do not resolve symlinks; `Path.unlink()` removes the symlink node itself.
- Let unexpected `OSError` surface.
- Do not call `cleanup_cache_sessions_root()` anywhere in this function.

### UPDATED: python/larch/design/design_step0_env.py

Add `reason` and `tool` fields to `Step0WrapperNs`.

Add `--reason` and `--tool` to `_parse_wrapper_args` value flags.

Default values preserve current degraded-tools behavior:

- `reason`: `external tool unhealthy; re-run once it recovers.`
- `tool`: `degraded-tools-gate`

Change `_parsed_cache_path(claude_pid)` to delegate to `session_env._step0_parsed_env_path(claude_pid)` so write and reap share one canonical helper.

### UPDATED: python/larch/design/design_step0.py

Update `step0_abort_cleanup_main` to use `ns.reason` and `ns.tool`.

Print banner:

`**⚠ /design: aborted by operator: <reason>**`

Use parsed `tool` in `_append_failure`.

Run tmpdir cleanup first. If cleanup returns non-zero, return that code and do **not** reap PID residuals. If cleanup returns zero, call `session_env.reap_pid_residuals(ns.claude_pid)` and return zero.

### UPDATED: python/larch/design/design_step6.py

In `step6_cleanup_core`, after `session_env.cleanup_tmpdir_main(["--dir", str(design_tmpdir)])` returns zero, call `session_env.reap_pid_residuals(parsed.claude_pid)`.

Do not reap when cleanup is preserved, in-flight, invalid, or when tmpdir cleanup returns non-zero.

### UPDATED: skills/design/SKILL.md

In the Step 0a degraded-tools **Abort** branch (~line 119), keep the existing launcher invocation but document that defaults match today's degraded-tools banner/log. Optionally pass explicit flags for clarity:

```bash
"$HOME/.cache/larch/sessions/design-run-$PPID.sh" step0-abort-cleanup \
  --reason 'external tool unhealthy; re-run once it recovers.' \
  --tool degraded-tools-gate

Add a short note near that fence: any non-degraded abort or operator-postpone path that reuses `step0-abort-cleanup` **must** pass caller-specific `--reason` and `--tool` (launcher forwards wrapper args). Example for operator postpone:

  --reason 'operator postpone; resume later' \
  --tool operator-postpone

Without explicit flags, the verb falls back to degraded-tools messaging even when tools are healthy.

### UPDATED: python/tests/design/test_design_lifecycle.py

Extend `test_step0_abort_cleanup_appends_failure_and_cleans` to assert:

- default degraded banner remains compatible
- default tool remains `degraded-tools-gate`
- all three PID residuals under `Path.home()/.cache/larch/sessions/` are removed after cleanup succeeds

Add parameterization for `step0_abort_cleanup_main`:

- pass `--reason "operator postpone; resume later"` and `--tool operator-postpone`
- assert banner uses supplied reason
- assert failure append uses supplied tool
- assert output does not mention external tool unhealthy

Add a test that write and reap share the same parsed-env path (e.g. `_parsed_cache_path("123") == session_env._step0_parsed_env_path("123")`).

Optionally add an `XDG_CACHE_HOME` mismatch regression: create `step0-parsed-{pid}.env` under `Path.home()/.cache/larch/sessions`, set `XDG_CACHE_HOME` to a different directory, run reaper, and assert the home-cache file is removed (not left behind because reap used the XDG root).

Extend Step 6 cleanup deletion-path coverage to assert:

- Step 6 reaps all three PID residuals after successful tmpdir cleanup
- Step 6 does not reap when cleanup is preserved
- Step 6 does not reap when tmpdir cleanup returns non-zero

## Edge cases

- Missing residual files should not fail cleanup.
- A dangling `current-design-env-$PPID.sh` symlink should be removed by unlinking the symlink, not by resolving it.
- Invalid or empty `--claude-pid` should fail loudly via `_validate_claude_pid` rather than risk broad deletion.
- Step 6 must not remove residuals when it preserved the design tmpdir for recovery.
- With `XDG_CACHE_HOME` set, reap must still target `Path.home()/.cache/larch/sessions/step0-parsed-{pid}.env` to match the write path until a broader cache-root unification is intentionally scoped.

## Failure modes

- If tmpdir cleanup fails and residuals are reaped anyway, recovery gets harder. Gate reaping on cleanup rc `0`.
- If the reaper uses `cleanup_cache_sessions_root()` for parsed-env while writes use `Path.home()/.cache/...`, one PID residual survives under alternate XDG layouts. Use `_step0_parsed_env_path` everywhere.
- If new flags lack defaults, the documented degraded-tools **Abort** caller regresses. Keep parser defaults; document explicit non-degraded `--reason`/`--tool` in `SKILL.md`.
- If operators reuse `step0-abort-cleanup` without flags for postpone, messaging stays misleading. Document and exemplify caller-specific flags in `SKILL.md`.

## Testing strategy

Run focused tests:

python3 -m pytest python/tests/design/test_design_lifecycle.py -k 'step0_abort_cleanup or step6_cleanup'

Run changed-file lint/type checks:

python3 -m ruff check python/larch/design/design_step0_env.py python/larch/design/design_step0.py python/larch/state/session_env.py python/larch/design/design_step6.py python/tests/design/test_design_lifecycle.py

If available:

python3 python/cli.py checks run-relevant

## Acceptance

Run focused tests:

python3 -m pytest python/tests/design/test_design_lifecycle.py -k 'step0_abort_cleanup or step6_cleanup'

Run changed-file lint/type checks:

python3 -m ruff check python/larch/design/design_step0_env.py python/larch/design/design_step0.py python/larch/state/session_env.py python/larch/design/design_step6.py python/tests/design/test_design_lifecycle.py

If available:

python3 python/cli.py checks run-relevant

review_status: complete
rounds_completed: 2
difficulty: MODERATE
diff_lines: 145

## Test plan
(no test plan section in plan-file)
