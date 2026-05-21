# plan-block-write.sh contract

## Purpose

Atomically replaces the plan marker block in an issue body, or appends a new block when markers are absent. Full composed body is piped through `scripts/redact-secrets.sh` before `gh issue edit --body-file`.

## Interface

```
plan-block-write.sh --issue <N> --content-file <path> [--repo OWNER/REPO]
```

## Output Contract

- Success: `WRITTEN=true`, `MODE=appended|replaced`, `MARKERS_PRESENT=true|false` (pre-edit), `BODY_BYTES=<n>`, exit 0.
- Malformed current body: `MALFORMED=<token>` (same tokens as `plan-block-read.sh`), exit 1.
- `gh` failure: `FAILED=true`, `ERROR=…`, exit 2.
- Redaction helper missing / failure: `FAILED=true`, `ERROR=…`, exit 3.

## Test Harness

```
bash scripts/test-plan-block.sh
```

## Edit-in-sync

Update with `scripts/plan-block-read.sh`, `scripts/test-plan-block.sh`, and `scripts/plan-block-read.md`.
