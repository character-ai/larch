### FINDING_2: Read verification expects prose body that the reader strips
- **Reviewer(s)**: Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Codex-Requirements
- **Severity**: major
- **Concern**: The acceptance check asks `architectural-invariants read` to expose the new invariant’s full prose body, but the current reader only preserves headings and `- Why:` bullets. As written, the plan’s self-check will fail on existing behavior unless the invariant is reformatted into reader-supported bullets or the parser is changed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Revise Testing strategy step 1: require the read content block to include the I-Stale-1 heading (INVARIANT_HEADING_RE match). Verify full prose only via git diff -- ARCHITECTURAL_INVARIANTS.md (step 2). Note that full body means the committed markdown entry, not normalized read payload.
  - From Codex-Innovation: Spell out the new invariant as `- Why:` bullets so the current reader emits it, or relax the no-Python rule and update `parse_invariant_entries` plus its tests to preserve the full text.
  - From Cursor-Pragmatic: Split verification: read must include I-Stale-1 heading like siblings; confirm full normative text only in ARCHITECTURAL_INVARIANTS.md via git diff. Drop the read full-body requirement or note reader extension as follow-up
  - From Codex-Pragmatic: Align verification with current behavior: require the `I-Stale-1` heading in the read block; require the full normative text in `ARCHITECTURAL_INVARIANTS.md` via `git diff`. If issue acceptance truly needs body text in read output, that is a separate follow-up to extend `parse_invariant_entries`, not this markdown-only PR.
  - From Codex-Requirements: Rewrite the invariant body as supported `- Why:` bullets, including the citations and mechanical references, or widen the PR to change the parser so prose is retained.


### FINDING_3:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/core/architectural_guidelines.py:287-310
- **Concern**: [SCOPE-REDUCTION] Plan read validation requires full body but parse_invariant_entries keeps only headings for prose invariants. Scenario: Proposed I-Stale-1 text matches sibling paragraph-style entries; after edit, architectural-invariants read emits only `### I-Stale-1: ...` with no following lines, so the plan Testing strategy step to verify full body in read output cannot pass even when ARCHITECTURAL_INVARIANTS.md is correct
- **Proposed resolution**: Narrow Testing strategy to match the reader contract: require I-Stale-1 heading in read output and verify full prose via git diff only, unless the entry adds `- Why:` bullet lines that parse_invariant_entries preserves

### FINDING_2: Ensure architectural-invariants read emits the full invariant body
- **Reviewer(s)**: Codex-Arch, Codex-Pragmatic, Codex-Requirements
- **Severity**: major
- **Concern**: The plan still permits `I-Stale-1` to land in a form that `architectural-invariants read` strips, so the canonical reader surface may show only the heading instead of the full invariant body required by acceptance.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: "Reformat I-Stale-1 into `- Why:` bullets so the reader emits the full body, or widen this PR to update `parse_invariant_entries` and its tests."
  - From Codex-Pragmatic: "Revise the plan so the read command emits the full `I-Stale-1` body, either by updating `parse_invariant_entries` with focused tests or by formatting the invariant in the reader-supported shape while preserving the required normative content"
  - From Codex-Requirements: "Make the firm plan satisfy full-body read output: either format the new invariant body using reader-preserved `- Why:` lines, or add firm parser and targeted test updates that preserve invariant prose in `architectural-invariants read`"


