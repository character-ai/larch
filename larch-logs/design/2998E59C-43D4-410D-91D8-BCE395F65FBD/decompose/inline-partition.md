## Pieces

### Piece 1: Harness inventory reconciliation
- Scope: Reconcile `Makefile` shard-line assignments, `scripts/residual-bash-paths.txt` stale-entry removal, `scripts/test-harness-shards-coverage.sh` CARVE_OUTS and self-test update, and conditional `.github/workflows/ci.yaml` shard rebalance.
- Firm-headings: Makefile, scripts/residual-bash-paths.txt, scripts/test-harness-shards-coverage.sh
- Acceptance: `make test-harness-shards-coverage` and its self-test pass; residual-bash-paths.txt has no stale entries; every remaining Bash harness is in exactly one shard; no pytest recipe is in any shard.
- Dependencies: none
- Size estimate: 200 diff lines

### Piece 2: Documentation and reference sweep
- Scope: Sweep `agent-lint.toml` comment blocks for retired harnesses, update I-Outcome-1 in `ARCHITECTURAL_INVARIANTS.md`, and reconcile the harness inventory section of `docs/linting.md`.
- Firm-headings: agent-lint.toml, ARCHITECTURAL_INVARIANTS.md, docs/linting.md
- Acceptance: `make lint` passes; agent-lint.toml has no comments referencing deleted test scripts; ARCHITECTURAL_INVARIANTS.md cites only the surviving pytest twin for Step 7a; docs/linting.md inventory section is accurate.
- Dependencies: blocked-by Piece 1
- Size estimate: 100 diff lines
