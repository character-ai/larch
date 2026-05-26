### [rejected] FINDING_12

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_12: correctness: scripts/parse-judge-vote-and-rating.sh:38-72
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Without -- delimiter, prose tokens matching axis=value patterns are parsed as real ratings. A judge writing "reviewer mentioned QUALITY=weak" without -- can populate vN_quality=weak in the committed TSV. Tighten parsing or require -- before rationale; update harness to match.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_14: correctness: skills/design/scripts/plan-review-loop.sh:97-99
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Zero-findings header is duplicated inline, not sourced from tally helper. Future schema column changes in tally could leave empty-round design logs with an outdated header line. Call tally for header-only output or share emit_findings_classification_header.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_16: risk-integration: skills/design/scripts/tally-plan-review.sh:274-277
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] parse_rating_for captures parser via stdout while emit_kv uses FD 3 under larch_quiet_init /design tally without LARCH_QUIET_DISABLE leaves vN rating columns empty in findings-classification.tsv while vote columns still populate via vote_for_id stdout Wrap parser invocation with LARCH_QUIET_DISABLE=1 or FD-3 capture; add harness without quiet disable
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_17

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_17: security: scripts/design-log-publish.sh:279-335
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] plan-review publish allowlist rejects symlinks but not hardlinks at allowlisted paths. A session writer hardlinks plan-review/round-1/findings-classification.tsv to another readable local file; publish stages that content into public larch-logs after redaction. Reject hardlinked allowlist paths (stat link count / inode checks) or only stage TSV files created by tally in-session.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_18

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_18: security: skills/design/scripts/tally-plan-review.sh:252-326
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] finding_reviewers propagates untrusted ballot attribution into committed design logs. Aggregator text with paths or token-shaped strings lands in larch-logs; gitleaks does not scan larch-logs, so redact-secrets completeness is the only gate. Document untrusted column; consider redacting finding_reviewers or post-processing the TSV before publish.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_19

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_19: security: scripts/parse-judge-vote-and-rating.sh:36-37
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] ballot_id is embedded in an awk regex without escaping. A non-conforming caller could pass metacharacters and mis-parse or stress awk matching. Use literal-prefix matching or escape id before regex construction.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_24

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_24: correctness: scripts/parse-judge-vote-and-rating.sh:43-72
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Without -- delimiter axis-like rationale text is parsed as real axes Judge writes UNCERTAIN=false ... mentioned QUALITY=weak and vN_quality becomes weak Keep prompt discipline; optionally tighten parser or parse-rate warnings
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: code-quality: skills/design/scripts/tally-plan-review.sh:280-413
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Duplicated per-finding vote-count loop in TSV writer and markdown tally. Future tally threshold or JERR rule change updated in one path only leaves TSV and voting-tally.md inconsistent. Extract shared tally_block_votes helper used by both paths.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_36

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_36: architecture: skills/design/scripts/plan-review-loop.sh:87-99
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] write_empty_review_artifacts inlines TSV header instead of tally invocation. Header string could drift from tally emit_findings_classification_header without a failing test. Call tally with empty ballot and --findings-classification-out or share one header helper.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_37

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_37: correctness: scripts/parse-judge-vote-and-rating.sh
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] No quiet-mode PARSED_* capture test. LARCH_QUIET_DISABLE-only harness misses FD3 emit_kv breakage under larch_quiet_init. Add one quiet-mode capture case like test-tally-plan-review emit_kv pattern.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: code-quality: skills/design/scripts/plan-review-loop.sh:97-99
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] write_empty_review_artifacts duplicates 21-column header literal. Adding a column updates tally header but empty-round short-circuit can emit stale header-only TSV. Invoke tally on empty ballot or share emit_findings_classification_header.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_49

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_49: **correctness** `scripts/parse-judge-vote-and-rating.sh:43-46` — Rationale scoping uses `index(scoped, " -- ")` (ASCII space–dash–dash–space only). With a tab before `--` (`...\t-- reviewer mentioned QUALITY=weak`), the delimiter is not found; a live check then sets `PARSED_QUALITY=weak` from rationale text instead of the intended pre-delimiter value `good`. Prompts specify ` -- `, but minor formatting drift is plausible in LLM output. **Suggested fix:** Treat `[[:space:]]--[[:space:]]` (any whitespace around `--`) as the delimiter, or normalize tabs to spaces before `index`, and add a harness case for tab-before-`--`.
- **Reviewer**: dyn-awk-parser-correctness-output.txt
- **Concern**: - **correctness** `scripts/parse-judge-vote-and-rating.sh:43-46` — Rationale scoping uses `index(scoped, " -- ")` (ASCII space–dash–dash–space only). With a tab before `--` (`...\t-- reviewer mentioned QUALITY=weak`), the delimiter is not found; a live check then sets `PARSED_QUALITY=weak` from rationale text instead of the intended pre-delimiter value `good`. Prompts specify ` -- `, but minor formatting drift is plausible in LLM output. **Suggested fix:** Treat `[[:space:]]--[[:space:]]` (any whitespace around `--`) as the delimiter, or normalize tabs to spaces before `index`, and add a harness case for tab-before-`--`.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=1

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: code-quality: skills/design/scripts/tally-plan-review.sh:274-319
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] parse_rating_for spawns subprocess and kv_value awk per cell. 30-finding 3-judge round runs 90+ parser invocations plus hundreds of awk splits. Batch-parse each voter file once per tally invocation.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

