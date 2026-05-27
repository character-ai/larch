### [Plan Review] FINDING_11

### FINDING_11: Coder validation bypasses external-tool registry
- **Reviewer(s)**: Cursor-Innovation, Codex-Innovation
- **Severity**: latent
- **Concern**: The new bootstrap `--coder` validation hardcodes the coder enum instead of using the canonical external-tool registry.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation, Codex-Innovation: Source scripts/external-tool-registry.sh in implement-bootstrap.sh and validate with larch_is_implementer_coder / larch_implementer_coders_braced; extend test-external-tool-registry.sh coverage to include bootstrap


### [Plan Review] FINDING_15

### FINDING_15: Gate C decision conflict is not machine-enforced
- **Reviewer(s)**: Cursor-dyn-decision-conflict, Codex-dyn-decision-conflict
- **Severity**: important
- **Concern**: The plan leaves the #2756 reversal as advisory Gate C prose rather than a machine-enforced decision or blocking preflight criterion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-decision-conflict, Codex-dyn-decision-conflict: Resolve the conflict before finalizing: replace the Open questions section with an explicit recorded decision outcome, or add a concrete Preflight refusal criterion/clarify marker that blocks implementation while unresolved wording remains


### [Plan Review] FINDING_18

### FINDING_18: Foreground marker comment does not satisfy Family B marker rules
- **Reviewer(s)**: Codex-dyn-deletion-completeness
- **Severity**: important
- **Concern**: The proposed Step 0 foreground comment is outside the Family B fence marker contract and would not be validated as satisfying BASH_AUTHORING.md §4 for denylisted background-monitor pairs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-deletion-completeness: Do not present the Step 0 foreground comment as satisfying BASH_AUTHORING.md §4. Keep it as a local style pin only, or remove the pin. For any denylisted Family B invocation, require the exact background banner and # Background pair required: see BASH_AUTHORING.md §4 comment.


