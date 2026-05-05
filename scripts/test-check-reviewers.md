# scripts/test-check-reviewers.sh — contract

Regression test for `check-reviewers.sh` probe acceptance logic. Tests the case-insensitive exact-match rule: after whitespace strip + lowercase, the probe reply must equal exactly `"ok"`.

## What it tests

Simulates the normalization pipeline (`tr -d '[:space:]' | tr '[:upper:]' '[:lower:]'`) and verifies healthy/unhealthy classification for representative fixture replies. Also PATH-stubs `gemini` to verify `--include-gemini` output, healthy/unhealthy probe classification, absent-binary output, and the default no-Gemini-key behavior.

## Fixture coverage

- **Positive** (should be healthy): `OK`, `ok`, `Ok`, `oK`, whitespace-padded, newline-terminated
- **Negative** (should be unhealthy): empty, `token`, `broken`, `NotOK`, `Sure OK`, `wok`, `okay`, `OK.`, auth errors, thinking-prefix responses
- **Gemini opt-in**: installed healthy, installed unhealthy, absent binary, and no `--include-gemini`

## Wiring

Target: `make test-harnesses`. Exit 0 on all-pass, exit 1 on any failure.

## Edit-in-sync

| File | Relationship |
|------|-------------|
| `scripts/check-reviewers.sh` | Source of truth for the acceptance rule this harness tests |
| `scripts/check-reviewers.md` | Contract for the script under test |
