### FINDING_1: NEVER #17 still points agents at direct gate invocation
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-state-handshake-output.txt
- **Severity**: important
- **Concern**: NEVER #17 still instructs orchestrator-side `oos-disposition-gate.sh` invocation and failure logging, while Step 8+ / NEVER #18 now require `oos-disposition-checkpoint.sh`. Agents following #17 may skip checkpoint-only wiring, duplicate logging, or bypass the intended OOS disposition contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-state-handshake-output.txt: Address the concern above.

### FINDING_2: NEVER #18 title still names the gate script instead of checkpoint
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: NEVER #18’s title still references `oos-disposition-gate.sh` even though its body points to `oos-disposition-checkpoint.sh`, which may cause contributors searching NEVER blocks to miss the required checkpoint entrypoint.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_3: Checkpoint and gate duplicate non-security OOS counting logic
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `oos-disposition-checkpoint.sh` and `oos-disposition-gate.sh` both count non-security OOS blocks via the same awk logic, creating redundant work and two update sites if counting rules change.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

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

### FINDING_6: [OUT_OF_SCOPE] Gate contract doc still assigns failure logging to orchestrator
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: `oos-disposition-gate.md` still describes consumer/orchestrator-owned `append-tool-failure.sh` logging, which conflicts with the checkpoint helper owning that logging path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] Commit-range fallback logic is duplicated across scripts
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `origin/main` commit-range fallback behavior exists in multiple scripts, risking drift between `ship-pr.sh` and the OOS checkpoint if range rules change.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_8: Disposition-gap log grep can match validation site accidentally
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: The test grep for `step-8-oos-checkpoint` also matches `step-8-oos-checkpoint-validation`, so a test for the normal checkpoint site could pass using only the validation site.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] Zero-OOS gate can still fail outside a git worktree
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: The gate runs inline-triage counting before its `non_sec==0` early exit, so a zero-OOS checkpoint outside a git worktree can exit 2 despite no OOS blocks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_10: Merge-base-absent checkpoint test does not verify range selection
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-fixture-realism-output.txt
- **Severity**: important
- **Concern**: The merge-base-absent checkpoint test uses empty accepted-OOS files and asserts only exit 0, so a regression from `origin/main..HEAD` to `HEAD` could still pass without exercising range-dependent disposition logic.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-fixture-realism-output.txt: Address the concern above.

### FINDING_11: Gate-exit-2 checkpoint test does not exercise invalid checkpoint commit range
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-fixture-realism-output.txt
- **Severity**: latent
- **Concern**: The checkpoint gate-exit-2 case exercises accepted-file / ndjson validation rather than an invalid `--commit-range` produced by checkpoint range resolution, so range-resolution failures could regress unnoticed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, dyn-fixture-realism-output.txt: Address the concern above.

### FINDING_12: Missing harness cases for checkpoint CLI / pre-gate exit 2
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The harness lacks explicit checkpoint CLI and pre-gate validation exit-2 cases, such as missing `--implement-tmpdir` or unknown args, leaving usage/validation regressions without CI coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_13: No explicit origin/main-absent HEAD fallback checkpoint test
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The harness does not explicitly test checkpoint behavior when `origin/main` is absent and the helper should fall back to `HEAD`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_14: [OUT_OF_SCOPE] Session id can be used as an unchecked path segment
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `session-id` is used in path construction without rejecting traversal or unexpected characters, so a party able to rewrite it could influence ndjson discovery paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_15: [OUT_OF_SCOPE] Design tmpdir / ndjson discovery trust tmpdir contents too broadly
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `--design-tmpdir` and find-based ndjson discovery trust session tmpdir contents; symlinks or cross-tmpdir use could steer the gate toward misleading or arbitrary readable inputs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_16: Step 8+ documents only 0/1/2 although helper can propagate other gate statuses
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `SKILL.md` tells agents to branch only on checkpoint exits 0/1/2, but the helper can propagate raw gate statuses like 126/127 or 3+, causing wrong remediation or stall handling for missing/non-executable gate failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_17: Best-effort append can lose durable Tool Failures rows
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Failure-path logging uses best-effort append with `|| true`, so disposition-gap exits can stop ship progression while `execution-issues.md` lacks a durable Tool Failures entry if append/redaction fails.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_18: [OUT_OF_SCOPE] ship-pr has a parallel weaker OOS gate path
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-state-handshake-output.txt
- **Severity**: latent
- **Concern**: `ship-pr.sh` still embeds a separate OOS disposition gate path that does not share checkpoint plumbing or strict/precondition behavior, risking divergence from Step 8+ checkpoint semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, dyn-state-handshake-output.txt: Address the concern above.

