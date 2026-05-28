# test-check-contains-pins.sh

Purpose: black-box regression harness for `scripts/check-contains-pins.sh`.

Primary caller: `make test-check-contains-pins`, with shard coverage through `test-harnesses-15`.

Covered cases: single-quoted happy path, static double-quoted happy path, one-character diverged literal defect with line number, unresolved variable warning, changed-file scoping, multiple defects across files, empty test set, interpolated double-quoted literal skip, and clean-environment Bash invocation plus static checks for Bash 3.2-forbidden constructs.

Fixture strategy: each case creates a disposable git repository containing a copied `scripts/check-contains-pins.sh`, `scripts/lib-quiet.sh`, fixture target files, and fixture `scripts/test-*.sh` files. The harness runs with `LARCH_QUIET_DISABLE=1` so stdout and stderr assertions observe the script contract directly.

Edit in sync: update this harness whenever the verifier CLI, warning text, defect text, path-resolution grammar, or v1 assertion grammar changes.
