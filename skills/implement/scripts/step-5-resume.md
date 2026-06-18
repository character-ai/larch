# step-5-resume.sh

Step 5 main-agent handoff resume helper. Records round timing, exits immediately for `--record-only`, otherwise captures `commit-fixes --stage-all` in an errexit-safe block, relays its handoff commit KV records, and re-enters `review-and-fix step5` when the tree is clean.

## Caller

`skills/implement/SKILL.md` invokes this wrapper from the named `/implement` step so the prompt-side Bash fence remains a plugin-root source guard plus one script call.

## KV grammar

The wrapper relays the underlying helper stdout unchanged unless this file names explicit keys. Explicit keys are newline-delimited `KEY=value` records and must be token-scannable by the orchestrator.

For `--ready-to-commit`, relay the `COMMITTED=`, `ERROR=`, and `SHA=` lines from `review-and-fix commit-fixes --stage-all` unchanged on wrapper stdout. A clean-tree `COMMITTED=false` no-op must not abort under `set -e`.

## Invariants

- Bash 3.2 portable; no associative arrays or namerefs.
- Self-rehydrates `CLAUDE_PLUGIN_ROOT` from `$IMPLEMENT_TMPDIR/plugin-root.env` where needed.
- Telemetry consumers read `LARCH_TOKEN_SESSION_ID`, `LARCH_CLAUDE_SOURCE_FILE`, and `LARCH_TIMING_LEDGER` from `$IMPLEMENT_TMPDIR/session-env.sh` internally instead of relying on inline SKILL.md triplets.
- The round-timing duplicate probe uses awk success-on-match semantics: `found` must exit `0`, and missing rows must exit `1`.
- `--ready-to-commit` exits non-zero before `review-and-fix step5` when porcelain remains non-empty after the handoff commit, including when `COMMITTED=true` left unstaged dirty paths. Empty porcelain continues to `step5` even when `COMMITTED=false`.
- Commit-phase failure exits before `review-and-fix step5`, so wrapper exit-code semantics stay separable from normal Step 5 loop stalls such as `STEP5_REVIEW_STATUS=stall`.
- `skills/implement/SKILL.md` treats commit-phase failure as a terminal Step 5 stall and skips to Step 16. When `STEP5_REVIEW_STATUS=` is present, the orchestrator branches on that envelope instead of treating non-zero exit alone as `resume-handoff-commit-failed`.

## Edit-in-sync

Update `skills/implement/SKILL.md` and the implement structure/timing harnesses when this contract or argv changes.
