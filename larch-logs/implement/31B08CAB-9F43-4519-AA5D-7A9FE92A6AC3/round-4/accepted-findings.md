### FINDING_16: Fixture inventory doc disagrees with harness case numbering/count
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: [scripts/test-lint-foreground-markers.md](scripts/test-lint-foreground-markers.md) (74–99) vs [scripts/test-lint-foreground-markers.sh](scripts/test-lint-foreground-markers.sh): sibling doc inventory does not match implemented scenarios, confusing triage after failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_17: `.pre-commit-config.yaml` header contradicts `make lint-only` vs `make lint` story
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [.pre-commit-config.yaml](.pre-commit-config.yaml) top-of-file comment still implies CI runs `make lint` while docs/plan call for reconciling to `make lint-only` for the CI job and local extras as appropriate (plan OOS_4 / reconciliation task).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_4: Strict fence-opener regex may skip valid fences
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: [scripts/lint-foreground-markers.sh](scripts/lint-foreground-markers.sh) (around 301–302) uses a strict trailing-token regex on the fence line so some Family B fence shapes are never scanned, yielding false green CI vs acceptance intent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


### FINDING_7: Plain-URL OOS recovery pairs sentinels to blocks by document order, not id
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: [skills/design/scripts/file-design-oos.sh](skills/design/scripts/file-design-oos.sh) (7095–7177 per input): recovery pairs plain URLs to the first unfiled OOS blocks in order without OOS id matching, so filing two issues in reverse order can swap **Filed URL** lines while still exiting 0; need `OOS_FILE_MAP` whenever multiple URLs/blocks or match URLs to OOS ids.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


