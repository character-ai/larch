### [Plan Review] FINDING_11

### FINDING_11: Generated implementer regeneration step is omitted
- **Reviewer(s)**: Cursor-dyn-generator-contract
- **Severity**: important
- **Concern**: The plan edits the base implementer prompt surface but does not explicitly require regenerating and committing the generated Codex/Cursor implementer files, risking CI failure or stale shipped prompts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-generator-contract: Implementer edits _implementer-base.md only; CI fails --check until someone remembers generators Add bullet: run bash scripts/generate-codex-implementer.sh and generate-cursor-implementer.sh; commit both agents/*.md


### [Plan Review] FINDING_14

### FINDING_14: Manifest-validation anchor verification is supporting evidence only
- **Reviewer(s)**: Cursor-dyn-line-anchor-verification
- **Severity**: nit
- **Concern**: The reviewer reports that the five manifest-validation anchors are verified and that this is supporting verification, not a defect; the only actionable caveat is covered by the separate corrupt resume-counter finding.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-line-anchor-verification: No plan change required for anchor list; implementer should still exclude 357 per row above### OOS_1:
- **Description**: —. Scenario: Plan does not update linting harness table for M1-M5 or grep regressions
- **Reviewer**: Cursor-dyn-generator-contract
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: docs/linting.md
- **Phase**: design


### [Plan Review] FINDING_6

### FINDING_6: Manifest template drift checks are too weak
- **Reviewer(s)**: Codex-Arch, Codex-Innovation, Codex-dyn-sync-surface-adequacy
- **Severity**: important
- **Concern**: The duplicated inline manifest template is guarded only by substring/presence checks, which can miss field-level drift from the canonical schema while tests still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add a stronger sync check that extracts the inline JSON/template and required-fields table and compares the field set/status requirements against codex-manifest-schema.md or generate the inline block from the schema reference
  - From Codex-Innovation: Generate the inline template from the canonical schema or add a sync test that compares required keys, field names, and status-specific requirements between the schema reference and agents/_implementer-base.md
  - From Codex-dyn-sync-surface-adequacy: Replace the string-presence check with a structural fixture check that extracts the Manifest JSON template and asserts required field names/paths, or compare it against a canonical fixture derived from codex-manifest-schema.md


