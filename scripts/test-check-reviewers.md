# scripts/test-check-reviewers.sh — contract

Regression test for `check-reviewers.sh` probe acceptance logic. Tests the case-insensitive exact-match rule: after whitespace strip + lowercase, the probe reply must equal exactly `"ok"`.

## What it tests

Simulates the normalization pipeline (`tr -d '[:space:]' | tr '[:upper:]' '[:lower:]'`) and verifies healthy/unhealthy classification for representative fixture replies. It also stubs `gemini` on PATH and runs `check-reviewers.sh --probe --include-gemini` to cover JSON `.response` extraction, JSON `.error` failure, and the `MISSING_JQ` diagnostic path. It does NOT launch real Codex/Cursor probes.

## Fixture coverage

- **Positive** (should be healthy): `OK`, `ok`, `Ok`, `oK`, whitespace-padded, newline-terminated
- **Negative** (should be unhealthy): empty, `token`, `broken`, `NotOK`, `Sure OK`, `wok`, `okay`, `OK.`, auth errors, thinking-prefix responses
- **Gemini integration**: stubbed `{"response":"OK"}` succeeds; stubbed `{"error":"auth failed"}` fails; forced missing-`jq` fails closed.

## Wiring

Target: `make test-harnesses`. Exit 0 on all-pass, exit 1 on any failure.

## Edit-in-sync

| File | Relationship |
|------|-------------|
| `scripts/check-reviewers.sh` | Source of truth for the acceptance rule this harness tests |
| `scripts/check-reviewers.md` | Contract for the script under test |
