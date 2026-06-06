### [Plan Review] FINDING_4

### FINDING_4: Item 3 is branch-dependent, not partially done on main
- **Reviewer(s)**: Cursor-dyn-dependency-chain
- **Severity**: important
- **Concern**: The plan marks Item 3 as partially done on main, but the helper needed for literal-redacted escaped framing exists only on the dependent branch; main still emits raw tags.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-dependency-chain: Reclassify item 3 as branch-dependent; state framing prose applies only after #3548 lands (or list porting emit_untrusted_file_block as prerequisite)


### [Plan Review] FINDING_5

### FINDING_5: Item 5 tests depend on branch-only redact/escape behavior
- **Reviewer(s)**: Cursor-dyn-dependency-chain
- **Severity**: important
- **Concern**: The plan treats Item 5 as code-complete with tests remaining, but main still cats context files raw; tests would require the dependent branch’s redact/escape pipeline.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-dependency-chain: Reclassify item 5 as branch-dependent test coverage; note main would need the #3548 redact/escape pipeline before tests can pass


### [Plan Review] FINDING_6

### FINDING_6: Item 2 re-tally edit assumes branch-only scope-anchor choreography
- **Reviewer(s)**: Cursor-dyn-dependency-chain
- **Severity**: important
- **Concern**: The SKILL.md re-tally edit assumes `SCOPE_ANCHOR_FILE` materialization and renderer plumbing that is not present on main, so applying it early would add orphaned prose.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-dependency-chain: Applying item 2 to main would add orphaned scope-anchor KV/re-tally prose with no materialization or renderer; keep hard gate on #3548 merge before item 2


### [Plan Review] FINDING_11

### FINDING_11: SCOPE_ANCHOR_FILE emission matrix omits --help/no-KV terminal path
- **Reviewer(s)**: Cursor-dyn-kv-propagation
- **Severity**: latent
- **Concern**: The planned docs cover ok, main-agent-vote-required, and tally-error behavior, but omit that `--help` emits no KVs at all.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-kv-propagation: When updating tally-plan-review.md note SCOPE_ANCHOR_FILE is absent on --help and all tally-error paths including EXIT trap pre-success failures

