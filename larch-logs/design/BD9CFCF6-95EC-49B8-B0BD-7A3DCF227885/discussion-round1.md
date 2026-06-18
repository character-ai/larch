## Decision 1: Scope — all three gaps
- **Question**: Issue #4712 documents three independent gaps (#1 legacy-prefix ALLOW omission, #2 test-partition overlap, #3 uncommitted review-loop fixes → ship stall). Which to address?
- **Resolution**: All three, smallest change per gap. The specific instances are already patched; this design is preventive/systemic.
- **Source**: user

## Decision 2: Handling #1/#2 — prevent at source + self-heal in CI
- **Question**: How to handle the two CI-harness-contract gaps, given CI already catches them and the operator relies on CI?
- **Resolution**: Two prongs. (a) Prevent at source: add an implementer-prompt checklist so implementers extend `ALLOW=` when adding a file with lifecycle-prefix literals and avoid `-k` overlap when adding tests to a partition-enforced file. (b) Self-heal in CI: teach the agentic CI-fixer (`python/ci_agentic_fix.py`) to recognize and fix these two specific failure signatures so they no longer escalate to Main Claude (`first-fixer-non-health`). The cost being reduced is the escalation, not a CI miss.
- **Source**: user

## Decision 3: Fast-lane for #1 only
- **Question**: #1's check is pure `git grep` (sub-second). Promote it to the local fast lane?
- **Resolution**: Yes. Add the legacy-prefix allow-list check to the local fast lane (pre-commit / relevant-checks) so #1 is caught at commit time before push. #2's partition check is `pytest --co`-based (not fast) and stays CI-only.
- **Source**: user

## Decision 4: Ship dirty-tree fix (#3) — review-loop commits first
- **Question**: Where should the fix for uncommitted review-loop fixes live?
- **Resolution**: The review/fix loop commits its working-tree changes before handing control to the ship driver, so ship never sees uncommitted edits. (Exact sequencing locus to be confirmed during plan drafting.)
- **Source**: user

## Hard constraints (established)
- Do NOT run the full CI / heavy `test-harnesses` locally pre-ship. Only really-fast checks may live in the local fast lane. The #2 partition guard (`pytest --co`) must stay CI-only.
- Do NOT weaken the guards' intent: preserve the allow-list's anti-sprawl behavior and the partition guard's strict-partition invariant. The operator explicitly rejected "loosen the guards."
- Preserve the CI-parallelized, fast-surfacing philosophy.

## Non-goals
- Not loosening or auto-tolerating the allow-list / partition guards.
- Not running heavy harnesses locally pre-ship.
- Not changing CI parallelization or shard layout.
