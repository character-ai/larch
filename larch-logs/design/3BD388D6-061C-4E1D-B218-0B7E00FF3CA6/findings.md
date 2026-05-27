### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/tally-plan-review.sh:314-321
- **Concern**: EXIT trap stays at line ~314 while most exit 2 paths are earlier. Scenario: Plan claims tally-error on exits at 81/87/112/321 and the new test uses unreadable ballot (112), but trap is not registered until 314; only post-trap exit 321 gets fallback—contradicts always-emit contract and the proposed harness case
- **Proposed resolution**: Register cleanup EXIT immediately after `_tally_status_emitted` init (post-mkdir); guard `rm -rf` with `[[ -n "${WORKDIR:-}" ]]`; or emit `tally-error` explicitly on each pre-trap exit 2 path

### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/tally-plan-review.sh:79-113,310-314
- **Concern**: Tally error fallback is specified inside a trap that is registered after several planned-covered exit paths and checks $? after cleanup work. Scenario: Early argv/ballot failures exit before the EXIT trap exists, and a cleanup body that runs rm before checking $? will see rm's status instead of the script's failing status, so TALLY_PLAN_REVIEW_STATUS=tally-error is still missing on some non-zero exits
- **Proposed resolution**: Register the EXIT trap before argv validation with WORKDIR initialized empty, capture rc at the first line of cleanup, guard rm with [[ -n ${WORKDIR:-} ]], then emit tally-error when rc is non-zero and the success guard is false

### FINDING_3:
- **Reviewer(s)**: Codex-Arch
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: scripts/dispatch-plan-voters.sh:211-236
- **Concern**: The proposed per-voter KV helper does not account for the existing interleaved stdout contract including VOTER_PATHS_FILE. Scenario: Replacing the current emit block with three per-slot helper calls either drops VOTER_PATHS_FILE or changes the byte-order the plan says must remain stable
- **Proposed resolution**: Keep VOTER_PATHS_FILE emission and current ordering inline, or make the helper block-level with all three voter records plus plan_voter_paths_file so it can reproduce the existing sequence exactly

### FINDING_4:
- **Reviewer(s)**: Cursor-Edge, Cursor-dyn-shell-trap-semantics
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/tally-plan-review.sh:311-314
- **Concern**: EXIT cleanup checks $? after rm -rf. Scenario: Trap runs after rm -rf; $? is usually 0 so tally-error fallback never fires on post-trap exit 2 paths (e.g. 306, 321) despite the always-emit goal
- **Proposed resolution**: Capture exit status first in cleanup (same pattern as scripts/ci-wait.sh:171: EXIT_STATUS=$? before rm -rf) and test against $? != 0 using the saved value

### FINDING_5:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/tally-plan-review.sh:79-314
- **Concern**: Tally fallback trap as planned is installed too late and can lose the original failing rc. Scenario: Early exits before the current trap registration, such as mutual-exclusion, missing required args, unreadable ballot, and voter validation, still emit no TALLY_PLAN_REVIEW_STATUS; if the fallback is appended after rm -rf, $? can also become 0 before the conditional runs
- **Proposed resolution**: Initialize _tally_status_emitted=false and WORKDIR="" near the top, install the EXIT trap before any nonzero exit path, capture local rc=$? as the first cleanup statement, rm WORKDIR only when nonempty, then emit tally-error when rc is nonzero and the guard is false

### FINDING_6:
- **Reviewer(s)**: Codex-Edge, Cursor-Innovation, Codex-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/dispatch-plan-voters.sh:224-236
- **Concern**: Per-voter KV helper shape conflicts with the existing stdout KV order contract. Scenario: Sequential calls to a helper that emits all four KVs per voter cannot preserve today's interleaved Voter 2/Voter 3 path order or VOTER_PATHS_FILE placement, despite the plan requiring byte-identical behavior and order-regression coverage
- **Proposed resolution**: Revise the plan so the helper emits the whole existing KV block in one function with VOTER_PATHS_FILE placement preserved, or leave the KV emit block inline and only extract effective-judge/degraded-warning logic

### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation, Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/tally-plan-review.sh:79-112,310-314
- **Concern**: Planned EXIT fallback is registered too late and may lose the original rc. Scenario: Current early exits before the existing trap registration would still produce no TALLY_PLAN_REVIEW_STATUS, and checking $? at the end of cleanup after rm -rf can see rm's rc instead of the script failure
- **Proposed resolution**: Initialize the guard and WORKDIR early, register the trap before the first possible non-zero exit, capture local rc=$? as the first cleanup statement, emit tally-error based on that rc, then return rc

### FINDING_8:
- **Reviewer(s)**: Cursor-Pragmatic, Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/tally-plan-review.sh:79-112,310-314
- **Concern**: Planned tally-error fallback is attached too late and reads $? after cleanup work. Scenario: Argv and ballot-file exits occur before the existing EXIT trap is registered, and later nonzero exits can have $? overwritten by rm -rf before the fallback check, so stdout can still miss TALLY_PLAN_REVIEW_STATUS=tally-error
- **Proposed resolution**: Define WORKDIR="" and _tally_status_emitted=false near the top, install cleanup before validation, capture local rc=$? as the first cleanup statement, rm only when WORKDIR is nonempty, and emit tally-error when rc != 0 and the guard is still false

