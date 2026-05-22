### FINDING_1: correctness: skills/implement/scripts/oos-disposition-shared.inc.bash:20-45
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Rejected-marker counter documents Rejected / Out-of-Scope headings but awk only extracts after ## Rejected A body that uses only a Rejected / Out-of-Scope heading (no ## Rejected line) records as rejected in the case filter yet yields zero counted markers; gate and oos-silent-drop scan can false-fail disposition Align awk capture with the documented heading shapes or narrow the jq/case filter to match implemented parsing only
- **Suggested revision**: Address the concern above.


### FINDING_12: risk-integration: skills/implement/scripts/test-oos-disposition-gate.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Regression harness never asserts filed URLs sourced only from --oos-issues-ndjson. A regression in the union path could ship while CHANGELOG claims NDJSON URLs satisfy disposition; CI would still pass on existing cases only. Add a passing harness where filed URLs exist only in the NDJSON sidecar.
- **Suggested revision**: Address the concern above.


### FINDING_13: correctness: skills/implement/scripts/oos-disposition-shared.inc.bash:25-51
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] count_rejected_oos_markers_from_ndjson sums per-JSON-line counts without deduping OOS indices. Duplicate NDJSON rows repeating the same rejected OOS block inflate rejected_oos_markers and can mask a silent drop on another block. Dedup by OOS index or document writer uniqueness; optionally clamp rejected count when comparing to non_security_oos.
- **Suggested revision**: Address the concern above.


### FINDING_2: correctness: skills/implement/scripts/oos-non-security-block-count.awk:12-16
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Security focus-area detection requires security plus specific delimiters Focus-area values like security-hardening are counted as non-security; disposition gate may stall runs that correctly tagged security-ish labels Document exact allowed tokens or broaden the prefix/boundary rule deliberately
- **Suggested revision**: Address the concern above.


### FINDING_22: correctness: .claude/skills/audit-runs/scripts/audit-scan-run.sh:486-516
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Recursive find sums all oos-accepted*.md which can double-count duplicate OOS markdown across review rounds versus the gate’s three-file aggregate. Multi-round run dirs inflate acc_total vs a single filed URL batch producing false fail (or distorted counts) on oos-silent-drop. Align scan inputs with the gate’s canonical accepted-OOS paths or dedupe blocks before totals.
- **Suggested revision**: Address the concern above.


### FINDING_24: correctness: skills/implement/scripts/oos-disposition-shared.inc.bash:32-48
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] jq failures skip NDJSON lines via continue undercounting rejected markers. Corrupted partial JSONL yields rejected=0 and can force gate exit 1 or skew audit results without surfacing parse failure. Surface jq errors (exit 2 or explicit error field) instead of silent continue.
- **Suggested revision**: Address the concern above.


### FINDING_3: risk-integration: skills/implement/SKILL.md:3298-3304
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Gate omits --oos-issues-ndjson when session-id file is empty If session-id is missing but accepted OOS exists and URLs exist only in the NDJSON batch, filed URL and rejection evidence are skipped; gate may exit 1 incorrectly Always pass the NDJSON path when known or exit 2 when required evidence paths cannot be resolved
- **Suggested revision**: Address the concern above.


### FINDING_7: correctness: .claude/skills/audit-runs/scripts/audit-scan-run.sh:88-115
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] oos-silent-drop inline-triage probe uses live repo HEAD merge-base, not run-log git identity Auditing a copied RUN_DIR from another cwd/branch counts Inline-triage lines from the wrong git history → high-severity scan false pass or false fail. Derive range from run-log artifacts when available; document cwd coupling or refuse git path without manifest proof.
- **Suggested revision**: Address the concern above.


### FINDING_8: correctness: skills/implement/scripts/oos-non-security-block-count.awk:12-13
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Security-routed detection is case- and suffix-sensitive -focus-area: Security- or -security-related- is counted as non-security → false gate failure or wrong obligation set. Case-fold value; widen security prefix rule and add harness cases for capitalized / compound values.
- **Suggested revision**: Address the concern above.


