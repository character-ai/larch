# test-block-submodule-edit.sh

Regression harness for `scripts/block-submodule-edit.sh`. Wired into `make lint` via the `test-block-submodule` target. The full contract is owned by `scripts/block-submodule-edit.md`; this sibling stub keeps the harness discoverable and auditable. Edits to either side must stay in sync in the same PR.
