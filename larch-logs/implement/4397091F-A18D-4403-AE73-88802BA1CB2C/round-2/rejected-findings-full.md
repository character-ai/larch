### [rejected] FINDING_12

### FINDING_12: code-quality: scripts/test-larch-log.sh; skills/review-and-fix/scripts/test-review-and-fix.sh (scout sections)
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Extra regression cases (duplicate basename symlink dynamic-archetypes test 8 invalid slots) beyond issue tests 1-7. Only tracking/traceability noise for reviewers expecting exactly seven tests. Update companion .md contracts or issue text to acknowledge the added cases.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 NEUTRAL=0

### [rejected] FINDING_13

### FINDING_13: code-quality: skills/review-and-fix/scripts/review-and-fix.md:104
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Doc says non-empty and not na but code defaults empty to na Wording implies empty skips flush differently than implemented Align prose with normalization and comparison
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=2 EXON=0 NEUTRAL=0

### [rejected] FINDING_14

### FINDING_14: code-quality: skills/review-and-fix/scripts/review-and-fix.md:104
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Doc says non-empty and not na but code only implements != na after empty default. Documents a stricter contract than the shell implements (whitespace-only still flushes). Update doc or implement explicit non-empty trim check.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=2 EXON=0 NEUTRAL=0

### [rejected] FINDING_15

### FINDING_15: code-quality: skills/review-and-fix/scripts/review-and-fix.md:104
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Doc claims non-empty SCOUT_STATUS guard; implementation treats empty like na via parameter expansion. Doc/implementation mismatch for edge documentation readers. Match SKILL.md wording (SCOUT_STATUS:-na and != na).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 NEUTRAL=0

### [rejected] FINDING_16

### FINDING_16: code-quality: skills/review-and-fix/scripts/review-and-fix.md:104 area
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Doc says non-empty and not na while code defaults empty SCOUT_STATUS to na Readers expect different behavior for empty SCOUT_STATUS Align documentation with defaulting rules
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 NEUTRAL=0

### [rejected] FINDING_18

### FINDING_18: correctness: skills/review-and-fix/scripts/review-and-fix.sh:1096
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Flush guard uses -x on LARCH_LOG_SH instead of plan wording (set). If LARCH_LOG_SH is set but not executable, scout manifest flush is silently skipped. Use -n/-f as in plan or document and test the executable requirement explicitly.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 NEUTRAL=0

### [rejected] FINDING_22

### FINDING_22: correctness: skills/review-and-fix/scripts/review-and-fix.sh:1108-1122
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Non-na SCOUT_STATUS still writes manifest when SCOUT_MANIFEST/YIELD paths are missing If files disappear before flush JSON shows ok with empty manifest_basename yield_tsv_basename losing audit linkage Warn or skip write when expected files absent for ok status
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0

### [rejected] FINDING_25

### FINDING_25: risk-integration: scripts/test-larch-log.sh (plain fixture block)
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Plan test 4 asked for same artifact set as before; test only checks a subset plus negatives An extra unintended file in round output could pass unnoticed Optionally assert full sorted basename allow-list for the fixture
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0

### [rejected] FINDING_26

### FINDING_26: risk-integration: scripts/test-larch-log.sh (plain write-round fixture block)
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Regression test 4 does not assert full round directory equality to a prior baseline. An extra unexpected file could appear in round-1/ and tests might still pass. Compare full sorted file list or directory fingerprint to a frozen expected set.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0

### [rejected] FINDING_27

### FINDING_27: risk-integration: skills/review-and-fix/scripts/review-and-fix.sh:1096-1100
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Scout flush gated on executable LARCH_LOG_SH with no fallback warning If LARCH_LOG_SH is unset or not executable while SCOUT_STATUS is ok the manifest flush is skipped silently with no execution-issues entry Log a warning or relax gate when SCOUT_STATUS!=na after normalization
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0

### [rejected] FINDING_28

### FINDING_28: security: skills/review-and-fix/scripts/review-and-fix.sh:1102-1109
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] SCOUT_MANIFEST and YIELD_TSV_FILE paths are not rooted-checked before basename is logged. Malicious review-core could point at existing sensitive paths; basenames can leak into committed audit logs. Canonicalize paths and require they live under IMPLEMENT_TMPDIR or round_dir before recording.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 NEUTRAL=0

### [rejected] FINDING_7

### FINDING_7: architecture: skills/review-and-fix/scripts/review-and-fix.sh:1123-1139 scripts/lib-larch-log.sh:56-62
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Run-root review-scout-manifest.json is replace-mode without round suffix Multi-round Step 5 overwrites prior scout summary at implement run root Document or version batch per round
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 NEUTRAL=0

### [rejected] FINDING_8

### FINDING_8: architecture: skills/review-and-fix/scripts/test-review-and-fix.sh; scripts/test-larch-log.sh
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Test count exceeds plan items 1-7 (extra test 8 and extra write-round scenarios). None unless release notes or issue #2356 must match exact test enumeration. Update issue text or accept as follow-on hardening.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 NEUTRAL=0

