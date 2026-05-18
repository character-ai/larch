### FINDING_1: panel [code-review/accepted]

## **Nit** `code-quality` `scripts/harness-timer.md:55`: The new sibling contract says Makefile timing changes must update `docs/linting.md`, but the shard rebalancing docs still describe the old manual timing loop in `docs/linting.md:44-81` and do not mention the new `LARCH_HARNESS_TIMING` CI rows. Update that section to use the emitted timing lines, or explicitly document the manual loop as a fallback.

- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Nit** `code-quality` `scripts/harness-timer.md:55`: The new sibling contract says Makefile timing changes must update `docs/linting.md`, but the shard rebalancing docs still describe the old manual timing loop in `docs/linting.md:44-81` and do not mention the new `LARCH_HARNESS_TIMING` CI rows. Update that section to use the emitted timing lines, or explicitly document the manual loop as a fallback.
- **Suggested revision**: Address the concern above.

### FINDING_10: panel [code-review/accepted]

## correctness: scripts/harness-timer.md:32-34

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Doc invariant overclaims coverage for failures vs signals. CI cancel or kill of the recipe shell can skip the timing printf even though the child ran, contradicting partial-run analytics expectations and the written invariant. Narrow wording to normal child return (any exit code) and/or add EXIT/TERM trap with documented partial-duration semantics.
- **Suggested revision**: Address the concern above.

### FINDING_5: panel [code-review/accepted]

## architecture: scripts/harness-timer.md:50-54

- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] New Edit-In-Sync requires concurrent docs/linting.md update on Makefile wiring changes, but Makefile was rewired without updating docs/linting.md “Refreshing harness shard balance.” Maintainers use docs/linting.md for shard rebalancing and never learn about LARCH_HARNESS_TIMING; the new markdown imposes an obligation the PR does not satisfy. Narrow Edit-In-Sync to post-bootstrap changes or extend docs/linting.md with LARCH_HARNESS_TIMING collection notes.
- **Suggested revision**: Address the concern above.

