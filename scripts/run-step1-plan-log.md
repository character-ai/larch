# run-step1-plan-log.sh contract

`scripts/run-step1-plan-log.sh` is the `/implement` Step 1 launcher for the
`plan-goals-test` run-log batch. It wraps `compose-plan-goals-test.sh` and the
corresponding `larch-log.sh write` call so SKILL.md only passes the tmpdir and
the human-authored goal sentence.

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

Hardcoded downstream flags:

- `larch-log.sh write --skill implement --batch plan-goals-test`

Exceptions: `--goal-text` remains caller-supplied because it is the
orchestrator's one-sentence objective, not a canonical session artifact.

Harness: `scripts/test-run-step1-plan-log.sh`.
