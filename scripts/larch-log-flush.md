# larch-log-flush.sh contract

`scripts/larch-log-flush.sh` is the best-effort helper used at explicit
`/implement` lifecycle flush points. It flushes the active run's staged
larch-log directory into a follow-up log commit when the run context is
available.

## Invariants

- Exits 0 in every case.
- No-ops when `IMPLEMENT_TMPDIR` is unset, `IMPLEMENT_TMPDIR/session-id` is
  missing or empty, `LARCH_NO_LOGS_COMMIT=true`, or
  `$IMPLEMENT_TMPDIR/post-merge-sentinel` exists.
- Reads the run id from `$IMPLEMENT_TMPDIR/session-id`.
- When `$IMPLEMENT_TMPDIR/execution-issues.md` is non-empty and Step 7a has
  already been reached (checkpoint file, sentinel, or existing batch present),
  it first runs `skills/implement/scripts/flush-execution-issues.sh` in
  commit-tail mode so post-7a entries are committed before the log flush.
- Invokes `scripts/larch-log.sh commit --log-root "$IMPLEMENT_TMPDIR/larch-logs"
  --skill implement --run-id "$run_id"` and swallows failures so the preceding
  business commit remains successful.

## Call sites (invoke `larch-log-flush.sh` only here)

Business commits must **not** tail-call this helper (for example `scripts/git-commit.sh` and
`scripts/git-amend-add.sh` intentionally omit it so every code commit does not spawn a
`chore(larch-logs): flush` follow-up). Authorized flush paths instead are:

- **External implementer** — `skills/implement/scripts/step2-implement.sh` (post-dispatcher
  commit).
- **Step 7a pre-bump** — the implement orchestrator runs `scripts/larch-log.sh commit` directly
  at the pre-bump checkpoint (not via this wrapper).
- **Pre-push refresh** — `scripts/refresh-run-logs.sh` before each push.

## Edit In Sync

Keep this file synchronized with `scripts/larch-log.md`, `scripts/ship-pr.md`,
and `skills/implement/SKILL.md` when log-flush ownership changes.
