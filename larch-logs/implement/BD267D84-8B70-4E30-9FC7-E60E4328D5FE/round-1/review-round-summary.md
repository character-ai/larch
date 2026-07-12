# Review Round 1

- Mode: `diff`
- 10 accepted, 2 rejected (4 neutral)

## Accepted Findings

### FINDING_1: Partition batch filing can invent undeclared dependencies
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: major
- **Concern**: Partition batch invocation omits `--no-dep-llm`, allowing the LLM to add blocker edges that are absent from `partition-deps.tsv`; the resulting graph can violate the operator-approved partition and independent-piece semantics. The intra-batch dependency file should be supplied only when non-empty.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Require --no-dep-llm on every partition batch invoke; keep --intra-batch-deps-file conditional on non-empty TSV; add regression test.
  - From cursor-specialist-testing: Require --no-dep-llm for partition batches and test the empty-TSV independent-pieces case.


### FINDING_3: Step 1c can ask a preliminary partition question
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-testing
- **Severity**: major
- **Concern**: The Step 1c sprawl heuristic still presents a preliminary Split/Cancel question before the unified Split-path question, potentially causing two partition prompts. Sprawl should enter the unified Split path directly, with Cancel routed through Other/chat.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-testing: Rewrite Step 1c to match unified Split-path entry and pin the contract in test-design-structure.sh.


### FINDING_4: Step 1c and Step 1d specify inconsistent sprawl behavior
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: major
- **Concern**: Step 1c describes a preliminary prompt while Step 1d describes direct unified Split-path entry, leaving sprawl routing nondeterministic.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.


### FINDING_5: Annotation does not require a complete piece mapping
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: major
- **Concern**: Annotation accepts any zero-failure subset of issue URLs instead of requiring a one-to-one mapping for every prepared piece. A missing piece can therefore be treated as successfully filed, allowing migration and closure to proceed incomplete.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.


### FINDING_6: Migration does not fail closed on live dependency drift
- **Reviewer(s)**: codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-testing, dyn-dyn-dependency-migration
- **Severity**: major
- **Concern**: Migration validates persisted manifest edges individually but does not re-read and compare the original issue’s complete live `blocked_by` and `blocking` sets before removals or retry continuation. Dependencies added, removed, or swapped after the snapshot can remain on the original while migration reports success and closure proceeds with an incomplete graph.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Re-read original blocked_by/blocking before removals; abort if live edges are not exactly the snapshotted manifest set (modulo verified replacements).
  - From codex-specialist-testing: Re-read both original dependency sets before removal, compare them to the manifest, fail closed on drift, and add changed-live-graph coverage.
  - From dyn-dyn-dependency-migration: On every `migrate-deps` entry (including manifest re-entry), read live original dependencies, require exact equality with manifest edges (or refresh the manifest only before any mutation), and fail closed when live relations differ; extend `close_original_issue` to repeat the same check before close.


### FINDING_7: Migration failures are not durably recorded
- **Reviewer(s)**: codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases, dyn-dyn-dependency-migration
- **Severity**: major
- **Concern**: Authorization denials and operational migration failures—including dependency reads, mutations, verification, and postcondition failures—return status values without consistently appending redacted execution-issues records and stable failure-phase rows. Failed or partial migrations therefore lack the required audit trail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Call _append_failure (or run-log append-failure) on auth denial, gh/cli failures, and postcondition misses before returning non-ok.
  - From codex-specialist-edge-cases: Record every migration failure through the existing execution-issues path and emit stable status and phase rows on each failure path.
  - From dyn-dyn-dependency-migration: On each failed read, mutation, readback, or postcondition check, append a redacted failure record via `_append_failure` (or the run-log execution-issues path) with site `design decompose migrate-deps`, preserving tmpdir state for retry.


### FINDING_8: Resume flow lacks migrate-then-close guidance
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: major
- **Concern**: After filing succeeds but dependency migration or closure fails, resumed `/design` runs have no documented path to run `migrate-deps` before `close-original`; closure consequently fails or lacks an explicit recovery sequence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Restore resume-close rules: when .decompose-issues-filed exists and migration is incomplete or stale, run migrate-deps before close-original.


### FINDING_9: Close does not re-verify intra-piece dependencies
- **Reviewer(s)**: cursor-specialist-correctness, dyn-dyn-dependency-migration
- **Severity**: major
- **Concern**: The migration postcondition and close path verify replacement and original-edge removal but do not verify every declared `partition-deps.tsv` intra-piece edge. Missing or removed intra-piece edges can therefore go unnoticed before the original issue is closed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From dyn-dyn-dependency-migration: Include intra-piece edges in the postcondition checked at sentinel write, on `migrate-deps` fast-path re-entry, and in `close_original_issue`; refuse closure unless every `partition-deps.tsv` edge is live-verified on filed piece numbers.


### FINDING_14: Migration recovery and closure-gate coverage is incomplete
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-testing, codex-specialist-testing, dyn-dyn-dependency-migration
- **Severity**: major
- **Concern**: Tests do not cover the plan-required stale-sentinel, partial-retry, changed-live-graph, malformed mapping, ordering, migration-reentry, and closure-refusal paths. High-risk regressions can therefore ship without CI detection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Add the plan-listed migration fixtures when extending test_decompose.py
  - From cursor-specialist-testing: Add tests for stale sentinel rejection, changed-live-graph abort, and interrupted migration re-entry.
  - From codex-specialist-testing: Add isolated fixtures for every plan-required migration state, ordering rule, retry path, and closure refusal.
  - From dyn-dyn-dependency-migration: Address the concern above.


### FINDING_15: Remove-blocked-by lacks failure-path tests
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: major
- **Concern**: `remove-blocked-by` has only success coverage, so migration removal failures may regress in exit code or diagnostic behavior without CI detection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Mirror add-blocked-by failure tests for remove_blocked_by_main.
