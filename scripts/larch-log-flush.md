# larch-log-flush.sh contract

`scripts/larch-log-flush.sh` is the best-effort tail-call helper used by commit
primitives after they create a business commit. It flushes the active
`/implement` run's staged larch-log directory into a follow-up log commit when
the run context is available.

## Invariants

- Exits 0 in every case.
- No-ops when `IMPLEMENT_TMPDIR` is unset, `IMPLEMENT_TMPDIR/session-id` is
  missing or empty, `LARCH_NO_LOGS_COMMIT=true`, or
  `$IMPLEMENT_TMPDIR/post-merge-sentinel` exists.
- Reads the run id from `$IMPLEMENT_TMPDIR/session-id`.
- Invokes `scripts/larch-log.sh commit --log-root "$IMPLEMENT_TMPDIR/larch-logs"
  --skill implement --run-id "$run_id"` and swallows failures so the preceding
  business commit remains successful.

## Primary Callers

- `scripts/git-commit.sh`
- `scripts/git-amend-add.sh`
- `.claude/skills/bump-version/scripts/apply-bump.sh`
- `skills/implement/scripts/step2-implement.sh`

## Edit In Sync

Keep this file synchronized with `scripts/larch-log.md`, `scripts/ship-pr.md`,
and `skills/implement/SKILL.md` when log-flush ownership changes.
