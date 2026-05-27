### FINDING_1: EXIT fallback can miss tally-error status
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Edge, Cursor-dyn-shell-trap-semantics, Codex-Edge, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements, Codex-dyn-shell-trap-semantics
- **Severity**: important
- **Concern**: The planned `tally-error` EXIT fallback is installed after several nonzero exit paths and checks `$?` after cleanup work, so both early validation failures and later failures can still exit without `TALLY_PLAN_REVIEW_STATUS=tally-error`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Register cleanup EXIT immediately after `_tally_status_emitted` init (post-mkdir); guard `rm -rf` with `[[ -n "${WORKDIR:-}" ]]`; or emit `tally-error` explicitly on each pre-trap exit 2 path
  - From Codex-Arch: Register the EXIT trap before argv validation with WORKDIR initialized empty, capture rc at the first line of cleanup, guard rm with [[ -n ${WORKDIR:-} ]], then emit tally-error when rc is non-zero and the success guard is false
  - From Cursor-Edge: Capture exit status first in cleanup (same pattern as scripts/ci-wait.sh:171: EXIT_STATUS=$? before rm -rf) and test against $? != 0 using the saved value
  - From Cursor-dyn-shell-trap-semantics: Capture exit status first in cleanup (same pattern as scripts/ci-wait.sh:171: EXIT_STATUS=$? before rm -rf) and test against $? != 0 using the saved value
  - From Codex-Edge: Initialize _tally_status_emitted=false and WORKDIR="" near the top, install the EXIT trap before any nonzero exit path, capture local rc=$? as the first cleanup statement, rm WORKDIR only when nonempty, then emit tally-error when rc is nonzero and the guard is false
  - From Cursor-Innovation: Initialize the guard and WORKDIR early, register the trap before the first possible non-zero exit, capture local rc=$? as the first cleanup statement, emit tally-error based on that rc, then return rc
  - From Codex-Innovation: Initialize the guard and WORKDIR early, register the trap before the first possible non-zero exit, capture local rc=$? as the first cleanup statement, emit tally-error based on that rc, then return rc
  - From Cursor-Pragmatic: Define WORKDIR="" and _tally_status_emitted=false near the top, install cleanup before validation, capture local rc=$? as the first cleanup statement, rm only when WORKDIR is nonempty, and emit tally-error when rc != 0 and the guard is still false
  - From Codex-Pragmatic: Define WORKDIR="" and _tally_status_emitted=false near the top, install cleanup before validation, capture local rc=$? as the first cleanup statement, rm only when WORKDIR is nonempty, and emit tally-error when rc != 0 and the guard is still false
  - From Cursor-Requirements: Capture the trap status as the first cleanup line, e.g. local rc=$?, run cleanup with || true, then test rc != 0 for the fallback emit
  - From Codex-Requirements: Capture the trap status as the first cleanup line, e.g. local rc=$?, run cleanup with || true, then test rc != 0 for the fallback emit
  - From Cursor-Requirements: Register the guarded EXIT trap before argv validation, with WORKDIR initialized empty and cleanup handling an empty WORKDIR, or explicitly emit tally-error on every pre-trap exit path
  - From Codex-Requirements: Register the guarded EXIT trap before argv validation, with WORKDIR initialized empty and cleanup handling an empty WORKDIR, or explicitly emit tally-error on every pre-trap exit path
  - From Codex-dyn-shell-trap-semantics: Register the status fallback before the first validation exit, initialize _tally_status_emitted before that, and make cleanup tolerate WORKDIR being unset or split status emission from tempdir removal
  - From Codex-dyn-shell-trap-semantics: Capture rc as the first command in cleanup, use that saved rc for the guard condition, run rm -rf in a non-fatal form, and return the saved rc from the trap handler


### FINDING_2: Per-voter KV helper breaks stdout order contract
- **Reviewer(s)**: Codex-Arch, Codex-Edge, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements, Cursor-dyn-refactor-equivalence, Codex-dyn-refactor-equivalence
- **Severity**: important
- **Concern**: The proposed per-voter KV helper cannot preserve the existing interleaved stdout KV order and `VOTER_PATHS_FILE` placement required by the byte-identical contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Keep VOTER_PATHS_FILE emission and current ordering inline, or make the helper block-level with all three voter records plus plan_voter_paths_file so it can reproduce the existing sequence exactly
  - From Codex-Edge: Revise the plan so the helper emits the whole existing KV block in one function with VOTER_PATHS_FILE placement preserved, or leave the KV emit block inline and only extract effective-judge/degraded-warning logic
  - From Cursor-Innovation: Revise the plan so the helper emits the whole existing KV block in one function with VOTER_PATHS_FILE placement preserved, or leave the KV emit block inline and only extract effective-judge/degraded-warning logic
  - From Codex-Innovation: Revise the plan so the helper emits the whole existing KV block in one function with VOTER_PATHS_FILE placement preserved, or leave the KV emit block inline and only extract effective-judge/degraded-warning logic
  - From Cursor-Pragmatic: Keep the emit block inline, or make a single helper emit the entire current ordered sequence including VOTER_PATHS_FILE; do not use the per-voter helper as the replacement for this block
  - From Codex-Pragmatic: Keep the emit block inline, or make a single helper emit the entire current ordered sequence including VOTER_PATHS_FILE; do not use the per-voter helper as the replacement for this block
  - From Cursor-Requirements: Keep the existing emit order exactly, either by leaving this block inline or by defining one helper that emits the whole current sequence including the VOTER_PATHS_FILE placement
  - From Codex-Requirements: Keep the existing emit order exactly, either by leaving this block inline or by defining one helper that emits the whole current sequence including the VOTER_PATHS_FILE placement
  - From Cursor-dyn-refactor-equivalence: Use one literal-block helper that takes all three voter tuples plus plan_voter_paths_file and emits lines 224-236 in the current order, or leave VOTER_PATHS_FILE and the interleaved VOTER_2/VOTER_3 emission in the dispatcher.
  - From Codex-dyn-refactor-equivalence: Use one literal-block helper that takes all three voter tuples plus plan_voter_paths_file and emits lines 224-236 in the current order, or leave VOTER_PATHS_FILE and the interleaved VOTER_2/VOTER_3 emission in the dispatcher.


