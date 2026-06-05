### [rejected] FINDING_16

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_16: risk-integration: skills/design/scripts/test-design-postplan-emit.sh:9594-9844
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] No --with-plan-size test for check-plan-size rc 3 rc3 argv-error path untested though handled like rc2 Add stub exit 3 harness case
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_20

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_20: security: skills/design/scripts/design-postplan-emit.sh:113-169
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Classification stderr is stored and displayed with only control-char sanitization not secret/path redaction. Future or verbose classification stderr could expose tmpdir paths or accidental secrets in chat and result env WARN= lines. Redact classification stderr before WARN_LINES; document in design-postplan-emit.md.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_24

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_24: risk-integration: skills/design/SKILL.md:889-936
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Thin-fence case arms 10/12/13 do not exit; behavior depends on prose after esac. Orchestrator halt or mis-read after Bash could skip validator failure or Split prompts and advance toward Step 3 incorrectly. Add explicit non-proceed guards in rc 10/12/13 arms or strengthen structure pins for mandatory post-esac handlers.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_25

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_25: correctness: skills/design/SKILL.md:916-923
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] rc 12/13 write only step-2b before Split; step-2b.5 deferred to non-exiting returns. Cancel or pause after hard/partition entry without Refine/Continue may leave step-2b.5 unset and confuse resume. Document or adjust sentinel writes on hard/partition entry vs cancel/pause paths.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_26

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_26: code-quality: skills/design/SKILL.md:874
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Stale text says continue after Step 2b.5 while merged path folds 2b.5 into the driver. Minor orchestrator confusion on clean path only. Reword to refer to merged post-plan driver settlement and retained 2b.5 callers.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: code-quality: skills/design/scripts/design-postplan-emit.sh:378-403
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Nonfatal check-plan-size rc2/rc3 warning/logging block duplicated in plan-review-loop.sh Future edits to log paths site labels or append suppression may update one caller and not the other Extract shared helper for warn-and-continue plan-size failures
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: architecture: skills/design/references/approval-gates.md:157-158
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Merged postplan rc dispatch delegated to SKILL Step 2b prose only; no executable fence in reference files Orchestrator copying three sites can drift on rc 10/12/13 sentinel or site-specific prompt handling Centralize rc-dispatch snippet or add scoped bash fences to references
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

