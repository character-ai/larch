# test-verify-run-log-completeness.sh contract

## Purpose

`scripts/test-verify-run-log-completeness.sh` is the regression harness for
`scripts/verify-run-log-completeness.sh`.

## Coverage

The harness verifies:

- manifest batch slugs and extensions stay aligned with `scripts/larch-log-batches.sh`
- condition-gated rows, including `step7a`, `step8`, and `step9a1`, stay aligned with `scripts/larch-log-batches.sh`
- fully populated Step-7a-complete trees emit `OK`
- missing required Step-7a files, including `session-transcript.jsonl`, emit `MISSING=...`
- pre-Step-7a partial trees do not falsely require Step-7a+ batches
- Step-8 trees do not falsely require Step-9a.1-only batches
- missing run directories still fail with a descriptive error

## Edit-in-sync

Update this harness when either of these changes:

- `docs/run-logs-required-files.tsv` condition semantics or required paths change
- `scripts/verify-run-log-completeness.sh` reachability inference changes
