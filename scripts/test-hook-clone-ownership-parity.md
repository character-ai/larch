# `test-hook-clone-ownership-parity.sh`

## Purpose

Regression harness for the duplicated clone-ownership helpers in `scripts/hook-bg-poll-guard.sh` and `scripts/hook-no-progress-guard.sh`.

## Invariants

- Extract functions with brace-depth tracking so nested command groups do not truncate a body.
- Extract `canonical_dir()`, `marker_value()`, `marker_candidates()`, `clone_paths_same()`, and `marker_foreign_clone()` from both hooks.
- Compare each extracted same-name function byte-for-byte.
- Compare `marker_step_completed()` with `is_step_completed()` after stripping the differing header and comment-only lines.
- Exercise negative fixtures for brace-depth extraction and renamed-pair drift detection; fixtures isolate `PASS`/`FAIL` counters so expected failures cannot leak into the harness total.
- Exclude `marker_is_live()` versus `is_marker_live()` from byte comparison. They differ by design in:
  - parent-guard return codes,
  - `reset_no_progress_state` missing-marker behavior,
  - the `LIVE_MARKER_DIR` side effect owned by `hook-no-progress-guard.sh`.
- Fail when any guarded helper is missing from either hook or the helper copies drift.

## Edit-in-sync

The hooks stay self-contained by design, so this harness deliberately avoids a shared Bash library. When changing clone-ownership behavior in one hook, make the same helper edit in the sibling hook and run `make test-hook-clone-ownership-parity`.
