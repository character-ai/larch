# test-launch-review.sh

**Purpose**: Offline regression harness for `scripts/launch-review.sh`.

## Coverage

- Dispatcher validation for missing and invalid `--tool`.
- Codex review launcher assertions from the former per-tool harness: timeout
  validation, prompt replay, dirty-tree sidecars, model argv handling,
  `--add-dir`, token-budget cap, and specialist `--diff-file`.
- Cursor review launcher assertions from the former per-tool harness: JSON
  post-processing, explicit empty `.result` marker promotion, outer retry
  metadata, prompt byte preservation, signal-trap sentinel publication,
  auth-preflight short-circuit, exact stdin-file inheritance on the non-Codex
  control path, and dirty-tree sidecars.
- Successful Codex and Cursor launches with no stderr populate their sidecars
  with informational `codex-status: ok` / `cursor-status: ok` markers.
- Model rejection, prompt hardening, token-session rehydration, timeout
  clamping, and snapshot guard behavior.

## Makefile

Run directly as `scripts/test-launch-review.sh` or through
`make test-launch-review`. The target is included in `test-harnesses-2`.
The harness unsets inherited session tempdir variables and points
`LARCH_EXECUTION_ISSUES_LOG` at each suite's tempdir so offline launch failures
cannot append to a parent `/implement` run's log.

## Edit In Sync

Update this harness with every `scripts/launch-review.sh` argv, sidecar,
retry, timing, token-budget, prompt-hardening, or vendor-output behavior change.
