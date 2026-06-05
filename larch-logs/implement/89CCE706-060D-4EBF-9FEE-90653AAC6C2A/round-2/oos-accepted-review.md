### FINDING_10: [OUT_OF_SCOPE] Scout harness does not pin prompt ban on folded static slugs
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The scout prompt forbids dynamic resurrection of folded `structure` and `plan-fidelity` slugs, but the harness does not assert that prose. Prompt drift could re-enable those folded slugs without immediate test failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=1 Result=exonerated


### FINDING_12: [OUT_OF_SCOPE] Stale static-focus mappings still mention folded archetypes
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-waterfall-routing-output.txt
- **Severity**: nit
- **Concern**: `tally-code-votes.sh` still maps `structure` and `plan-fidelity` even though those static panel slots are no longer dispatched. This is harmless for runtime/legacy manifests but can confuse maintainers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-waterfall-routing-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=1 Result=exonerated


### FINDING_15: [OUT_OF_SCOPE] Legacy folded specialist agents remain discoverable in-tree
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `agents/reviewer-structure.md` and `agents/reviewer-plan-fidelity.md` remain in the repository even though they are no longer active static panel slots. Operators browsing `agents/` may think they are still dispatched.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=1 Result=exonerated


### FINDING_17: [OUT_OF_SCOPE] Pre-existing description text quoting can break prompt structure
- **Reviewer(s)**: dyn-prompt-context-output.txt
- **Severity**: nit
- **Concern**: `render-specialist-prompt.sh` embeds `DESCRIPTION_TEXT` inside single quotes in an unquoted heredoc. A description containing a quote can break prompt structure. The reviewer marked this pre-existing, though the branch increases nearby plan/feature exposure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-prompt-context-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=1 Result=exonerated


### FINDING_18: [OUT_OF_SCOPE] Pre-existing issue/plan materialization lacks redaction
- **Reviewer(s)**: dyn-prompt-context-output.txt
- **Severity**: latent
- **Concern**: `implement-bootstrap.sh` copies issue-derived plan and feature-description content into session files without redaction. Codex re-enable increases exposure, but the underlying trust model predates this branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-prompt-context-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=1 Result=exonerated


### FINDING_19: [OUT_OF_SCOPE] Render-specialist prompt harness lacks broader negative assertions
- **Reviewer(s)**: dyn-prompt-context-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-render-specialist-prompt.sh` asserts plan injection for `reviewer-testing`, but does not broadly assert absence of plan injection for other agents in all narrowed modes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-prompt-context-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=1 Result=exonerated


### FINDING_23: [OUT_OF_SCOPE] Larch-log harness docs still list only Cursor static denied files
- **Reviewer(s)**: dyn-artifact-policy-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-larch-log.md` contract prose still lists only `cursor-specialist-*-output.txt` as denied write-round files, despite Codex static deny behavior being added elsewhere.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-artifact-policy-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=1 Result=exonerated


### FINDING_24: [OUT_OF_SCOPE] Timing kind enum still includes folded Codex specialist slugs
- **Reviewer(s)**: dyn-artifact-policy-output.txt
- **Severity**: nit
- **Concern**: `scripts/lib-timing-kinds.sh` still lists `codex-specialist-structure` and `codex-specialist-plan-fidelity` even though those archetypes are no longer dispatched. This may misattribute timing after the four-archetype collapse.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-artifact-policy-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=1 Result=exonerated


### FINDING_26: [OUT_OF_SCOPE] Tally docs use folded `structure` as representative static slug
- **Reviewer(s)**: dyn-sync-surfaces-output.txt
- **Severity**: nit
- **Concern**: `skills/review/scripts/tally-code-votes.md` uses `structure` as a representative static slug even though the live panel no longer dispatches that archetype.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-sync-surfaces-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=1 Result=exonerated


