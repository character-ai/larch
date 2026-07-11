---LARCH-REJECTED-BEGIN---
## Considered Plan Review Suggestions (Not Adopted)

These reviewer suggestions were considered but not adopted. Some may already be addressed by the current plan; they are not automatically unimplemented gaps.

### [Plan Review] FINDING_3

### FINDING_3: Pin the registry liveness predicate
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Concern**: The adapter does not specify whether a registry row is live when either its child or daemon is live, or only when both are live. Inconsistent semantics can unlink a still-running row or skip required stale handling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Pin step-8-ship.sh semantics: treat the row as live if child_liveness OR daemon_liveness is true; only unlink dead rows without a completed result env; on live row with identity mismatch emit ASSESSMENT_ERROR=active-stale-identity-mismatch and exit 2.


### [Plan Review] FINDING_5

### FINDING_5: Reject duplicate handoff kinds before normalization
- **Reviewer(s)**: Cursor-Innovation, Cursor-Requirements
- **Severity**: major
- **Concern**: `normalize_kinds` silently deduplicates repeated tokens, so passing raw handoff values allows duplicate `DETAIL` or `DETAIL_FILE` tokens instead of producing the required tool failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Before normalize_kinds, split DETAIL or DETAIL_FILE on commas, trim tokens, and exit 2 on empty, unknown, or duplicate tokens; call normalize_kinds only after that scan passes; add a harness case for repeated tokens.
  - From Cursor-Requirements: In step-8-assessment.sh, pin the assessments handoff grammar from ship-pr-exit-matrix.md: read DETAIL then DETAIL_FILE fallback, split on commas, trim tokens, fail closed on empty/unknown/duplicate tokens, then call normalize_kinds only on the cleaned unique set. Add a harness case for duplicate-token rejection.


### [Plan Review] FINDING_8

### FINDING_8:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Focus area**: architecture
- **Location**: skills/implement/scripts/step-8-assessment.sh
- **Concern**: [SCOPE-REDUCTION] Approach step 2 and edge cases require rejecting duplicate kind tokens but the script section delegates only to Piece 2 normalize_kinds which silently deduplicates. Scenario: Implementers may add a redundant pre-normalize duplicate scan or emit exit 2 for inputs normalize_kinds would accept; that adds Bash complexity without changing assessment identity or results
- **Proposed resolution**: Remove duplicate rejection from approach step 2 and the repeats-a-token edge case; state that normalize_kinds dedupe defines requested-kind identity and that duplicate DETAIL tokens are rejected by the Piece 4 assessments route per ship-pr-exit-matrix.md before this adapter runs


### [Plan Review] FINDING_9

### FINDING_9:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: architecture
- **Location**: skills/implement/scripts/step-8-assessment.sh:path-safety
- **Concern**: [SCOPE-REDUCTION] Launch-identity sidecar path is undefined while identity is stored in merge-result. Scenario: The plan both stores ASSESSMENT_REQUESTED_KINDS and ASSESSMENT_COVERED_FINGERPRINT in the merge-result envelope and separately lists a launch-identity sidecar to protect and clear. No path or filename is defined. An implementer may add a second identity file, extra symlink checks, and cleanup logic the harness does not cover.
- **Proposed resolution**: State the launch identity lives only in the merge-result envelope (and copied result env). Remove sidecar wording from protect and cleanup bullets. Mirror that in step-8-assessment.md.


### [Plan Review] FINDING_10

### FINDING_10:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: architecture
- **Location**: skills/implement/scripts/step-8-assessment.sh:handoff-parse
- **Concern**: [SCOPE-REDUCTION] Duplicate-kind edge case conflicts with normalize_kinds-only parsing. Scenario: Edge cases require rejecting repeated tokens, but the script section delegates kind resolution solely to Piece 2 normalize_kinds, which silently deduplicates per test_architectural_assessment.py. The ship driver already emits deduped comma lists and Piece 4 will reject repeats before calling the adapter. Keeping the edge case forces extra Bash logic with no normal-path benefit.
- **Proposed resolution**: Remove repeats-a-token from adapter edge cases and harness expectations, or if retained, require explicit duplicate detection on raw split tokens before calling normalize_kinds.


### [Plan Review] FINDING_11