### FINDING_19: [OUT_OF_SCOPE] Multiple ndjson files are not treated as ambiguous with non-empty session id
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: When `RUN_ID` is non-empty, multiple ndjson files do not trigger an ambiguity exit, so stale or wrong ndjson may be selected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

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

### FINDING_22: [OUT_OF_SCOPE] Checkpoint exit 2 passthrough is an intentional contract refinement
- **Reviewer(s)**: dyn-state-handshake-output.txt
- **Severity**: nit
- **Concern**: The reviewer notes that propagating checkpoint exit 2 for validation/setup aligns with the plan and is not a regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-state-handshake-output.txt: Address the concern above.

### FINDING_23: [OUT_OF_SCOPE] Helper boundaries are otherwise respected
- **Reviewer(s)**: dyn-state-handshake-output.txt
- **Severity**: nit
- **Concern**: The reviewer notes that the checkpoint helper does not mutate `OOS_PENDING`, `run-statistics`, or PR resume state, and its main exit mapping matches the plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-state-handshake-output.txt: Address the concern above.

### FINDING_24: Missing --design-tmpdir value before implement tmpdir parsing can misfile audit log
- **Reviewer(s)**: dyn-audit-trail-output.txt
- **Severity**: important
- **Concern**: If `--design-tmpdir` is passed without a value before `--implement-tmpdir` is parsed, validation logging can target `/execution-issues.md` or be swallowed, losing the durable Tool Failures row.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-audit-trail-output.txt: Address the concern above.

### FINDING_25: [OUT_OF_SCOPE] Pre-gate failures now improve audit coverage
- **Reviewer(s)**: dyn-audit-trail-output.txt
- **Severity**: nit
- **Concern**: The reviewer notes that ambiguous/missing ndjson pre-gate failures now flow through checkpoint validation logging, improving audit coverage over the old inline path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-audit-trail-output.txt: Address the concern above.

### FINDING_26: [OUT_OF_SCOPE] Gate rc 1/2 logging uses intended checkpoint sites and tool name
- **Reviewer(s)**: dyn-audit-trail-output.txt
- **Severity**: nit
- **Concern**: The reviewer notes that gate rc 1/2 logging uses the expected site tokens, checkpoint tool name, saved exit codes, and stderr sinks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-audit-trail-output.txt: Address the concern above.

### FINDING_27: [OUT_OF_SCOPE] Best-effort append remains by design
- **Reviewer(s)**: dyn-audit-trail-output.txt
- **Severity**: nit
- **Concern**: The reviewer notes that best-effort append semantics are unchanged from the prior inline block and that missing durable rows remain possible if append fails.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-audit-trail-output.txt: Address the concern above.

### FINDING_28: [OUT_OF_SCOPE] NEVER #17 checkpoint drift also noted as documentation-only by audit reviewer
- **Reviewer(s)**: dyn-audit-trail-output.txt
- **Severity**: nit
- **Concern**: The audit reviewer separately tags the NEVER #17 direct-gate wording as out-of-scope documentation drift rather than a helper audit-logging regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-audit-trail-output.txt: Address the concern above.

### FINDING_29: Design tmpdir checkpoint tests can pass without validating design path resolution
- **Reviewer(s)**: dyn-fixture-realism-output.txt
- **Severity**: latent
- **Concern**: The `--design-tmpdir` and `design-export/` checkpoint tests leave accepted-OOS files empty, so `non_sec` remains 0 and the gate exits 0 even if design-path resolution or strict-file wiring is broken.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-fixture-realism-output.txt: Address the concern above.

### FINDING_30: [OUT_OF_SCOPE] Checkpoint tests depend on earlier ORPHAN_TMP git initialization
- **Reviewer(s)**: dyn-fixture-realism-output.txt
- **Severity**: nit
- **Concern**: Some checkpoint cases depend on `ORPHAN_TMP` being `git init`’d earlier in the harness, making the tests fragile if reordered or split.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-fixture-realism-output.txt: Address the concern above.

### FINDING_31: [OUT_OF_SCOPE] Additional tmpdir cleanup hygiene issue
- **Reviewer(s)**: dyn-fixture-realism-output.txt
- **Severity**: nit
- **Concern**: The fixture-realism reviewer also notes that many `mkitmp()` / `_impl_g2` directories are not removed by the EXIT trap, treating it as harness hygiene rather than production correctness.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-fixture-realism-output.txt: Address the concern above.

### FINDING_32: [OUT_OF_SCOPE] Precondition case has weaker stderr-log assertion than ambiguity case
- **Reviewer(s)**: dyn-fixture-realism-output.txt
- **Severity**: nit
- **Concern**: The precondition case asserts `execution-issues.md` but not a non-empty `oos-disposition-checkpoint.stderr.log`, unlike the ambiguity case.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-fixture-realism-output.txt: Address the concern above.
