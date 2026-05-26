### [rejected] FINDING_11

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_11: **Item A** (`generate-code-flow-diagram.sh:102`): Portable awk now extracts the token between `REASON_TOKEN=` and the first whitespace, preserving embedded `=` while dropping `fence=` / `line=` metadata. `REASON_TOKEN` values in `sanitize-mermaid-fragment.sh` are fixed literals, not user-derived, so the trust boundary is appropriate. `emit_kv` still has no newline escaping, but that was already true and is not worsened by this diff.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Item A** (`generate-code-flow-diagram.sh:102`): Portable awk now extracts the token between `REASON_TOKEN=` and the first whitespace, preserving embedded `=` while dropping `fence=` / `line=` metadata. `REASON_TOKEN` values in `sanitize-mermaid-fragment.sh` are fixed literals, not user-derived, so the trust boundary is appropriate. `emit_kv` still has no newline escaping, but that was already true and is not worsened by this diff.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_12: **Item B** (`ci-failed-jobs.sh:29-33,86`): `sanitize_diagnostic_line` with `LC_ALL=C tr -d '[:cntrl:]'` plus `printf '%s'` before `larch_err` closes the control-byte / format-string edge on the only untrusted stderr passthrough site. KV emits at 152–153 remain on strict `sanitize_list` and are unchanged.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Item B** (`ci-failed-jobs.sh:29-33,86`): `sanitize_diagnostic_line` with `LC_ALL=C tr -d '[:cntrl:]'` plus `printf '%s'` before `larch_err` closes the control-byte / format-string edge on the only untrusted stderr passthrough site. KV emits at 152–153 remain on strict `sanitize_list` and are unchanged.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_13: **Tests**: T8 and the three Item A harness cases exercise the intended contracts without widening production attack surface.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Tests**: T8 and the three Item A harness cases exercise the intended contracts without widening production attack surface. ---
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_18

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_18: risk-integration: scripts/ci-failed-jobs.sh:85-88
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Under set -euo pipefail a failing printf|sanitize_diagnostic_line pipeline aborts the stderr relay loop before exit 1. Rare tr failure mid-loop yields partial gh stderr relay and a non-guaranteed exit code instead of the documented gh-failure exit 1. Wrap sanitization with set +e or capture rc separately; finish the read loop then exit 1 explicitly.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_24

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_24: correctness: skills/implement/scripts/generate-code-flow-diagram.sh:102
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Implementation uses sub(/[[:space:]].*$/, "") instead of acceptance-specified sub(/ .*$/, ""). Acceptance checklist quotes the space-only awk literally; reviewers auditing checkbox-by-checkbox will flag a mismatch even though behavior matches plan prose for normal space-separated sanitizer lines. Align the second sub with acceptance (sub(/ .*$/, "")) or update the plan acceptance text to authorize [[:space:]].
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

