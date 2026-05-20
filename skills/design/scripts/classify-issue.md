# classify-issue.sh

## Purpose

`classify-issue.sh` classifies a `/design` request as `TRIVIAL_DOC_ONLY`, `SIMPLE`, or `HARD` using deterministic heuristics and optional Cursor validation.

## Primary Callers

- `skills/design/scripts/design-driver.sh` for `ACTION=CLASSIFY`
- `/design` Step 0 tail when no trusted caller-forwarded classification is present

Caller-forwarded `/implement` classifications bypass this script when `/design` receives both `--design-classification` and trusted `--branch-info`.

## Invariants

- Deterministic classification always runs first.
- Cursor validation must go through `scripts/run-external-agent.sh`, use `cursor agent -p --trust --mode plan`, and treat feature/diff text as untrusted data.
- Cursor output only influences the result when it emits a valid `CLASSIFICATION=<enum>` record.
- Cursor failure, timeout, malformed output, or missing binary falls back to the deterministic result.
- `CLASSIFICATION_SOURCE` on stdout may be `deterministic`, `cursor-validated`, or `cursor-fallback`. Callers that write `run-params.json` map non-forwarded sources to `router-pre-design`.
- `try_cursor_validation()` acquires the per-tool KeyChain serial lock (`external_serial_lock_acquire` from `scripts/lib-external-launcher-common.sh`) immediately before the `run-external-agent.sh` call and releases it asynchronously via `external_serial_lock_release_after`.

## Makefile Wiring

The regression harness is `make test-classify-issue`, wired into `test-harnesses-1`.

## Harness

`test-classify-issue.sh` covers deterministic doc-only/simple/hard paths, Cursor confirmation, Cursor override, Cursor-unavailable fallback, malformed Cursor output fallback, and untrusted input containing prompt-like text.

## Edit In Sync

Update this contract, `test-classify-issue.sh`, `skills/design/SKILL.md`, and `skills/design/references/heavy-worker.md` together when classification enums or routing semantics change.

On non-zero exit, `FAILURE_LOG=<path>` may appear on stdout.
