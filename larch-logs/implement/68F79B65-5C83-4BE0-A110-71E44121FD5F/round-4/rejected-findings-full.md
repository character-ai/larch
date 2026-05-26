### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: `vN_vote` from `vote_for_id` not cross-checked against parser output
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: TSV `vN_vote` comes from `vote_for_id`, not `PARSED_VOTE`. Future line-shape changes could let vote and rating parsers disagree on the same row without detection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_12: Sole MainAgent TSV path omits forensic rating axes
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: MainAgent sole-voter adjudication sets `voting_result` from votes but does not parse forensic rating axes into TSV. Zero-judge MainAgent rerun files with `CORRECTNESS`/`SEVERITY` tokens produce empty `vN` rating columns in committed larch-logs, defeating Lesson 2 analytics on that path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_17

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_17: Retry prefix constants lack grep harness coverage for 4-axis shape
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Retry prefix constants were updated for 4-axis shape without grep harness coverage. Drift between renderer and retry text might not fail CI until runtime voter retries.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_18

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_18: `--voter` paths not confined under `--design-tmpdir`
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `--voter SLOT:PATH` accepts any readable path without requiring it under `--design-tmpdir`. Mis-invoked tally or tampered `VOTER_N_PATH` can aim vote parsing at arbitrary host files; parsed votes/ratings can enter `findings-classification.tsv` and be published after redaction.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_19

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_19: Tally failure replaces classification TSV with header-only
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: On tally `rc!=0`, `plan-review-loop.sh` replaces `findings-classification.tsv` with header-only. Publish can still stage an empty forensic file; analytics cannot distinguish tally-error from zero-findings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: Findings-classification lib is header-only; tally internals not shared
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `lib-findings-classification.sh` only defines the TSV header; slot assignment and TSV write logic remain in the enlarged tally script. Issue #2675 and future forensic work must copy or re-source tally internals instead of a small shared module, increasing merge-conflict surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_20

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_20: `parse_rating_for` swallows parser hard failures
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `parse_rating_for` uses `|| true` on parser failure. A parser crash yields empty `vN_uncertain` cells instead of the contract’s `uncertain=true` default.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_21

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_21: Whitespace tokenization misses hyphen-glued axis forms
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Whitespace-only axis tokenization misses hyphen-glued forms (e.g. `YES-CORRECTNESS=true`). Vote may record as YES while axes stay empty and `uncertain=true`, reducing forensic fidelity without parse-rate retry.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: Redundant `vote_for_id` calls per voter per finding in TSV write
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `write_findings_classification` calls `vote_for_id` twice per voter per finding. Large ballots multiply awk subprocess cost on every TSV write with no functional benefit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: Unused `kind` and `security` locals in TSV write path
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Unused locals `kind` and `security` in `write_findings_classification` mislead readers into expecting security/OOS handling in the TSV path that exists only in the markdown loop.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: Header-only TSV paths inline header emission instead of central helper
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Header-only `findings-classification.tsv` paths in `plan-review-loop.sh` call `emit_findings_classification_header` inline instead of delegating through tally or a single lib helper. A 22nd schema column could be updated in tally/tests but missed on zero-findings early exits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: Axis parser treats `KEY=value` tokens in free-form rationale
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `parse-judge-vote-and-rating.sh` treats any pre-delimiter `QUALITY=` / `CORRECTNESS=` token as real even in rationale without `--`. Judge output like `QUALITY=good` followed by prose containing `QUALITY=weak` can record `weak` in committed TSV, corrupting forensic analytics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_9: Parse-rate does not require four forensic axis tokens
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Parse-rate validation does not require `CORRECTNESS` / `SEVERITY` / `QUALITY` / `UNCERTAIN`. Judges can emit vote-only lines; TSV gets empty forensic axes despite a successful run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

