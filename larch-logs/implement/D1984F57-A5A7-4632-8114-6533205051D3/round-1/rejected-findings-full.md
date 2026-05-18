### [rejected] FINDING_13

### FINDING_13: code-quality: scripts/ship-pr.sh:230-240,.claude/skills/bump-version/scripts/apply-bump.sh:41-51
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Duplicate semver_lt implementations across two scripts. Two places to fix if semver rules ever change. Optional shared sourced helper under scripts/ if coupling is acceptable.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0

### [rejected] FINDING_14

### FINDING_14: code-quality: scripts/test-apply-bump.sh:103-106,312-396
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Sub-test H uses hardcoded 2.0.0 via invoke_apply instead of plan-specified 2.9.9 vs 3.0.0. No functional gap today; plan intent for illustrative versions not matched. Parameterize new version for the harness case so H uses 2.9.9 as in the plan.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0

### [rejected] FINDING_16

### FINDING_16: correctness: scripts/ship-pr.sh:1199-1216
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] new_version not regex-validated before semver_lt in run_rebase_rebump If classify output or parsing ever produced a non-canonical NEW_VERSION, semver_lt could mis-compare or exit under set -e. Validate new_version with the same strict X.Y.Z pattern as _origin_ver before semver_lt.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0

### [rejected] FINDING_17

### FINDING_17: correctness: scripts/ship-pr.sh:1202-1205
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] new_version from classify-bump is not strict-semver validated before semver_lt while _origin_ver is. Malformed or unexpected NEW_VERSION could make semver_lt numeric compares unreliable. Guard new_version with the same ^[0-9]+.[0-9]+.[0-9]+$ regex before semver_lt.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0

### [rejected] FINDING_18

### FINDING_18: correctness: scripts/test-apply-bump.sh:103-107 scripts/test-apply-bump.sh:310-319
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Sub-test H uses default --new-version 2.0.0 instead of plan-specified 2.9.9. Plan fidelity: literal test inputs differ though regression (less-than origin) is still covered. Add invoke path with --new-version 2.9.9 (or parameterize invoke_apply) and align assertions with plan.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0

### [rejected] FINDING_23

### FINDING_23: risk-integration: scripts/test-apply-bump.sh:311-314
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Test H uses fixed 2.0.0 vs plan’s 2.9.9 example. No functional gap; minor plan fidelity only. Optional: pass a distinct --new-version (extend invoke_apply) to match the plan’s scenario.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0

### [rejected] FINDING_6

### FINDING_6: architecture: .claude/skills/bump-version/scripts/apply-bump.sh:41-50 and scripts/ship-pr.sh:230-239
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Duplicate semver_lt helper in two scripts Future edits might update one copy and not the other Source a single shared helper
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0

### [rejected] FINDING_8

### FINDING_8: architecture: scripts/ship-pr.sh:230-240; .claude/skills/bump-version/scripts/apply-bump.sh:41-51
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Duplicate semver_lt implementations Future change to comparison rules could diverge between ship-pr and apply-bump. Factor into one shared helper or sourced library.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0

