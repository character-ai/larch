# scripts/test-audit-edit-write.sh — contract

Regression harness for `scripts/audit-edit-write.sh`. Wired into `make lint` via the `test-audit-edit-write` target. The full contract — including invariants, output shape, and edit-in-sync rules — lives in `scripts/audit-edit-write.md`; this stub exists so every `.sh` in `scripts/` has a sibling per `.claude/rules/script-md-siblings.md`. Edits to either the script or the harness must stay in sync in the same PR.
