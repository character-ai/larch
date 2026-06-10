# Review Round 3

- Mode: `diff`
- 5 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: CLI snippets invoke `python/cli.py` incorrectly
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: SKILL snippets invoke `python/cli.py` directly instead of via `python3`; `/design` Step 3b and `/research` validation can fail because `cli.py` is not executable, and one command quotes subcommand words into the path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.


### FINDING_2: Renderer-retargeted tests do not inspect the intended source
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Retargeted shell tests inspect nonexistent, tokenized, or wrong paths instead of `python/rendering.py`, allowing renderer prompt-prose and cache-key regressions to pass without actually scanning the migrated source.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt, codex-specialist-testing-output.txt: Address the concern above.


### FINDING_4: `render lane-status` emits KVs without quiet initialization
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `render lane-status` uses `logging_util.emit_kv` without initializing quiet mode, so inherited quiet sessions can route KVs to the parent fd 3 instead of captured subprocess output, leaving `/research` Step 3 with empty lane attribution.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt: Address the concern above.


### FINDING_5: Render cache setup failures abort prompt rendering
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Specialist render cache setup failures, such as an unwritable `LARCH_RENDER_CACHE_DIR`, can abort rendering instead of falling back to uncached rendering, preventing external reviewers from launching.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_7: Pytest replacement misses migrated renderer/generator harness coverage
- **Reviewer(s)**: codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The planned pytest replacement for deleted renderer/generator harnesses is largely missing, leaving contracts for flags, exit codes, quiet routing, generator byte identity, debate retry, voter/plan-review anchors, and Mermaid fixtures vulnerable to regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing-output.txt: Address the concern above.


