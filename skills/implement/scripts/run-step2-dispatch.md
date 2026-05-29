# run-step2-dispatch.sh contract

`skills/implement/scripts/run-step2-dispatch.sh` is the `/implement` Step 2
launcher for `step2-implement.sh`. It reduces the primary SKILL.md dispatcher
call to the implement tmpdir and selected coder while deriving the rest of the
context from session artifacts.

Caller: `skills/implement/SKILL.md` Step 2.1 and Q/A redispatch in Step 2.3.

`run-step2-dispatch.sh` is a top-level Family B launcher. It still calls the
Stage 3 no-op `larch_quiet_append_done_trap` shim for compatibility with
deferred skill fences; paired-PID plumbing was removed from the shell launcher
in breadcrumbs Stage 3.

Arguments:

- `--implement-tmpdir PATH` is required.
- `--coder CODER` is required.
- `--answers PATH` is optional and is only for Step 2.3 Q/A redispatch.

Derived sources:

- `$IMPLEMENT_TMPDIR/plan.txt`: always forwarded as `--plan-file` (conventional
  path; the launcher does not read `PLAN_FILE` from `session-env.sh`).
- `--workflow HARD` is always passed (the launcher does not read
  `POST_PLAN_WORKFLOW_PATH` from `session-env.sh`).
- `$IMPLEMENT_TMPDIR/session-env.sh`
  - `CURSOR_PRESENT`: forwarded as `--cursor-present`.
  - `LARCH_CLAUDE_PLUGIN_ROOT`: resolves the downstream script path when
    `CLAUDE_PLUGIN_ROOT` is not already set.
- `$IMPLEMENT_TMPDIR/feature-description.txt`: forwarded as `--feature-file`.
- `$IMPLEMENT_TMPDIR`: forwarded as `--tmpdir`.

Exception:

- `--answers PATH` cannot be derived safely from tmpdir state because each Q/A
  redispatch writes a new `$IMPLEMENT_TMPDIR/codex-answers-$RESUME_N.json`.
  Picking "latest" would be order-sensitive and could replay stale answers, so
  the Q/A loop passes the exact answers file for redispatch only.

Harness: `skills/implement/scripts/test-run-step2-dispatch.sh`.
