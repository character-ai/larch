## Goal
Implement issue #4213: [IMPLEMENTING] [OOS] Token-record sidecar ingestion & token-env hygiene — 6 items.

## Implementation Plan
## Plan

## Approach

- Treat `NO_SKETCHES` as binding.
- Keep the approved outline scope.
- Do not refactor the token ledger subsystem.
- Fix only the named token-record and env-hygiene gaps.
- Prefer existing helpers and harnesses over new infrastructure.
- Apply accepted reviewer corrections:
  - Validation ingestion must mirror research candidate-path expansion.
  - Ship-pr env-cleaning tests must intercept `env ... python3`.
  - Python output-path fallback must be fresh and limited to Codex/Cursor recovery sidecars.

## Files to modify/create

### UPDATED: scripts/lint-fix-loop.sh

- Update the Codex token ingestion block in `run_codex`.
- Keep `token append-record --tmpdir "$IMPLEMENT_TMPDIR"` unchanged in purpose.
- Stop discarding stderr from both token commands.
- Capture stderr in temporary files.
- On non-zero exit:
  - emit the existing warning.
  - include the exit code.
  - relay captured stderr when non-empty.
- On zero exit with stderr:
  - relay stderr as a warning/detail line.
- Run `token record-vendor-sidecar` with a clean active-ledger environment:
  - unset `LARCH_TOKEN_LEDGER`
  - unset `LARCH_TOKEN_SESSION_ID`
  - unset `DESIGN_TMPDIR`
  - unset `RESEARCH_TMPDIR`
  - unset `SESSION_ENV_PATH`
  - set only `IMPLEMENT_TMPDIR="$IMPLEMENT_TMPDIR"` for the active ledger root.
- Ensure temp stderr files are removed on all branches.

### UPDATED: scripts/test-lint-fix-loop.sh

- Update Codex telemetry cases that currently rely on inherited `LARCH_TOKEN_LEDGER`.
- Seed stale parent token env vars in at least one Codex telemetry case:
  - `LARCH_TOKEN_LEDGER`
  - `LARCH_TOKEN_SESSION_ID`
  - `DESIGN_TMPDIR`
  - `RESEARCH_TMPDIR`
  - `SESSION_ENV_PATH`
- Assert active-ledger rows land under the lint-fix `IMPLEMENT_TMPDIR` ledger, not the stale parent ledger.
- Assert the stale parent ledger path is absent or unchanged.
- Add a small failure-stderr fixture for `record-vendor-sidecar` so warning relay is pinned.

### UPDATED: scripts/launch-codex-drafter.sh

- Track whether the stable token-record path was actually written.
- Set a boolean such as `TOKEN_RECORD_AVAILABLE=false` before launch.
- Set it to true only when:
  - raw `${_codex_raw}.token-record` exists and is non-empty.
  - `cp -p` to `${OUTPUT_CANON}.token-record` succeeds.
  - the stable file exists and is non-empty.
- Replace every unconditional `emit_kv TOKEN_RECORD "${OUTPUT_CANON}.token-record"` with a small helper:
  - emit `TOKEN_RECORD=<stable path>` only when the stable sidecar exists.
  - otherwise emit `TOKEN_RECORD_MISSING=true`.
- Preserve the existing warning on copy failure.
- Do not fail the drafter only because token-record copy failed.

### UPDATED: scripts/test-launch-codex-drafter.sh

- Extend the existing token-copy-failure case.
- Assert stdout does not contain `TOKEN_RECORD=<missing stable path>` when the copy fails.
- Assert stdout contains `TOKEN_RECORD_MISSING=true`.
- Keep the current checks that:
  - drafter still succeeds.
  - warning includes both token-record paths.
  - stable `.token-record` is absent.

### UPDATED: skills/design/scripts/design-step2b-drafter.sh

- Update Codex drafter active-ledger ingestion env cleanup.
- Replace the current `env -u IMPLEMENT_TMPDIR DESIGN_TMPDIR=...` with the complete clean env set:
  - unset `LARCH_TOKEN_LEDGER`
  - unset `LARCH_TOKEN_SESSION_ID`
  - unset `IMPLEMENT_TMPDIR`
  - unset `RESEARCH_TMPDIR`
  - unset `SESSION_ENV_PATH`
  - set `DESIGN_TMPDIR="$DESIGN_TMPDIR"`.
