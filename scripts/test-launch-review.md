# test-launch-review.sh

**Purpose**: Offline regression harness for `scripts/launch-review.sh`.

## Coverage

- Dispatcher validation for missing and invalid `--tool`.
- Gemini rejection of specialist-only flags.
- Codex review launcher assertions from the former per-tool harness: timeout
  validation, prompt replay, dirty-tree sidecars, model argv handling,
  `--add-dir`, token-budget cap, and specialist `--diff-file`.
- Cursor review launcher assertions from the former per-tool harness: JSON
  post-processing, outer retry metadata, prompt byte preservation, signal-trap
  sentinel publication, auth-preflight short-circuit, and dirty-tree sidecars.
- Gemini review launcher assertions from the former per-tool harness:
  `GEMINI_REVIEW=1` gating, JSON normalization, `jq` fail-closed behavior,
  model rejection, prompt hardening, token-session rehydration, timeout
  clamping, and snapshot guard behavior.

## Makefile

Run directly as `scripts/test-launch-review.sh` or through
`make test-launch-review`. The target is included in `test-harnesses-2`.

## Edit In Sync

Update this harness with every `scripts/launch-review.sh` argv, sidecar,
retry, timing, token-budget, prompt-hardening, or vendor-output behavior change.
