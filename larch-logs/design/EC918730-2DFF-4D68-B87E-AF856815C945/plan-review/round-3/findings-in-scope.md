### FINDING_1: Remove ghost test doc reference from log plan
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: nit
- **Concern**: The plan still references `scripts/test-lib-design-round-artifacts.md`, which does not exist, risking implementers treating a missing-file search/update as required.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Reword the `scripts/larch-log.md` bullet to name only existing companions (`scripts/lib-design-round-artifacts.md`, `scripts/test-lib-design-round-artifacts.sh`); keep `scripts/test-larch-log-write-round.md` unconditional per FINDING_3

### FINDING_2: Keep design artifact allowlist changes out of this SIMPLE PR
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: The plan expands into design plan-review artifact allowlist behavior that is not required for the implement-log Dynamic Codex inclusion contract, increasing scope beyond the stated issue.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Remove the design artifact updates from this plan and handle that producer-name correction in a separate focused issue/PR unless it is proven necessary for the Dynamic Codex implement-log fix.

### FINDING_3: Add raw static Codex transcript exclusion coverage
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: Existing planned static Codex exclusion assertions cover only the unphased static Codex `.meta` sidecar, not the raw `codex-specialist-*-output.txt` transcript named in the feature description, leaving the static-vs-dynamic boundary under-tested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add a raw codex-specialist-security-output.txt fixture and assert it is excluded alongside the dynamic Codex inclusion assertions.

### FINDING_4: Do not encode fictional phased Dynamic Codex events fixture
- **Reviewer(s)**: Codex-dyn-fixture-producer-name
- **Severity**: important
- **Concern**: The planned `dyn-api-contract-codex-output-phase2.txt.events.jsonl` fixture does not match real producer behavior because Dynamic Codex slots use unphased `dyn-<name>-codex-output.txt`, while phase2 `other_tool codex` represents Cursor, so the regression suite would encode an artifact contract that real runs do not produce.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-fixture-producer-name: Drop the `dyn-api-contract-codex-output-phase2.txt.events.jsonl` fixture/assertion; keep the real unphased Codex `.events.jsonl` negative coverage.
