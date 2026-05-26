### [rejected] FINDING_12

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_12: risk-integration: scripts/lib-voter-parse-rate.sh:13-15
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Retry prefix literals updated but not harness-locked; publish harness omits round-1/unexpected.txt rejection. Voter-parse retry text can drift from renderer; extra plan-review files could be staged if allowlist regresses. Grep retry constants in a harness; add publish negative fixture for unexpected.txt under round-1.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_15

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_15: security: skills/design/scripts/tally-plan-review.sh:223-229
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Voter file paths are only checked for readability, not confined to DESIGN_TMPDIR or checked for symlinks. A compromised or mis-invoked tally could pass --voter Claude:/etc/passwd (or a symlink) and pull content into forensic TSV cells that are later redacted and published under larch-logs/design/. Resolve each voter path with pwd -P and require it to start with the resolved DESIGN_TMPDIR; reject symlinks before parse-judge reads.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_16: security: skills/design/scripts/tally-plan-review.sh:277-279
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] TSV sanitization does not neutralize spreadsheet formula injection prefixes in committed cells. An operator opens findings-classification.tsv in Excel/Sheets; a cell like =cmd|'/C calc'!A0 in finding_reviewers or an axis value can execute as a formula. Prefix cells starting with = + - @ with a safe escape (e.g. leading apostrophe) or strip those prefixes in sanitize_tsv_cell; add harness coverage.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_19

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_19: correctness: scripts/parse-judge-vote-and-rating.sh:42-71
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Without -- delimiter, rationale text containing axis-like tokens overwrites earlier axis values (last token wins). Judge omits -- reason and mentions QUALITY=weak in prose; TSV records weak while YES vote still tallies, producing plausible corrupted forensic data. Constrain axis scan region, require -- before prose in prompts, or use first-valid-axis semantics after the vote token block.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_20

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_20: risk-integration: skills/design/scripts/tally-plan-review.sh:290-294
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] parse_rating_for uses || true and hides parser exit 2 failures. Voter file becomes unreadable after pre-check; vN_vote populated but all rating cells empty, inconsistent TSV row. Only tolerate expected empty-parse exits; surface hard parser failures in tally status or per-slot error columns.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_21

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_21: architecture: skills/design/scripts/plan-review-loop.sh:87-103
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Duplicated 21-column header literal in write_empty_review_artifacts vs emit_findings_classification_header. Schema change updates tally header only; zero-findings early exits emit mismatched header-only TSV. Call single shared header emitter from loop and tally.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_25

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_25: architecture: skills/design/scripts/plan-review-loop.sh:91-104
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Plan preferred invoking tally for header-only TSV on zero-findings exits; write_empty_review_artifacts duplicates the 21-column header string. If tally header columns change, empty-round artifacts can drift from real tally output. Call tally with empty ballot + --findings-classification-out or share one header helper.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_27

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_27: correctness: skills/design/scripts/tally-plan-review.sh:76-78
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Plan acceptance specifies exit 1 for argv mutex; tally exits 2. Callers grepping for exit 1 specifically would mis-handle errors (unlikely today). Use exit 1 or update plan acceptance to non-zero.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: code-quality: skills/design/scripts/tally-plan-review.sh:310-336
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] TSV build calls vote_for_id twice per slot and ignores PARSED_VOTE from the new parser. vN_vote and rating axes can diverge if parsers ever disagree; extra subprocess work per finding per judge. Single parse per voter/id; populate vN_vote from PARSED_VOTE.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: code-quality: skills/design/scripts/tally-plan-review.sh:111-210
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Voter-slot argv parsing legacy inference and TSV emission all live in one ~470-line script. Harder reuse for code-review forensics (#2675) and higher merge conflict risk. Extract voter-slot assignment to a shared lib script.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: code-quality: skills/design/scripts/test-tally-plan-review.md:5
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Plan-listed test-tally-plan-review TSV cases were deferred to test-findings-classification only. CI gap if someone runs only test-tally-plan-review expecting --voter coverage. Add one smoke case or narrow plan acceptance to the new harness.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_8: risk-integration: skills/design/scripts/test-tally-plan-review.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Plan-required 13 TSV/argv cases were not added; harness still uses only legacy --voter-files with no findings-classification.tsv checks. Production plan-review-loop now passes --voter SLOT:PATH; regressions in default TSV path or tally+TSV integration will not be caught by the harness CI still runs every lint. Add planned cases to test-tally-plan-review.sh or update acceptance to state forensic argv coverage is solely in test-findings-classification.sh and add at least one --voter integration case there.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

