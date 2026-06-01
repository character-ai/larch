# Review Round 1

- Mode: `diff`
- 11 accepted, 5 rejected (5 exonerated)

## Accepted Findings

### FINDING_1: NEVER #17 still points agents at direct gate invocation
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-state-handshake-output.txt
- **Severity**: important
- **Concern**: NEVER #17 still instructs orchestrator-side `oos-disposition-gate.sh` invocation and failure logging, while Step 8+ / NEVER #18 now require `oos-disposition-checkpoint.sh`. Agents following #17 may skip checkpoint-only wiring, duplicate logging, or bypass the intended OOS disposition contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-state-handshake-output.txt: Address the concern above.


### FINDING_10: Merge-base-absent checkpoint test does not verify range selection
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-fixture-realism-output.txt
- **Severity**: important
- **Concern**: The merge-base-absent checkpoint test uses empty accepted-OOS files and asserts only exit 0, so a regression from `origin/main..HEAD` to `HEAD` could still pass without exercising range-dependent disposition logic.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-fixture-realism-output.txt: Address the concern above.


### FINDING_16: Step 8+ documents only 0/1/2 although helper can propagate other gate statuses
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `SKILL.md` tells agents to branch only on checkpoint exits 0/1/2, but the helper can propagate raw gate statuses like 126/127 or 3+, causing wrong remediation or stall handling for missing/non-executable gate failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_2: NEVER #18 title still names the gate script instead of checkpoint
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: NEVER #18’s title still references `oos-disposition-gate.sh` even though its body points to `oos-disposition-checkpoint.sh`, which may cause contributors searching NEVER blocks to miss the required checkpoint entrypoint.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


### FINDING_20: Ambiguity harness case lacks Tool Failures assertions
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The ambiguity harness case does not assert `Tool Failures` / tool-name logging, so a regression dropping append logging on ambiguity exit 2 would pass CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_21: ship-pr Exit 0 branch can resume pr-create before OOS checkpoint sequence
- **Reviewer(s)**: dyn-state-handshake-output.txt
- **Severity**: important
- **Concern**: The `ship-pr` Exit 0 prose still says to resume `pr-create` after Step 9a.1, while the expanded OOS checkpoint sequence requires checkpoint pass, `run-statistics`, `OOS_PENDING=false`, then resume. Following the earlier bullet can open a PR with pending OOS state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-state-handshake-output.txt: Address the concern above.


### FINDING_24: Missing --design-tmpdir value before implement tmpdir parsing can misfile audit log
- **Reviewer(s)**: dyn-audit-trail-output.txt
- **Severity**: important
- **Concern**: If `--design-tmpdir` is passed without a value before `--implement-tmpdir` is parsed, validation logging can target `/execution-issues.md` or be swallowed, losing the durable Tool Failures row.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-audit-trail-output.txt: Address the concern above.


### FINDING_29: Design tmpdir checkpoint tests can pass without validating design path resolution
- **Reviewer(s)**: dyn-fixture-realism-output.txt
- **Severity**: latent
- **Concern**: The `--design-tmpdir` and `design-export/` checkpoint tests leave accepted-OOS files empty, so `non_sec` remains 0 and the gate exits 0 even if design-path resolution or strict-file wiring is broken.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-fixture-realism-output.txt: Address the concern above.


### FINDING_4: Harness header still describes gate-only coverage
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The `test-oos-disposition-gate.sh` header comment still describes only gate coverage, so contributors may miss that checkpoint cases live in the same harness.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


### FINDING_5: Test fixture tmpdirs are not cleaned up
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `mkitmp` fixture directories are not registered in the existing EXIT trap, so repeated local or CI harness runs can accumulate temporary directories.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_8: Disposition-gap log grep can match validation site accidentally
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: The test grep for `step-8-oos-checkpoint` also matches `step-8-oos-checkpoint-validation`, so a test for the normal checkpoint site could pass using only the validation site.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


