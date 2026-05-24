### [Plan Review] FINDING_19

### FINDING_19: Optional timing-ledger hook for Step 2b.5
- **Reviewers**: Cursor-Innovation (1 reviewer)
- **Concern**: Other `/design` sub-steps emit `LARCH_TIMING_SKILL=design timing-ledger.sh mark "design Step <N> — <name>"` so timing diagnostics are uniform. Omitting a `2b.5` mark hides latency for the new threshold check.
- **Proposed resolution**: Optional/latent — add `timing-ledger.sh mark "design Step 2b.5 — plan size"` at the start of the Step 2b.5 sub-step. Add `2b.5  plan size` to the step-name-registry.tsv (this overlaps with FINDING_1's registry change).


