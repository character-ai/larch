### [rejected] FINDING_2

**Rejected subtype:** dismissed (0 YES)

### FINDING_2: Duplicate detection misses notes already recorded under Tool Failures
- **Reviewer(s)**: codex-specialist-correctness, codex-specialist-edge-cases
- **Severity**: important
- **Concern**: The duplicate scan only looks at Warnings rows, so a note already present in Tool Failures can be appended again under Warnings and produce two records for the same deviation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_12: Redaction and chunking order can disagree with flush-path hashing
- **Reviewer(s)**: dyn-dyn-runlog-dedupe
- **Severity**: important
- **Concern**: Candidate and markdown-side keys are computed by redacting the full Warnings body before chunking, while the flush path chunks first and redacts each chunk separately. On multiline chunks, that can make dedupe keys or `source_sha256` values differ from what flush already committed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-runlog-dedupe: Extract a shared helper used by both paths: chunk with `execution_issue_chunks`, then `_redact_batch_payload` per chunk, then compute `structured_body_dedupe_keys` and `_normalize_body_for_hash` on each redacted chunk—the same sequence as `_execution_issue_record`.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0

