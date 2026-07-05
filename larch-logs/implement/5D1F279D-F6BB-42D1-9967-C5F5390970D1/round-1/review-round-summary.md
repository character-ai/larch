# Review Round 1

- Mode: `diff`
- 2 accepted, 1 rejected (1 neutral)

## Accepted Findings

### FINDING_1: Partial-overlap dedup can drop new deviation bullets
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, dyn-dyn-runlog-dedupe
- **Severity**: important
- **Concern**: `append_deviation_note` treats any overlap with an existing chunk key or source SHA as a full duplicate, so a reassessment draft that repeats one bullet but adds new ones can lose the new deviations instead of appending them.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From dyn-dyn-runlog-dedupe: Match flush semantics: treat the note as duplicate only when every candidate chunk key (and sha, if used) is already present (`candidate_keys <= existing_keys | ndjson_keys`), otherwise append only the non-duplicate bullet lines (filter chunks before calling `append_execution_issue`), mirroring `_execution_issue_chunks` + per-chunk `_execution_issue_record` behavior.


### FINDING_5: execution-issues.md should reject symlink targets
- **Reviewer(s)**: codex-specialist-edge-cases
- **Severity**: important
- **Concern**: The append path writes `execution-issues.md` without checking for symlinks or non-regular files, so a crafted `IMPLEMENT_TMPDIR` could redirect the write outside the temp directory.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Address the concern above.