### FINDING_11:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: architecture
- **Location**: skills/implement/scripts/step-8-assessment.sh:launch-identity
- **Concern**: [SCOPE-REDUCTION] launch-identity sidecar wording invites an extra artifact. Scenario: Approach step 7 mentions clearing a launch-identity sidecar, while the normative contract stores ASSESSMENT_REQUESTED_KINDS, ASSESSMENT_COVERED_FINGERPRINT, and ASSESSMENT_ATTEMPT only in the merge-result envelope before bgjob start. A literal sidecar file would duplicate state and add cleanup paths not used by step-8-ship.sh or step-8-ci-fixer.sh.
- **Proposed resolution**: Clarify that launch identity lives only in implement-step8-assessment.merge.env; drop sidecar wording from approach step 7 and stale-cleanup bullets unless a separate file is truly required.


### [Plan Review] FINDING_12

### FINDING_12:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: code-quality
- **Location**: skills/implement/scripts/step-8-assessment.md:fingerprint-helper
- **Concern**: [SCOPE-REDUCTION] Covered-fingerprint helper deliverable is unspecified relative to the four-file scope. Scenario: The plan requires a shared Python helper importing Piece 2 validate_materialization, but ### NEW lists only shell/markdown files and forbids Piece 2 edits unless proven insufficient. Implementers may add an unplanned cli.py verb or duplicate preimage logic in the harness.
- **Proposed resolution**: Clarify the helper is a bounded inline python3 block inside step-8-assessment.sh (sys.path bootstrap matching step-8-ship.sh registry helpers), document its stdout KV contract in step-8-assessment.md, and mirror only that contract in test harness stubs. Do not add a separate Python module unless scope expands. ## Findings ### 1. Handoff duplicate rejection before `normalize_kinds` (correctness) The plan references the existing DETAIL / DETAIL_FILE grammar, and `ship-pr-exit-matrix.md` requires split, trim, and Tool Failure on duplicate tokens. The script section only says to normalize via Piece 2's `normalize_kinds`. Piece 2 deduplicates silently: def test_normalize_kinds_deduplicates_and_orders() -> None: assert assessment.normalize_kinds(["guidelines", "invariants", "guidelines"]) == ("invariants", "guidelines") If the adapter delegates duplicate detection to `normalize_kinds`, repeated handoff tokens will not fail closed. Pin explicit handoff parsing in `step-8-assessment.sh` before any Python normalization call, and add a harness case. ### 2. Bgjob child must be the bash wrapper (architecture) Child mode is responsible for validating `ARCHITECTURAL_ASSESSMENT_*` stdout and writing adapter KVs (`ASSESSMENT_STATUS`, `ASSESSMENT_RESULTS`, etc.) into merge-result. The foreground launch section lists `bgjob start` arguments but does not pin the child argv. Without an explicit self-invoke pattern (`bash step-8-assessment.sh --bgjob-child`), an implementer could start `architectural-assessment run` directly under bgjob and skip the adapter envelope that rejoin logic depends on. Match `step-8-ship.sh`: python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" bgjob start \ --step "$STEP" \ --tmpdir "$IMPLEMENT_TMPDIR" \ --budget-s 21600 \ --owner-pid "${LARCH_CLAUDE_PID:-$PPID}" \ --merge-result-env "$MERGE_RESULT_ENV" \ -- \ bash "$SCRIPT_DIR/step-8-ship.sh" --bgjob-child --merge-result-env "$MERGE_RESULT_ENV" ### 3. [SCOPE-REDUCTION] Pin the fingerprint helper inside the four-file boundary (completeness) Round 1 fixes defined the normative `ASSESSMENT_COVERED_FINGERPRINT` preimage well. The plan still requires a shared Python helper that imports Piece 2's `validate_materialization`, but the firm file list contains only the adapter script, contract doc, and harness files. Scope controls also say not to change Piece 2 unless testing proves insufficiency. There is no firm home for the helper, which invites either unplanned Python surface area or duplicated preimage logic between script and harness. Minimum-change fix: state that the helper is an inline bounded `python3` block in `step-8-assessment.sh` (same `sys.path` pattern as `step8_live_registry_exists` in `step-8-ship.sh`), document its stdout contract in `step-8-assessment.md`, and have harness stubs mirror that contract only. --- Prior accepted findings (budget pin, fingerprint grammar, no post-run fingerprint compare, zero-duration rejoin, foreground retry owner, active-stale refusal, child non-zero exit, terminal fail-closed rejoin) appear addressed in the current plan. I did not re-raise rejected items (both DETAIL+DETAIL_FILE, NEEDS_USER_REASON validation, `--owner-pid`, REPO_ROOT key name, concurrent serialization, whitespace trim as a separate item) without new evidence.

---LARCH-REJECTED-END---
