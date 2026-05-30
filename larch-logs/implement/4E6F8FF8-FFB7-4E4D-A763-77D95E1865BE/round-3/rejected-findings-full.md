### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: risk-integration: (branch)
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Branch stacks #3204 #3209 #3212 review-and-fix version bumps and larch-logs in one diff. CI or make lint failure on shard-12 cannot be attributed to trailer harness vs cleanup vs ship-pr without manual bisect. Split commits by issue or run targeted make targets per surface before merge.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_16: architecture: skills/design/scripts/test-trailer-awk.sh:14-16
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Harness duplicates trailer_nr awk one-liner instead of sharing wrapper helper. Future edit to _plan_optional_trailer_nr only breaks production parsing; test-trailer-awk.sh still passes. Document must-stay-in-sync linkage or factor shared trailer_nr helper used by both paths.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_17

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_17: `parse`: all-three, none, octal-rejected, block-boundary, blank boundary, mech true/false, `010` retention, duplicate `diff_added` (`block_len=2`, last-match-wins value `2`) — covered
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - `parse`: all-three, none, octal-rejected, block-boundary, blank boundary, mech true/false, `010` retention, duplicate `diff_added` (`block_len=2`, last-match-wins value `2`) — covered
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_18

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_18: `keys` / `values`: mech true/false, `010`, octal empty/retained, last-match-wins on duplicate — covered
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - `keys` / `values`: mech true/false, `010`, octal empty/retained, last-match-wins on duplicate — covered
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_19

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_19: `has_key`: present keys, absent/octal/boundary exit-1 with `assert_has_key` wrapper — covered; block-boundary split (in-block rc=0 vs orphan rc=1) documented in `test-trailer-awk.md`
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - `has_key`: present keys, absent/octal/boundary exit-1 with `assert_has_key` wrapper — covered; block-boundary split (in-block rc=0 vs orphan rc=1) documented in `test-trailer-awk.md` Claim #1 (Gate A/B wiring) was correctly scoped as already resolved; only structural pin tightening was required and delivered.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: code-quality: skills/design/scripts/test-trailer-awk.sh:26-35
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] run_has_key duplicates run_awk awk invocation wiring. Two places to update when trailer_nr or mode flags change. Fold has_key into run_awk with an optional key parameter.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: code-quality: skills/design/scripts/test-trailer-awk.md:15-17
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Expected-failure prose implies has_key exit 1 for any block-boundary case. Readers may expect block-boundary to return rc=1 before reading the split-fixture note. Rewrite to state orphan/blank fixtures rc=1 and in-block block-boundary rc=0 first.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

