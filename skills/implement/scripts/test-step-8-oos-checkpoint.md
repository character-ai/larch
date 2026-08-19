# test-step-8-oos-checkpoint.sh

Offline harness for `step-8-oos-checkpoint.sh`.

## Coverage

- The wrapper delegates to `scripts/larch.sh implement step-8-oos-checkpoint`.
- No Python command owner or direct disposition-checkpoint call remains in the wrapper.
- Rust black-box tests own the stdout, exit-code, and bookkeeping parity contract.

## Edit-in-sync

Update this harness when `step-8-oos-checkpoint.sh` changes its delegation or stdout contract.
