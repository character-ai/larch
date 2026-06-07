### FINDING_18: [OUT_OF_SCOPE] Python 3.11 floor changes are incidental scope creep
- **Reviewer(s)**: dyn-design-flow-output.txt, dyn-runtime-compat-output.txt
- **Severity**: latent
- **Concern**: The branch bundles Python 3.11 floor alignment with unrelated `/design` Gate B work, increasing review and rollback surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-design-flow-output.txt, dyn-runtime-compat-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_19: [OUT_OF_SCOPE] Assessor skip behavior is pre-existing or specified
- **Reviewer(s)**: dyn-design-flow-output.txt, dyn-runtime-compat-output.txt
- **Severity**: latent
- **Concern**: Some assessor-skip behavior predates the branch or is explicitly specified for SIMPLE until later work, though default auto-apply amplifies its impact.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-design-flow-output.txt, dyn-runtime-compat-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_23: [OUT_OF_SCOPE] Validator repo-root behavior is pre-existing
- **Reviewer(s)**: dyn-autofix-launch-output.txt
- **Severity**: nit
- **Concern**: Initial validation and auto-fix both use the plugin root rather than a consumer repo root for Tier-3 resolution; this is unchanged by the branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-autofix-launch-output.txt: Address the concern above.


Vote tally: YES=1 NO=2 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_24: [OUT_OF_SCOPE] Reduced Gate B chat visibility is intentional
- **Reviewer(s)**: dyn-autofix-launch-output.txt
- **Severity**: nit
- **Concern**: Default auto-apply intentionally removes Gate B chat visibility, and logging auto-fix outcomes only through warnings matches the stated acceptance criteria.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-autofix-launch-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_26: [OUT_OF_SCOPE] Python 3.12 reference mismatch appears resolved
- **Reviewer(s)**: dyn-runtime-compat-output.txt
- **Severity**: nit
- **Concern**: Runtime docs, CI, and config no longer appear to retain Python 3.12 references outside `larch-logs/` artifacts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-runtime-compat-output.txt: Address the concern above.

Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_6: [OUT_OF_SCOPE] Revert failure can leave operator-visible rollback semantics incorrect
- **Reviewer(s)**: cursor-specialist-security-output.txt, codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Revert failure handling can continue after rollback fails or partially succeeds, leaving operators believing rollback occurred while the applied or partially restored plan state remains active.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_7: [OUT_OF_SCOPE] Auto-fix dispatch override env vars are too permissive
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `LARCH_AUTOFIX_*` environment variables allow full dispatch override, so a compromised local shell environment could redirect auto-fix to attacker-controlled scripts outside test contexts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated

