# test-oos-disposition-gate.sh

Regression harness for `oos-disposition-gate.sh` and `oos-disposition-checkpoint.sh`. See `oos-disposition-gate.md` and `oos-disposition-checkpoint.md` for contracts.

## Gate cases

Covers strict `--filed-urls-strict-file` counting (`S1`–`S3`) alongside legacy loose-file and ndjson cases (fork/repo-unavailable skip, disposition gap, invalid range, rejected markers, URL union, and related edge cases).

## Checkpoint cases

Harness prelude asserts `oos-disposition-checkpoint.sh` is executable (`[ -x "$CHECKPOINT" ]`).

- Proceed with zero non-security OOS (exit 0)
- Proceed with filed URL satisfied (exit 0)
- Disposition gap (exit 1) with `Tool Failures` log asserting `step-8-oos-checkpoint` and `oos-disposition-checkpoint.sh`
- Fork-mode skip (exit 0)
- Repo-unavailable skip (exit 0)
- Ndjson RUN_ID-keyed path with rejection markers (exit 0)
- Stale RUN_ID: keyed path missing, sole foreign `oos-issues.ndjson` — no find bind (exit 2, validation site)
- Single `find` fallback when `session-id` absent (exit 0)
- Ambiguity (exit 2): multiple ndjson dirs without `session-id`; logs validation site and checkpoint stderr
- Precondition (exit 2): non-security OOS without resolvable ndjson
- Gate exit 2 passthrough (gate validation) with gate stderr log
- Merge-base absent: `origin/main` ref with empty merge-base uses `origin/main..HEAD` disposition range; harness expects disposition-gap exit 1
- `origin/main` absent: commit range `HEAD`; harness expects disposition-gap exit 1
- Design path: `--design-tmpdir` strict URL pass; `--design-tmpdir` unresolved OOS (exit 1)
- Design path: `design-export/` fallback pass; `design-export/` unresolved OOS (exit 1)
- Missing `--design-tmpdir` value (exit 2, logs under implement tmpdir)
- Security sidecar only (exit 3): non-security disposition is clear, but private `SECURITY.md` disposition remains required.

Makefile target: `test-oos-disposition-gate` (one target covers both scripts).
