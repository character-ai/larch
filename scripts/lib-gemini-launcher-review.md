# lib-gemini-launcher-review.sh

**Purpose**: Sourced-only Gemini review implementation for
`scripts/launch-review.sh --tool gemini`.

## Invariants

- No shebang and no `set -e`; the caller owns process semantics.
- Guarded by `LARCH_LIB_GEMINI_LAUNCHER_REVIEW_LOADED` for idempotent sourcing.
- `GEMINI_REVIEW=1` is required to run the dormant reviewer lane. Without it,
  a valid invocation writes an empty output file, prints an enablement hint on
  stderr, and exits 0 before launching Gemini or writing lifecycle sidecars.
- Defines `_launch_gemini`, which preserves Gemini review JSON normalization,
  model resolution, prompt hardening, dirty-tree sidecar publication, timing
  rows, and the tracked/index snapshot guard.
- The Gemini CLI spawn uses `scripts/lib-external-launcher-common.sh` for the
  per-tool Darwin serial lock and outer auth-startup retry loop. Retry
  classification reads `${RAW_OUTPUT}.diag`, where `run-external-agent.sh
  --capture-stdout-only` routes Gemini stderr before `fail_closed` handles the
  final non-zero exit.
- Rejects specialist-only flags through the unified launcher before this library
  runs; the Gemini path remains generic-only.

## Harness

Covered by `make test-launch-review` and by the Gemini launcher-shaped
`CMD_JSON` retry case in `scripts/test-collect-agent-retry.sh`.

## Edit In Sync

Update `scripts/launch-review.sh`, `scripts/launch-review.md`,
`scripts/test-launch-review.sh`, `scripts/collect-agent-results.sh`, and
`SECURITY.md` when Gemini reviewer CLI flags, policy/snapshot behavior, retry
metadata, or output normalization changes.
