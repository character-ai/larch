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

## Validator Pattern: Ratifier

`try_cursor_validation()` uses a **ratifier** pattern: the deterministic classifier's proposed answer and reason are explicitly embedded in the Cursor prompt. The validator may confirm or override, but it sees the deterministic proposal first.

This is a deliberate design choice, not a bug. The rationale: for the vast majority of classification inputs the deterministic heuristics are correct; showing the proposal gives the LLM a fast-path confirmation with low token cost. The bias toward agreement is acceptable because the deterministic classifier itself is conservative (it defaults HARD on ambiguity), and the validator's job is to catch clear misclassifications (e.g. a "doc-only" diff that the deterministic path mis-tagged as SIMPLE), not to be an independent adversarial agent.

Operators who want independent classification should set `CLASSIFY_ISSUE_SKIP_CURSOR=true` to use the deterministic result only. A future "challenger" variant would hide the deterministic proposal until after the LLM emits its own classification; that variant requires a two-pass prompt exchange and is out of scope for current tooling.

## Edit In Sync

Update this contract, `test-classify-issue.sh`, `skills/design/SKILL.md`, and `skills/design/references/heavy-worker.md` together when classification enums or routing semantics change.

On non-zero exit, `FAILURE_LOG=<path>` may appear on stdout.
