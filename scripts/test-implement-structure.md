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

It pins `write-final-report.sh --print-stdout` to Step **17** only; Step **18**
must call `write-final-report.sh` **without** `--print-stdout` (silent refresh).

Two assertions added for the orchestrator narrow-protocol-bounds rule (issue #2286):
`SKILL.md Exit 4 prose must direct orchestrator to 'Continue to Step 16'` (pins that
the documented recovery directive is present) and `ship-pr.sh must emit DO NOT improvise
diagnostic on STALL_STEP=12d exit 4 path` (guards against accidental removal of the
diagnostic message).
