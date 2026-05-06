# scripts/test-check-reviewers.sh — contract

Regression test for `check-reviewers.sh` probe acceptance logic. Tests the case-insensitive exact-match rule: after whitespace strip + lowercase, the probe reply must equal exactly `"ok"`.

## What it tests

Simulates the normalization pipeline (`tr -d '[:space:]' | tr '[:upper:]' '[:lower:]'`) and verifies healthy/unhealthy classification for representative fixture replies. It also stubs `codex` / `cursor` with sleeping binaries for the wait-preflight infrastructure-error case and stubs `gemini` on PATH to run `check-reviewers.sh --probe --include-gemini` for JSON `.response` extraction, JSON `.error` failure, the `MISSING_JQ` diagnostic path, and Gemini tool-catalog drift classification. It does NOT launch real Codex/Cursor probes.

## Fixture coverage

- **Positive** (should be healthy): `OK`, `ok`, `Ok`, `oK`, whitespace-padded, newline-terminated
- **Negative** (should be unhealthy): empty, `token`, `broken`, `NotOK`, `Sure OK`, `wok`, `okay`, `OK.`, auth errors, thinking-prefix responses
- **Wait infrastructure**: invalid `WAIT_FOR_REVIEWERS_POLL_INTERVAL=00` emits `WAIT_INFRA_ERROR`, marks available tools as `*_HEALTHY=false`, skips retry attempt 2, and launches no sleeping probe wrapper. A separate Gemini-inclusive fixture pins value-side `=` preservation and confirms the Gemini drift checker does not run on the infra-error branch.
- **Gemini integration**: stubbed `{"response":"OK"}` succeeds; stubbed `{"error":"auth failed"}` fails; forced missing-`jq` fails closed.
- **Gemini drift alarm**: clean known catalog, benign unknown warning, write-style unknown health flip, raw hyphen/dot/camelCase write-style names, anchored-token negative coverage for `metadata_writer_index`, unavailable discovery fixture fallback, policy parser failure, fixture checksum mismatch, fixture-known write-style tool missing from the deny list, and hung `/tools` discovery timeout.

## Wiring

Target: `make test-harnesses`. Exit 0 on all-pass, exit 1 on any failure.

## Edit-in-sync

| File | Relationship |
|------|-------------|
| `scripts/check-reviewers.sh` | Source of truth for the acceptance rule this harness tests |
| `scripts/check-reviewers.md` | Contract for the script under test |
