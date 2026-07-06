# test-audit-edit-write.sh

Regression harness for `scripts/audit-edit-write.sh`. Wired into `make lint` via the `test-audit-edit-write` target. The full contract, including invariants, output shape, and edit-in-sync rules, lives in `scripts/audit-edit-write.md`; this sibling stub keeps the harness discoverable. Edits to either the script or the harness must stay in sync in the same PR.
