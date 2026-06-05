### [rejected] FINDING_11

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_11: Gate B delegates thin-fence arms without embedded fence
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Gate B merged post-apply (`approval-gates.md` ~158) delegates thin-fence `case` arms to `SKILL.md` instead of embedding a fence. An orchestrator following only `approval-gates.md` may omit mandatory case arms or echo discipline even when Step 2b’s fence is correct.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Duplicate minimal fence skeleton in reference or pin delegation completeness in structure test.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_13: Manifest author can stall PR via security OOS sidecar
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Manifest author can mark observations as security to fill `security-oos-observations.md` (`materialize-manifest-oos.sh` ~127–133). `ship-pr.sh` blocks PR creation while that sidecar is non-empty, letting an external implementer stall shipping without completing private disclosure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Document recovery; consider gating block on operator acknowledgment or tightening security_signal false-positive rules.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_14: Plan-size validation log written before redaction
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: Plan-size rc2/3 writes combined stdout+stderr to `check-plan-size.validation.log` before redacted append (`design-postplan-emit.sh` ~313–357). Failed check output may leave secrets or internal URLs in the session tmpdir until cleanup.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Redact the combined capture before writing the validation log file.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_15

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_15: Plan-size checker rc2/3 nonfatal continues as under-threshold
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Plan-size checker rc2/3 is nonfatal and continues as under-threshold (`design-postplan-emit.sh` ~376–384). Misconfigured checker allows oversized plans into full review, increasing cost and DoS surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Keep as monitored degradation or fail closed on HARD tier unless operator overrides.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

