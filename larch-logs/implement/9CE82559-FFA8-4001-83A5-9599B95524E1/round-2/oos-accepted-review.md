### OOS_1: [OUT_OF_SCOPE] Artifact `.tmp` files can also block publishing
- **Reviewer(s)**: dyn-robustness-output.txt
- **Severity**: latent
- **Concern**: Failed moves can leave `panel-manifest.ndjson.tmp` or `round-meta.json.tmp` beside final artifacts, and those unallowlisted files can trip `design-log-publish.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-robustness-output.txt: Same trap/cleanup pattern as above would harden this.


### OOS_2: [OUT_OF_SCOPE] Existing renderer normalization has the same substring-stripping pattern
- **Reviewer(s)**: dyn-data-parsing-output.txt
- **Severity**: nit
- **Concern**: `render-final-summary.sh` already contains the same fragile Gate B substring-stripping normalization; the branch amplifies its impact but did not introduce that pattern.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-data-parsing-output.txt: Address the concern above.


### OOS_3: [OUT_OF_SCOPE] Document security OOS holdback semantics
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: The write-design-round-meta contract does not document security OOS subtraction/holdback semantics or failure modes, making future behavior changes and operator interpretation risky.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Document security holdback semantics and failure modes in write-design-round-meta.md.
  - From cursor-specialist-edge-cases-output.txt: Document security OOS subtraction in the contract doc


### OOS_4: [OUT_OF_SCOPE] No dedicated write-design-round-meta tally parser test exists
- **Reviewer(s)**: dyn-data-parsing-output.txt
- **Severity**: nit
- **Concern**: Tally parsing is only exercised indirectly, so the no-trailing-pipe edge case is unlikely to be caught by CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-data-parsing-output.txt: Address the concern above.


### OOS_5: [OUT_OF_SCOPE] Plan-review slot label mapping is duplicated
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Human-label mapping for plan-review slots is duplicated, making future slot renames prone to divergence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Centralize plan_slot_human_label in one module used by loop, compose, and tests.


