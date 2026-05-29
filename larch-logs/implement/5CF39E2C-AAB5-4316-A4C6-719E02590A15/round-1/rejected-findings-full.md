### [rejected] FINDING_16

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_16: risk-integration: skills/design/SKILL.md:1120
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] main-agent-vote-required re-tally state refresh is documented only in prose with no regression harness. Stale .step3-plan-review-result.env or wrong findings-classification round could reach Gate B undetected. Add a small offline fixture asserting re-tally refresh keys and classification path when feasible.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_18

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_18: **No new executable surface in production.** `assess-plan-round.sh` / `snapshot-plan-round.sh` are unchanged. Dispatch paths from KV output remain constrained by existing `assessor_path_valid()` (basename + resolved path must live under `$DESIGN_TMPDIR`).
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **No new executable surface in production.** `assess-plan-round.sh` / `snapshot-plan-round.sh` are unchanged. Dispatch paths from KV output remain constrained by existing `assessor_path_valid()` (basename + resolved path must live under `$DESIGN_TMPDIR`).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_19

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_19: **Trust-boundary prose is strengthened, not weakened.** `ballot.txt` stays explicitly untrusted; `main-agent-vote-required` now documents refreshing `.step3-plan-review-result.env` and round-scoped `--findings-classification-out` before Gate B — reducing stale-state / wrong-round classification risk (workflow integrity).
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Trust-boundary prose is strengthened, not weakened.** `ballot.txt` stays explicitly untrusted; `main-agent-vote-required` now documents refreshing `.step3-plan-review-result.env` and round-scoped `--findings-classification-out` before Gate B — reducing stale-state / wrong-round classification risk (workflow integrity).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_20

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_20: **New harness code is test-only.** Case-local `mktemp` dir, heredoc mocks, quoted `"$DIR/..."` writes, `workflow_path` fixed to `HARD` via `printf`. No secrets, injection primitives, or network/auth changes.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **New harness code is test-only.** Case-local `mktemp` dir, heredoc mocks, quoted `"$DIR/..."` writes, `workflow_path` fixed to `HARD` via `printf`. No secrets, injection primitives, or network/auth changes.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_21

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_21: **`LARCH_*` overrides** (`LARCH_DISPATCH_PLAN_ASSESSORS_SH`, etc.) are pre-existing test hooks in `assess-plan-round.sh`; the new case follows the same pattern and runs last before `pass`, so it does not widen production exposure.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **`LARCH_*` overrides** (`LARCH_DISPATCH_PLAN_ASSESSORS_SH`, etc.) are pre-existing test hooks in `assess-plan-round.sh`; the new case follows the same pattern and runs last before `pass`, so it does not widen production exposure.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_25

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_25: architecture: skills/design/SKILL.md:1120
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] main-agent re-tally state refresh is prose-only with no mechanical guard Stale .step3-plan-review-result.env or wrong findings-classification.tsv can still reach Gate B Add offline harness asserting --findings-classification-out and refreshed env before Gate B
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_26

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_26: code-quality: skills/design/scripts/test-assess-plan-round.sh:349-376
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Two-entry case leaves LARCH_* exports pointing at deleted case_tmp after rm -rf Future appended harness cases could call deleted mock paths Save/restore LARCH overrides or run integration before global mock mutation
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: code-quality: skills/design/scripts/test-assess-plan-round.sh:349-376
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Two-entry case deletes case_tmp while LARCH_DISPATCH_* exports still reference it Appending tests after this block could invoke deleted mock paths Run the case in a subshell or restore $TMP mock exports after rm -rf
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_9: correctness: skills/design/scripts/test-assess-plan-round.sh:349-376
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Case-local LARCH_* mock exports left pointing at deleted case_tmp after rm -rf A test appended after the two-entry case would call missing mock scripts unset or restore LARCH_DISPATCH_PLAN_ASSESSORS_SH and LARCH_BREADCRUMB_MONITOR_SH after the case
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