### FINDING_9:
- **Reviewer(s)**: Cursor-Pragmatic, Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/dispatch-plan-voters.sh:224-236
- **Concern**: The proposed per-voter emit helper cannot preserve the existing stdout KV order and VOTER_PATHS_FILE placement. Scenario: Replacing the current ordered emit block with three VOTER_N helper calls either moves VOTER_2/3 tool/status keys ahead of today’s positions or leaves VOTER_PATHS_FILE outside the preserved sequence, conflicting with the plan’s byte-identical contract
- **Proposed resolution**: Keep the emit block inline, or make a single helper emit the entire current ordered sequence including VOTER_PATHS_FILE; do not use the per-voter helper as the replacement for this block

### FINDING_10:
- **Reviewer(s)**: Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/tally-plan-review.sh:310-314
- **Concern**: The cleanup fallback plan checks $? after cleanup work, so it will likely see rm's status instead of the original failing exit. Scenario: An exit 2 after the trap is installed can run rm -rf "$WORKDIR" successfully, reset $? to 0, and skip the required TALLY_PLAN_REVIEW_STATUS=tally-error emit
- **Proposed resolution**: Capture the trap status as the first cleanup line, e.g. local rc=$?, run cleanup with || true, then test rc != 0 for the fallback emit

### FINDING_11:
- **Reviewer(s)**: Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/tally-plan-review.sh:79-112
- **Concern**: The plan relies on the existing EXIT trap, but several required error paths exit before that trap is registered. Scenario: Mutual-exclusion, missing-argv, and unreadable-ballot failures can still return non-zero without the required TALLY_PLAN_REVIEW_STATUS=tally-error stdout KV
- **Proposed resolution**: Register the guarded EXIT trap before argv validation, with WORKDIR initialized empty and cleanup handling an empty WORKDIR, or explicitly emit tally-error on every pre-trap exit path

### FINDING_12:
- **Reviewer(s)**: Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/dispatch-plan-voters.sh:224-236
- **Concern**: The proposed per-voter KV helper conflicts with the stated byte-identical stdout order requirement. Scenario: The current stdout order interleaves Voter 2/3 path keys, VOTER_PATHS_FILE, then tool/status/parse keys; replacing it with three per-voter four-key helper calls changes the contract and can fail the planned KV-order regression
- **Proposed resolution**: Keep the existing emit order exactly, either by leaving this block inline or by defining one helper that emits the whole current sequence including the VOTER_PATHS_FILE placement

### FINDING_13:
- **Reviewer(s)**: Codex-dyn-shell-trap-semantics
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/tally-plan-review.sh:79-112,187-207,301-314
- **Concern**: The proposed fallback extends the EXIT trap that is registered only after several explicit exit paths have already run. Scenario: Argument errors, unreadable ballot files, invalid voter slots, duplicate voter positions, and missing voter files can exit before trap cleanup is installed, so they will not emit TALLY_PLAN_REVIEW_STATUS=tally-error despite the plan's always-emit invariant
- **Proposed resolution**: Register the status fallback before the first validation exit, initialize _tally_status_emitted before that, and make cleanup tolerate WORKDIR being unset or split status emission from tempdir removal

### FINDING_14:
- **Reviewer(s)**: Codex-dyn-shell-trap-semantics
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/tally-plan-review.sh:310-314
- **Concern**: The proposed cleanup check uses $? at the end of cleanup after rm -rf has already overwritten the script's real exit status. Scenario: If split_ballot_to_blocks or a later set -e pipeline exits nonzero, cleanup runs rm -rf successfully, $? becomes 0, and the tally-error fallback is skipped; if cleanup commands fail, trap behavior depends on set -e rather than the script rc
- **Proposed resolution**: Capture rc as the first command in cleanup, use that saved rc for the guard condition, run rm -rf in a non-fatal form, and return the saved rc from the trap handler

### FINDING_15:
- **Reviewer(s)**: Cursor-dyn-refactor-equivalence, Codex-dyn-refactor-equivalence
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:15,102-115; scripts/dispatch-plan-voters.sh:224-236
- **Concern**: The proposed per-voter voter_coverage_emit_voter_kvs(index,path,tool,status,parse_rate_status) shape does not faithfully preserve today's global KV order. Current output emits VOTER_1's four KVs, then VOTER_2_PATH, VOTER_3_PATH, optional VOTER_PATHS_FILE, both tools, both statuses, then both parse-rate statuses.. Scenario: A helper called once per voter would group VOTER_2_* before VOTER_3_PATH/VOTER_PATHS_FILE or otherwise force extra choreography, violating the plan's byte-identical stdout contract.
- **Proposed resolution**: Use one literal-block helper that takes all three voter tuples plus plan_voter_paths_file and emits lines 224-236 in the current order, or leave VOTER_PATHS_FILE and the interleaved VOTER_2/VOTER_3 emission in the dispatcher.

### FINDING_16:
- **Reviewer(s)**: Cursor-dyn-refactor-equivalence, Codex-dyn-refactor-equivalence
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:13-14,36,77,123-125; scripts/dispatch-plan-voters.sh:196-208
- **Concern**: The plan requires voter_coverage_emit_degraded_warning_if_needed(effective_judges, expected_judges) but never defines expected_judges. In the current dispatcher expected_judges is a fixed constant, expected_judges=3, not derived from the slot list or passed from argv.. Scenario: An implementer replacing the surrounding block could drop the constant, pass an unset variable under set -u, or derive the denominator from surviving slots, changing both the degraded-warning predicate/message and the three-judge panel semantics.
- **Proposed resolution**: Specify the minimum-change contract explicitly: keep expected_judges=3 in dispatch-plan-voters.sh or pass literal 3 to the helper, and preserve the effective judge condition status != failed && parse_rate_status != NOT_SUBSTANTIVE && -s path.
