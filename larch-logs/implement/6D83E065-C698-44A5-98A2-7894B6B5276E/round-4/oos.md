### FINDING_10: [OUT_OF_SCOPE] Manifest security routing can be spoofed, injected, or miss sensitive items
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-oos-flow-output.txt, dyn-redaction-boundary-output.txt
- **Severity**: important
- **Concern**: `materialize-manifest-oos.sh` security routing relies on inconsistent text/markdown heuristics around `focus_area` and description bodies. A malformed or adversarial manifest can privately route non-security items, misclassify via newline injection, or send unmarked security narratives to the public OOS path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From dyn-oos-flow-output.txt: Address the concern above.
  - From dyn-redaction-boundary-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_12: [OUT_OF_SCOPE] Security OOS sidecar handling is inconsistent or underdocumented
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-redaction-boundary-output.txt
- **Severity**: important
- **Concern**: `security-oos-observations.md` blocking/remediation is implemented across ship/checkpoint/Python paths but not fully documented in the OOS pipeline, not enforced inside Python `_oos_gate`, and has fork/checkpoint semantics that can diverge from `ship-pr`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-redaction-boundary-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_13: [OUT_OF_SCOPE] Python ship re-handoffs after completed OOS disposition on accepted markdown
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-oos-flow-output.txt, dyn-python-ship-output.txt
- **Severity**: important
- **Concern**: `python/ship.py` returns `NEEDS_USER_OOS_FILING` on any non-empty accepted-OOS markdown before consulting `_oos_gate` disposition evidence. Post-Step 9a.1 reinvocation can therefore loop instead of reaching `ensure_pr`, and security-only accepted content can be treated as needing public filing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From dyn-oos-flow-output.txt: Address the concern above.
  - From dyn-python-ship-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_3: [OUT_OF_SCOPE] Python design-OOS tests are misnamed or too weak for their asserted behavior
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-python-ship-output.txt, dyn-contract-sync-output.txt
- **Severity**: important
- **Concern**: Several `python/test_ship.py` names imply PR creation after disposition, but the assertions expect `NEEDS_USER_INPUT` / first-pass blocking. Weak or misleading assertions could invite future “fixes” that break design-export OOS blocking coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-python-ship-output.txt: Address the concern above.
  - From dyn-contract-sync-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_4: [OUT_OF_SCOPE] OOS public sanitization/redaction is inconsistent and not mechanically enforced end-to-end
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt, dyn-redaction-boundary-output.txt
- **Severity**: important
- **Concern**: Redaction is duplicated between materialization and prompt-side OOS filing/logging, while later Step 9a.1 outputs rely on orchestrator discipline rather than a shared helper. Public OOS issues, NDJSON, logs, or raw manifests can retain PII, internal URLs, or novel secret formats.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From dyn-redaction-boundary-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_8: [OUT_OF_SCOPE] Non-security OOS counting is duplicated in checkpoint/gate scripts
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Existing duplicate non-security counting logic between the checkpoint and gate awk means security predicate changes require multiple coordinated edits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### FINDING_9: [OUT_OF_SCOPE] Bash `pr-create` resume re-arms `OOS_PENDING` from non-empty accepted files
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-oos-flow-output.txt, dyn-python-ship-output.txt, dyn-contract-sync-output.txt
- **Severity**: important
- **Concern**: Resuming with `--resume-phase pr-create` routes through `pr-prep`, which sets `OOS_PENDING=true` on any non-empty accepted-OOS markdown before honoring completed disposition evidence. After Step 9a.1 clears `OOS_PENDING`, the run can loop forever instead of opening the PR.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-oos-flow-output.txt: Address the concern above.
  - From dyn-python-ship-output.txt: Address the concern above.
  - From dyn-contract-sync-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

