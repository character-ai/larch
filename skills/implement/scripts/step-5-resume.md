# step-5-resume.sh

Step 5 main-agent handoff resume helper. Records round timing, exits immediately for `--record-only`, delegates the `--ready-to-commit` commit phase to `python/cli.py implement commit-route --site step5-resume-handoff`, and re-enters `review-and-fix step5` only when commit-route emits `NEXT_ACTION=continue`. Resume reuses the persisted difficulty override while `review-and-fix step5` reuses recorded audit and escalation state.

## Caller

`skills/implement/SKILL.md` invokes this wrapper from the named `/implement` step so the prompt-side Bash fence remains a plugin-root source guard plus one script call.

## KV grammar

The wrapper relays explicit commit-route KVs as newline-delimited `KEY=value` records that the orchestrator can scan:

- `NEXT_ACTION=continue|stall`
- `COMMITTED=`
- `ERROR=`
- `SHA=`
- `COMMIT_OUTCOME=ok|noop|failed`

`--ready-to-commit` parses `NEXT_ACTION=` only from newline-delimited records whose key is exactly `NEXT_ACTION` at the start of the line. Exactly one line-anchored `NEXT_ACTION=` is required. The wrapper relays `NEXT_ACTION=` on both stall and continue branches before the remaining filtered commit KVs.

The commit phase is captured with an errexit-safe block:

```bash
set +e
commit_output="$(python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" implement commit-route --site step5-resume-handoff)"
commit_rc=$?
set -e
```

This capture is required so usage errors, seed failures, and commit-route stalls can still be parsed and relayed from captured stdout. Missing, duplicated, or malformed `NEXT_ACTION=` relays any captured explicit KVs and exits non-zero so the orchestrator enters the lacks-envelope preflight/resume failure branch.

## Invariants

- Bash 3.2 portable; no associative arrays or namerefs.
- Self-rehydrates `CLAUDE_PLUGIN_ROOT` from `$IMPLEMENT_TMPDIR/plugin-root.env` where needed.
- For telemetry key definitions, see `skills/shared/session-setup-output.md`; resume paths use `$IMPLEMENT_TMPDIR/session-env.sh`.
- The round-timing duplicate probe uses awk success-on-match semantics: `found` must exit `0`, and missing rows must exit `1`.
- `--ready-to-commit` exits before `review-and-fix step5` unless the parsed route is exactly `NEXT_ACTION=continue`.
- Porcelain probing for the resume-handoff site lives inside `commit-route`, not in this wrapper.
- A Python `commit-route` rc `0` with `NEXT_ACTION=stall` means durable stall state is already seeded. The wrapper relays that route and exits `1` so the immediate-background fence visibly fails while the orchestrator can still parse `NEXT_ACTION=stall` from stdout.
- `STEP5_REVIEW_STATUS=` is the only Step 6 authorization. `NEXT_ACTION=continue` proves only that the commit phase completed and `review-and-fix step5` was allowed to start.

## Python parity

`python3 python/cli.py implement step-5-resume` (`step5_resume_main` in `python/implement_dispatch.py`) uses the same shared commit-route helper for the ready-to-commit phase. It treats `NEXT_ACTION=stall` as a terminal commit-phase failure, returns non-zero, relays `NEXT_ACTION`, and does not relaunch `review-and-fix step5`. Coverage lives in `python/test_implement_dispatch.py` (`test_step5_resume_*`).

## Edit-in-sync

Update `skills/implement/SKILL.md` and the implement structure/timing harnesses when this contract or argv changes. Keep `step5_resume_main` in `python/implement_dispatch.py` and `python/test_implement_dispatch.py` at commit-route parity when changing the commit-handoff behavior here.
