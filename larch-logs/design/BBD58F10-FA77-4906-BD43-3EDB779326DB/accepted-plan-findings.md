### FINDING_1: New pin-check scripts may be reported unreachable
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Concern**: The plan adds `scripts/check-contains-pins.sh` and its harness/docs without updating `agent-lint.toml`, so `agent-lint --pedantic` can classify the new helper or harness as dead/orphaned after landing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add agent-lint.toml entries for scripts/check-contains-pins.sh, scripts/check-contains-pins.md, scripts/test-check-contains-pins.sh, and scripts/test-check-contains-pins.md near the existing relevant-checks helper block, with the same Makefile/script-helper rationale


### FINDING_2: Makefile aggregate would violate shard partition invariant
- **Reviewer(s)**: Cursor-Edge, Codex-Edge, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Concern**: The plan adds `test-check-contains-pins` directly to the `test-harnesses` aggregate while also adding it to a shard, but the aggregate is expected to list only `test-harnesses-N` shard targets. This can fail the shard coverage guard and may run the harness twice.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge, Codex-Edge: Leave test-harnesses line unchanged; add the new harness only to .PHONY, one shard line, and its recipe
  - From Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic: Revise the Makefile step to add test-check-contains-pins only to .PHONY, exactly one shard such as test-harnesses-3, and its recipe; leave the test-harnesses aggregate line unchanged
  - From Cursor-Requirements, Codex-Requirements: Do not add the individual harness to Makefile:47; add it only to .PHONY, its recipe, and exactly one test-harnesses-N shard


### FINDING_3: Relevant-checks pin verifier can silently skip
- **Reviewer(s)**: Cursor-Edge, Codex-Edge, Cursor-dyn-grammar-coverage, Codex-dyn-grammar-coverage
- **Severity**: important
- **Concern**: The proposed `relevant-checks.sh` phase is guarded by executable-bit checks even though the plan invokes the helper with `bash` elsewhere and does not require the new script to be executable. A non-executable file could pass the Make harness while disabling the relevant-checks backstop.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge, Codex-Edge: Invoke the helper unconditionally or under -f/readability, and fail if it is missing; only keep -x if the plan also requires and tests the executable bit
  - From Cursor-dyn-grammar-coverage, Codex-dyn-grammar-coverage: Use a file/readability guard before invoking with bash, or add an explicit chmod/executable-mode step plus a test-relevant-checks assertion that fails when the phase is skipped


### FINDING_4: Pin grammar misses existing double-quoted literals
- **Reviewer(s)**: Cursor-dyn-grammar-coverage, Codex-dyn-grammar-coverage
- **Severity**: important
- **Concern**: The plan only covers the single-quoted `contains "$VAR" 'LITERAL' 'label'` grammar, but existing first-argument target pins include static double-quoted literals for high-value design files. Those pins could be skipped as non-canonical and leave intended coverage unenforced.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-grammar-coverage, Codex-dyn-grammar-coverage: Either convert these existing contains calls to single-quoted literals in the plan, or explicitly support static double-quoted no-substitution contains literals in v1 and cover them in scripts/test-check-contains-pins.sh


### FINDING_5: Shard selection relies on inaccurate balance premise
- **Reviewer(s)**: Cursor-dyn-makefile-shard-audit, Codex-dyn-makefile-shard-audit
- **Severity**: latent
- **Concern**: The plan assigns the new harness to `test-harnesses-3` based on an inaccurate “lightest shard” premise. Current Makefile comments indicate shards 1-4 isolate slow harnesses, and shard 3 currently contains `test-dispatch-code-voters-happy`, so choosing it by target count may worsen sharding rather than preserve the intended balance.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-makefile-shard-audit, Codex-dyn-makefile-shard-audit: Revise the Makefile step to avoid test-harnesses-3 as a count-based "lightest" target; choose a non-isolated shard using the current sharding contract or measured timing, then keep the minimal edits to .PHONY, the aggregate coverage, and exactly one shard line.

