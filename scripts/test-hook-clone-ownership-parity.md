# `test-hook-clone-ownership-parity.sh`

## Purpose

Regression harness for the duplicated clone-ownership helpers in `scripts/hook-bg-poll-guard.sh` and `scripts/hook-no-progress-guard.sh`.

## Invariants

- Extract `canonical_dir()`, `marker_value()`, `marker_candidates()`, `clone_paths_same()`, and `marker_foreign_clone()` from both hooks.
- Compare each extracted function byte-for-byte.
- Fail when any guarded helper is missing from either hook or the helper copies drift.

## Edit-in-sync

The hooks stay self-contained by design, so this harness deliberately avoids a shared Bash library. When changing clone-ownership behavior in one hook, make the same helper edit in the sibling hook and run `make test-hook-clone-ownership-parity`.
