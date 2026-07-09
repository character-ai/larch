### [rejected] FINDING_4

**Rejected subtype:** dismissed (0 YES)

### FINDING_4: occurrence index is unstable across unrelated setattr calls
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: major
- **Concern**: The baseline key counts every resolved repo-module `setattr` in scope, so inserting or reordering unrelated patches shifts occurrence numbers and makes the ratchet keys unstable.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: `Count only emitted findings or use lineno-only identity; remove occurrence from the baseline key if it stays order-sensitive.`


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** dismissed (0 YES)

### FINDING_5: diagnostic text does not branch for consumer targets
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: The diagnostic message still talks about patching the defining or consuming module even when `M` is already the consumer, which can mislead authors applying the consumer-side fix.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: `Branch message on whether M is a facade vs direct consumer; do not use the facade wording for consumer targets.`


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** dismissed (0 YES)

### FINDING_7: resolver misses imported external bindings in attribute chains
- **Reviewer(s)**: codex-specialist-edge-cases
- **Severity**: major
- **Concern**: The chain resolver only follows repo submodules, so imported bindings that are not repo modules are skipped even when the parent module does bind them.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: `Resolve attribute chains and dotted strings against imported names in the current module, not just repo submodules, and stop when the next hop is an imported external binding.`


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_8: facade imports later defined at module scope lack coverage
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: There is no coverage for the case where a facade imports a name and later defines it at module scope, so a classifier regression could false-flag valid patches.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: `Add parametrized fixtures with import-then-def/class/assign/annassign for the same attribute and assert scan_file returns [].`


Vote tally: YES=1 NO=2 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_9: from-import-as aliases and duplicate occurrence indexing lack coverage
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: The aliasing and occurrence-number edge cases are untested, so baseline identity could drift if duplicate setattr calls or `as` bindings are handled incorrectly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: `Add tests for from-import-as facade bindings and for two identical setattr calls in one function asserting occurrence 1 and 2.`


Vote tally: YES=1 NO=2 JUDGE_ERROR=0