- Keep append-record bound to `--tmpdir "$DESIGN_TMPDIR"`.
- Keep the existing fail-soft warnings.

### UPDATED: skills/design/scripts/test-design-step2b-drafter.sh

- Seed stale `LARCH_TOKEN_SESSION_ID`, `LARCH_TOKEN_LEDGER`, and `IMPLEMENT_TMPDIR` in the fresh-sidecar case.
- Assert active ledger rows are written only under `DESIGN_TMPDIR`.
- Assert no active ledger appears under stale `IMPLEMENT_TMPDIR`.
- If practical, assert the active ledger session is not the stale parent `LARCH_TOKEN_SESSION_ID`.

### UPDATED: python/agents.py

- Add a small helper for sidecar ingestion env cleanup, similar to `python/checks.py`:
  - start from `os.environ`.
  - remove `LARCH_TOKEN_LEDGER`.
  - remove `LARCH_TOKEN_SESSION_ID`.
  - remove `DESIGN_TMPDIR`.
  - remove `RESEARCH_TMPDIR`.
  - remove `SESSION_ENV_PATH`.
  - set `IMPLEMENT_TMPDIR` when provided.
  - otherwise set the effective tmpdir key that matches the caller only if needed.
- Update `ingest_launcher_token_sidecar`.
- Preserve existing stdout `TOKEN_RECORD=` parsing.
- Add a Bash-parity output fallback only when explicitly allowed by the caller:
  - stdout has no `TOKEN_RECORD=`.
  - `allow_output_fallback` is true.
  - `output` is provided.
  - `${output}.token-record` exists and is non-empty.
- Keep stdout `TOKEN_RECORD=` handling unchanged for all tiers.
- Do not fallback-ingest Claude `.token-record` sidecars.
- Keep de-duplication semantics:
  - `append-record` once per unique sidecar path.
  - `record-vendor-sidecar` on every invocation for a resolved sidecar.
- Pass the cleaned env to the `record-vendor-sidecar` runner call.
- Keep the helper pure enough for direct unit tests.

### UPDATED: python/ci_monitor.py

- Gate Python CI-fix output fallback to Codex and Cursor only.
- Pass `allow_output_fallback=True` only for Codex/Cursor CI-fix launchers.
- Pass `allow_output_fallback=False` or omit it for Claude.
- Prevent stale stable sidecar reuse before launch:
  - remove the expected `${output}.token-record` fallback path before invoking a Codex/Cursor launcher, or
  - otherwise prove the fallback sidecar was produced by the current launch.
- Keep stdout `TOKEN_RECORD=` ingestion behavior unchanged.
- Do not change `python/ship.py` unless inspection during implementation finds a separate Python ship recovery path that bypasses `ci_monitor._make_default_launch_fn`.

### UPDATED: python/test_agents.py

- Add direct tests for `ingest_launcher_token_sidecar`.
- Cover `TOKEN_RECORD=` stdout path.
- Cover fallback to `${output}.token-record` when stdout lacks `TOKEN_RECORD=` and `allow_output_fallback=True`.
- Cover no fallback when `allow_output_fallback=False`.
- Cover missing stdout token and missing fallback sidecar returning `False`.
- Cover de-dup behavior:
  - first call runs `append-record` and `record-vendor-sidecar`.
  - repeat call runs only `record-vendor-sidecar`.
- Seed stale env vars and assert the `record-vendor-sidecar` call receives a clean env.
- Assert `IMPLEMENT_TMPDIR` is set to the provided implement tmpdir in that env.

### UPDATED: python/test_ci_monitor.py

- Add or extend a focused CI monitor ingestion test.
- Assert Codex/Cursor CI-fix paths pass `allow_output_fallback=True`.
- Assert Claude paths do not use output fallback.
- Assert a Claude `${output}.token-record` without stdout `TOKEN_RECORD=` is not fallback-ingested.
- Assert the expected Codex/Cursor fallback sidecar path is cleared before launch, or otherwise assert freshness enforcement.

### UPDATED: scripts/ship-pr.sh

