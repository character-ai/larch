# test-implement-structure.sh contract

Structural regression harness for `/implement` after the larch-log migration.

It pins the core top-level headings, required reference files, the new
`larch-log.sh` and `tracking-issue-summary.sh` surfaces, and rejects references
to removed anchor infrastructure.

It also pins the finalize-state teardown contract: the SKILL.md NEVER bullet
for prompt-side writes, Step 18's restore-before-teardown invocation order, the
`restore-finalize-state.sh` executable plus sibling docs, and the shared
`lib-finalize-state-keys.sh` library plus source references from restore and
ship-pr.
