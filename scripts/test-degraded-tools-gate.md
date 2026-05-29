# scripts/test-degraded-tools-gate.sh — contract

Offline regression harness for `scripts/degraded-tools-gate.sh` (the issue #3207
degraded-external-tools gate detector). Full contract lives in the primary
`scripts/degraded-tools-gate.md`.

Covers the state-classification matrix (`ok` / `binary-missing` / `probe-failed`
/ generic `unavailable`) for each tool, the `DEGRADED` boolean, the binary-gate
precedence rule, explanation-block presence/absence, present-only wiring (binary
-found omitted, as `/design` / `/review` / `/research` call it), the `--skill`
label, and the unknown-flag exit-2 path.

Run via `make test-degraded-tools-gate` (registered in the Makefile `.PHONY` list
and the `test-harnesses-1` shard). Makefile-only harness — runtime reachability
of the primary is through the Step 0 `degraded-tools-gate.sh` invocation in
`/design`, `/implement`, `/review`, and `/research` SKILL.md.