- Update `ship_pr_ingest_token_record_once`.
- Keep `append-record --tmpdir "$IMPLEMENT_TMPDIR"` as-is.
- Change the active-ledger command to run with:
  - unset `LARCH_TOKEN_LEDGER`
  - unset `LARCH_TOKEN_SESSION_ID`
  - unset `DESIGN_TMPDIR`
  - unset `RESEARCH_TMPDIR`
  - unset `SESSION_ENV_PATH`
  - set `IMPLEMENT_TMPDIR="$IMPLEMENT_TMPDIR"`.
- Preserve current warning recording via `record_failure`.

### UPDATED: scripts/test-ship-pr-rebase.sh

- Extend the existing sidecar-ingestion cases.
- Replace function-only `python3()` interception for env-prefixed commands with a temporary PATH-front executable `python3` stub.
- Keep any function stub only for calls that are not invoked through `env`.
- Make the executable stub log relevant env values for `record-vendor-sidecar`.
- Seed stale parent token env vars before calling `run_ci_fix_vendor`.
- Assert `record-vendor-sidecar` sees:
  - `IMPLEMENT_TMPDIR` set to the case implement tmpdir.
  - no `LARCH_TOKEN_LEDGER`.
  - no `LARCH_TOKEN_SESSION_ID`.
  - no `DESIGN_TMPDIR`.
  - no `RESEARCH_TMPDIR`.
  - no `SESSION_ENV_PATH`.
- Keep existing ordering assertions that ingestion happens before rollback.

### UPDATED: skills/research/references/validation-phase.md

- Add a token sidecar ingestion block for validation after `collect-agent-results.sh --validation-mode` completes and after collector output has been parsed enough to know each lane `REVIEWER_FILE`.
- Run the ingestion block before validation status decisions, runtime fallback handling, or finding merge behavior.
- Mirror the research-phase candidate-path logic.
- For each selected validation lane:
  - include collector `REVIEWER_FILE` when present.
  - include the fixed `COLLECT_ARGS` output path.
  - include `${fixed%.txt}-retry.txt`.
  - include `${fixed%.txt}-ns-retry.txt`.
  - dedupe candidate paths before ingestion.
- For each deduped candidate path:
  - set `SIDECAR="${CANDIDATE}.token-record"`.
  - if it exists and is non-empty, run `token append-record --input "$SIDECAR" --tmpdir "$RESEARCH_TMPDIR"`.
  - then run `token record-vendor-sidecar --input "$SIDECAR"` with clean env.
- Use the same stderr capture and warning relay shape as `research-phase.md`.
- Keep active-ledger env clean:
  - unset `LARCH_TOKEN_LEDGER`
  - unset `LARCH_TOKEN_SESSION_ID`
  - unset `IMPLEMENT_TMPDIR`
  - unset `DESIGN_TMPDIR`
  - unset `SESSION_ENV_PATH`
  - set `RESEARCH_TMPDIR="$RESEARCH_TMPDIR"`.
- Document absent sidecars as no-ops.
- State ingestion is independent of collector status.
- Do not alter validation negotiation, fallback, or finding merge behavior.

### UPDATED: scripts/test-research-structure.sh

- Add static structural pins for research and validation sidecar ingestion.
- For `research-phase.md`, assert the existing ingestion block contains:
  - `token append-record`
  - `token record-vendor-sidecar`
  - `env -u LARCH_TOKEN_LEDGER`
  - `-u LARCH_TOKEN_SESSION_ID`
  - `RESEARCH_TMPDIR="$RESEARCH_TMPDIR"`.
- For `validation-phase.md`, assert the new ingestion block contains the same critical tokens.
- Assert validation ingestion appears after the `collect-agent-results.sh --timeout 1860 --substantive-validation --validation-mode` line.
- Assert validation ingestion appears after collector `REVIEWER_FILE` parsing or mapping.
- Assert validation ingestion appears before status decision instructions.
- Assert validation candidate expansion includes:
  - `REVIEWER_FILE`
  - `-retry.txt`
  - `-ns-retry.txt`
  - candidate de-duplication.

## Edge cases

