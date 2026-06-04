### FINDING_11: [OUT_OF_SCOPE] Python OOS tests encode or obscure the wrong post-disposition behavior
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-oos-flow-output.txt, dyn-python-parity-output.txt
- **Severity**: important
- **Concern**: Tests named as if PR creation is allowed after disposition assert `NEEDS_USER_INPUT` instead, and related design-export tests do not verify resolved accepted-file paths. This bakes in or obscures the post-Step-9a.1 resume regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-oos-flow-output.txt, dyn-python-parity-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_17: [OUT_OF_SCOPE] Description-body `focus-area` scanning can mis-route manifest OOS
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-oos-flow-output.txt, dyn-shell-state-output.txt
- **Severity**: latent
- **Concern**: `security_signal` scans description text for focus-area-shaped lines, so quoted or narrative `- **focus-area**: security` text can route otherwise non-security observations to the private sidecar and stall shipping.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, dyn-oos-flow-output.txt, dyn-shell-state-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_21: [OUT_OF_SCOPE] SECURITY.md does not clearly cross-link manifest routing asymmetry
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: SECURITY.md and manifest OOS use different security discrimination rules, which can mislead operators unless the asymmetry and manifest predicate are explicitly cross-linked.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_22: [OUT_OF_SCOPE] Checkpoint ndjson requirement may reject inline-triage-only coverage
- **Reviewer(s)**: dyn-oos-flow-output.txt
- **Severity**: latent
- **Concern**: Requiring `oos-issues.ndjson` whenever non-security accepted OOS exists can prevent checkpoint success for inline-triage-only coverage if accepted markdown remains without ndjson.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-oos-flow-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_23: [OUT_OF_SCOPE] Count-only materializer failure can stall zero-OOS manifests
- **Reviewer(s)**: dyn-shell-state-output.txt
- **Severity**: latent
- **Concern**: If count-only materialization fails on a manifest with zero OOS observations, the failure branch still sets `OOS_PENDING=true`, conservatively stalling shipping for infrastructure or schema errors unrelated to actual OOS.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-state-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_24: [OUT_OF_SCOPE] Python `_oos_gate` remains architecturally behind checkpoint parity
- **Reviewer(s)**: dyn-shell-state-output.txt
- **Severity**: latent
- **Concern**: Beyond the direct PR-create path, `_oos_gate` does not fully apply checkpoint preconditions such as ndjson validation or security sidecar blocking for future direct callers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-state-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_25: [OUT_OF_SCOPE] Python ship driver lacks phase-aware resume support
- **Reviewer(s)**: dyn-python-parity-output.txt
- **Severity**: latent
- **Concern**: Python has no `--resume-phase` or phase-aware entry point, so every invocation reruns the full sequence rather than matching bash resume semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-python-parity-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_26: [OUT_OF_SCOPE] Security sidecar redaction branch lacks direct tests
- **Reviewer(s)**: dyn-public-redaction-output.txt
- **Severity**: latent
- **Concern**: Redaction tests cover public accepted-OOS output but not `security-oos-observations.md`, even though the security-routed branch also passes through sanitization.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-public-redaction-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_27: [OUT_OF_SCOPE] Step 9a.1 combine and issue redaction remain prompt-level
- **Reviewer(s)**: dyn-public-redaction-output.txt
- **Severity**: latent
- **Concern**: Combine, `/issue`, and larch-log redaction still depend on orchestrator prompt instructions rather than a mechanical enforcement hook beyond the new materializer.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-public-redaction-output.txt: Address the concern above.

Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

