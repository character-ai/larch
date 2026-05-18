# run-step1-plan-log.sh contract

`scripts/run-step1-plan-log.sh` is the `/implement` Step 1 launcher for the
`plan-goals-test` run-log batch. It wraps `compose-plan-goals-test.sh` and the
corresponding `larch-log.sh write` call so SKILL.md only passes the tmpdir and
the human-authored goal sentence. When `$IMPLEMENT_TMPDIR/parent-issue.md`
exists, it also refreshes the `parent-issue` run-log batch after the plan batch
write so the tracking sentinel survives session tmpdir cleanup.

Caller: `skills/implement/SKILL.md` Step 1 "Larch-log batches".

Arguments:

- `--implement-tmpdir PATH` is required.
- `--goal-text TEXT` is required. The flag may carry an empty string, but the
  caller must pass it explicitly.

Derived sources:

- `$IMPLEMENT_TMPDIR/session-env.sh`
  - `PLAN_FILE`: passed to `compose-plan-goals-test.sh --plan-file`.
  - `LARCH_CLAUDE_PLUGIN_ROOT`: resolves helper paths when
    `CLAUDE_PLUGIN_ROOT` is not already set.
- `$IMPLEMENT_TMPDIR/session-id`: passed to `larch-log.sh write --run-id`.
- `$IMPLEMENT_TMPDIR/larch-logs`: passed as `--log-root`.
- `$IMPLEMENT_TMPDIR/plan-goals-test.md`: conventional composed output path.
- `$IMPLEMENT_TMPDIR/parent-issue.md`: optional tracking-issue sentinel written
  to the `parent-issue` batch when present.

Hardcoded downstream flags:

- `larch-log.sh write --skill implement --batch plan-goals-test`
- `larch-log.sh write --skill implement --batch parent-issue` (best-effort,
  only when the sentinel exists)

Exceptions: `--goal-text` remains caller-supplied because it is the
orchestrator's one-sentence objective, not a canonical session artifact.

Harness: `scripts/test-run-step1-plan-log.sh`.
