# step-5-resume.sh

Step 5 main-agent handoff resume helper. Records round timing, exits immediately for `--record-only`, otherwise captures `commit-fixes --stage-all` in an errexit-safe block, gates on its handoff commit outcome, and re-enters `review-and-fix step5` when the tree is clean.

## Caller

`skills/implement/SKILL.md` invokes this wrapper from the named `/implement` step so the prompt-side Bash fence remains a plugin-root source guard plus one script call.

## KV grammar

The wrapper relays the underlying helper stdout unchanged unless this file names explicit keys. Explicit keys are newline-delimited `KEY=value` records and must be token-scannable by the orchestrator.

For `--ready-to-commit`, the wrapper understands `COMMITTED=`, `ERROR=`, `SHA=`, and `COMMIT_OUTCOME=` lines from `review-and-fix commit-fixes --stage-all`. `COMMIT_OUTCOME` values are `ok`, `noop`, or `failed`: `ok` means a commit was created, `noop` means a clean-tree `--stage-all` no-op, and `failed` means the commit phase failed closed.

The wrapper parses `COMMIT_OUTCOME` internally only from newline-delimited records whose key is exactly `COMMIT_OUTCOME` at the start of the line (`^COMMIT_OUTCOME=`). It must not read `COMMIT_OUTCOME` from free-form `ERROR=` text or from any other KV line. It exits before `review-and-fix step5` unless the parsed value is exactly `ok` or `noop`; absent or malformed values fail closed.

Successful commit KVs, including `COMMIT_OUTCOME=ok` or `COMMIT_OUTCOME=noop`, are relayed only after both the internal allowlist gate and the wrapper porcelain probe pass. Failure paths that stop before `step5` relay commit KVs, including `COMMIT_OUTCOME=failed` when the wrapper owns the failure, before exit.

## Invariants

- Bash 3.2 portable; no associative arrays or namerefs.
- Self-rehydrates `CLAUDE_PLUGIN_ROOT` from `$IMPLEMENT_TMPDIR/plugin-root.env` where needed.
- Telemetry consumers read `LARCH_TOKEN_SESSION_ID`, `LARCH_CLAUDE_SOURCE_FILE`, and `LARCH_TIMING_LEDGER` from `$IMPLEMENT_TMPDIR/session-env.sh` internally instead of relying on inline SKILL.md triplets.
- The round-timing duplicate probe uses awk success-on-match semantics: `found` must exit `0`, and missing rows must exit `1`.
- `--ready-to-commit` exits non-zero before `review-and-fix step5` when the line-anchored `COMMIT_OUTCOME` value is absent, malformed, or not `ok`/`noop`.
- `--ready-to-commit` still probes porcelain before resuming the review loop as an additional dirty-tree guard; dirty porcelain or probe failure relays `COMMIT_OUTCOME=failed` and exits before `step5`.
- Commit-phase failure exits before `review-and-fix step5`, so later `STEP5_REVIEW_STATUS=` output cannot mask an unknown commit phase.
- `skills/implement/SKILL.md` treats commit-phase failure as a terminal Step 5 stall and skips to Step 18 (the Step 18a stall-recovery gate runs before the final report). When `STEP5_REVIEW_STATUS=` is present, the orchestrator branches on that envelope instead of re-checking `COMMIT_OUTCOME` for `resume-handoff-commit-failed`.
- `COMMIT_OUTCOME=ok` or `COMMIT_OUTCOME=noop` without `STEP5_REVIEW_STATUS=` is not Step 6 continuation. In the lacks-envelope path, consumers evaluate the line-anchored `COMMIT_OUTCOME` allowlist before preflight routing.

## Edit-in-sync

Update `skills/implement/SKILL.md` and the implement structure/timing harnesses when this contract or argv changes.
