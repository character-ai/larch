# step-8-python-guard.sh

Thin wrapper for the Rust-owned Python 3.11 guard used by `/implement` Step 8.

## Caller

The surviving Python pre-driver invokes `scripts/larch.sh implement step-8-python-guard` through the verified bootstrap. The Rust ship child calls the same guard implementation in process. This wrapper preserves direct path invocation and plugin-root rehydration.

## Contract

Rust runs a fixed `python3 -c` version probe. On Python 3.11 or newer, the command exits `0` with no stdout. If the probe fails or Python is older, it writes `ERROR: Ship merge and finalize dependencies require Python 3.11 or newer` to stderr, emits the single-line STALLED JSON object on stdout, and exits `4`.

The diagnostic retains its historical merge wording for byte compatibility; after issue #8788, only the surviving Python finalizer requires this probe.

## Edit-in-sync

Keep `crates/larch-cli/src/implement_ship_commands.rs`, the Rust black-box parity test, and the Step 8 JSON routing contract aligned.