- **No sidecar exists**: ingestion remains a no-op.
- **Validation retry output**: sidecars beside `REVIEWER_FILE`, `-retry.txt`, or `-ns-retry.txt` are ingested once.
- **Validation duplicate candidates**: the same path is de-duped before append-record and active recording.
- **Copy failure in Codex drafter**: drafter may still succeed, but stdout must not point consumers at a missing stable sidecar.
- **Repeated recovery attempts**: Python and Bash ship paths should append once per sidecar but still active-record each resolved sidecar invocation where that is current behavior.
- **Stale parent env**: active-ledger ingestion must not use a parent ledger path or parent token session id.
- **Token command warning output with exit 0**: preserve it so unsupported or partial parser diagnostics are visible.
- **Python Claude CI sidecar**: output fallback must not ingest it unless a future feature explicitly scopes that in.
- **Stale stable CI-fix sidecar**: fallback must not pick up a sidecar from a previous launch.
- **Validation zero-externals branch**: no ingestion block runs because `collect-agent-results.sh` is skipped and no validation lane sidecars exist.

## Failure modes

- If env cleanup is incomplete, `resolve_session_id` can still prefer stale `LARCH_TOKEN_SESSION_ID` over tmpdir `session-id`.
- If drafter emits `TOKEN_RECORD=` after copy failure, downstream ingestion can try to ingest a path that was never written.
- If Python ship fallback only trusts stdout, a launcher that writes `${output}.token-record` but omits `TOKEN_RECORD=` can still drop Codex/Cursor CI-fix usage.
- If Python output fallback is not tier-gated, Claude CI usage can be double-counted.
- If Python output fallback does not prove freshness, stale stable sidecars can be ingested.
- If validation prompt instructions ingest only fixed output stems, retry sidecars can be collected but never ingested.
- If ship-pr tests keep function-only stubs, `env ... python3` can bypass the stub and invalidate env assertions.

## Testing strategy

- Run focused harnesses:
  - `make test-lint-fix-loop`
  - `make test-launch-codex-drafter`
  - `make test-design-step2b-drafter`
  - `make test-ship-pr-rebase`
  - `make test-research-structure`
- Run focused Python tests:
  - `python3 -m pytest python/test_agents.py python/test_checks.py python/test_ci_monitor.py python/test_rebase.py`
- Run the repository-selected check set after implementation:
  - `bash scripts/relevant-checks.sh`

## Acceptance

- `scripts/lint-fix-loop.sh` `run_codex` calls `token record-vendor-sidecar` via `env -u LARCH_TOKEN_LEDGER -u LARCH_TOKEN_SESSION_ID -u DESIGN_TMPDIR -u RESEARCH_TMPDIR -u SESSION_ENV_PATH IMPLEMENT_TMPDIR=...` and relays stderr from both token commands on failure and non-empty success.
- `scripts/launch-codex-drafter.sh` emits `TOKEN_RECORD=<path>` only when the stable sidecar exists; emits `TOKEN_RECORD_MISSING=true` otherwise.
- `skills/design/scripts/design-step2b-drafter.sh` calls `token record-vendor-sidecar` via `env -u LARCH_TOKEN_LEDGER -u LARCH_TOKEN_SESSION_ID -u IMPLEMENT_TMPDIR -u RESEARCH_TMPDIR -u SESSION_ENV_PATH DESIGN_TMPDIR=...`.
- `python/agents.py` `ingest_launcher_token_sidecar` passes a clean env dict (ledger keys removed, `IMPLEMENT_TMPDIR` set) to `record-vendor-sidecar`; supports optional `allow_output_fallback` for Codex/Cursor paths.
- `python/ci_monitor.py` passes `allow_output_fallback=True` for Codex/Cursor CI-fix launchers only and pre-clears the expected fallback sidecar path before each launch.
- `scripts/ship-pr.sh` `ship_pr_ingest_token_record_once` calls `token record-vendor-sidecar` via `env -u LARCH_TOKEN_LEDGER -u LARCH_TOKEN_SESSION_ID -u DESIGN_TMPDIR -u RESEARCH_TMPDIR -u SESSION_ENV_PATH IMPLEMENT_TMPDIR=...`.
- `skills/research/references/validation-phase.md` has a Codex sidecar ingestion block with candidate expansion matching `research-phase.md` and proper `env -u` including `LARCH_TOKEN_SESSION_ID`.
- All affected harnesses pass: `make test-lint-fix-loop`, `make test-launch-codex-drafter`, `make test-design-step2b-drafter`, `make test-ship-pr-rebase`, `make test-research-structure`, and `python3 -m pytest python/test_agents.py python/test_ci_monitor.py`.

diff_lines: 340

## Test plan
(no test plan section in plan-file)
