# test-oos-disposition-gate.sh

Regression harness for `oos-disposition-gate.sh` and `oos-disposition-checkpoint.sh`. See `oos-disposition-gate.md` and `oos-disposition-checkpoint.md` for contracts.

## Gate cases

Covers strict `--filed-urls-strict-file` counting (`S1`–`S3`) alongside legacy loose-file and ndjson cases (fork/repo-unavailable skip, disposition gap, invalid range, rejected markers, URL union, and related edge cases).

## Checkpoint cases

Harness prelude asserts `oos-disposition-checkpoint.sh` is executable (`[ -x "$CHECKPOINT" ]`).

- Proceed with zero non-security OOS or filed URL satisfied
- Disposition gap (exit 1) with `Tool Failures` log asserting `step-8-oos-checkpoint` and `oos-disposition-checkpoint.sh`
- Fork-mode and repo-unavailable skips (exit 0)
- Ndjson discovery: RUN_ID-keyed path; single-find fallback without `session-id`
- Ambiguity (exit 2): multiple ndjson dirs without `session-id`; logs validation site and checkpoint stderr
- Precondition (exit 2): non-security OOS without resolvable ndjson
- Gate exit 2 passthrough (invalid range) with gate stderr log
- Merge-base absent: `origin/main` ref with empty merge-base uses `origin/main..HEAD` and proceeds
- Design path: `--design-tmpdir` vs `design-export/` fallback

Makefile target: `test-oos-disposition-gate` (one target covers both scripts).
