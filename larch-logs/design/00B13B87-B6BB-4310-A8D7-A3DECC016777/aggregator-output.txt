### FINDING_1: Revise failures are treated as successful revisions
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Edge, Codex-Edge, Cursor-Innovation, Codex-Innovation, Cursor-Requirements, Codex-Requirements, Cursor-dyn-loop-state-ordering, Codex-dyn-loop-state-ordering
- **Severity**: important
- **Concern**: The loop checks the revise helper's process exit code, but the helper can report logical failures through `REVISE_STATUS=failed-*` while exiting 0. Failed revisions can therefore be counted as applied, allowing convergence or cap-hit with an unchanged restored plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch, Codex-Arch: Parse REVISE_STATUS from stdout and require ok; treat failed-no-patch, failed-validation, and failed-apply as LOOP_STATUS=revision-failed
  - From Cursor-Edge, Codex-Edge: Parse revise stdout, require REVISE_STATUS=ok for success, branch revision-failed on any failed-* status, and add a regression where the helper exits 0 with REVISE_STATUS=failed-no-patch
  - From Cursor-Innovation, Codex-Innovation: Parse revise stdout, require REVISE_STATUS=ok, and treat any failed-* status as LOOP_STATUS=revision-failed; update tests to stub rc=0 plus failed status
  - From Cursor-Requirements, Codex-Requirements: Parse REVISE_STATUS=ok from revise stdout or change revise-plan-with-waterfall.sh to exit nonzero on failed-*; add tests for failed-no-patch and failed-validation
  - From Cursor-dyn-loop-state-ordering, Codex-dyn-loop-state-ordering: Parse revise-plan-with-waterfall.sh stdout, branch on REVISE_STATUS != ok, and add a test where the helper exits 0 with REVISE_STATUS=failed-no-patch

### FINDING_2: Revise artifact path conflicts with publish allowlist
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Edge, Codex-Edge, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Concern**: The revise helper writes forensics under `plan-review/round-N/revise/*`, while the proposed publisher contract disallows that nested subtree. Any successful auto-revise round can cause final design-log publishing to fail closed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch, Codex-Arch: Choose one layout and update both sides: either move revise output to DESIGN_TMPDIR/revise/round-N or explicitly allow a constrained round-N/revise allowlist
  - From Cursor-Edge, Codex-Edge: Either update revise-plan-with-waterfall.sh and its md/tests to write under DESIGN_TMPDIR/revise/round-N, or allow a constrained round-N/revise allowlist in design-log-publish and document it
  - From Cursor-Innovation, Codex-Innovation: Choose one contract: either allow a constrained round-N/revise allowlist in design-log-publish.sh, or change the revise helper output dir and add explicit publishing support for that subtree
  - From Cursor-Pragmatic, Codex-Pragmatic: Update revise-plan-with-waterfall.sh and its md sibling to write forensics under DESIGN_TMPDIR/revise/round-N, or allow a constrained nested revise allowlist in design-log-publish.sh; make the plan choose one concrete contract
  - From Cursor-Requirements, Codex-Requirements: Add UPDATED revise-plan-with-waterfall.sh to move revise forensics to DESIGN_TMPDIR/revise/round-N, or allow a constrained revise subdir in publisher; align snapshot and integration tests

### FINDING_3: Accepted OOS artifacts are overwritten across rounds
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Edge, Codex-Edge, Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Concern**: Per-round tally output overwrites root OOS artifacts, and Step 5b reads only the final top-level file. Accepted OOS items from earlier rounds can disappear before issue filing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch, Codex-Arch: Add an accumulated accepted-OOS artifact across internal rounds and make Step 5b read it, with stable IDs or round-qualified IDs
  - From Cursor-Edge, Codex-Edge: Define and test a cross-round OOS union artifact, dedupe OOS IDs across rounds, and make Step 5b consume the union after the loop
  - From Cursor-Requirements, Codex-Requirements: Maintain cumulative loop-level OOS and rejected artifacts or merge per-round snapshots into the root artifacts before Step 4 and Step 5b; add regression coverage

### FINDING_4: Auto-applied revisions skip the post-apply validation pipeline
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Codex-Innovation, Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Concern**: Moving revision application into the loop bypasses Gate B's shared post-apply checks, including duplicate sweep, validator dispatch, and Step 2b.5 size/decomposition gates. A revised final plan can proceed without validations that previously ran after applied findings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch, Codex-Arch: Factor the post-revision pipeline into a scriptable helper and call it after successful auto-revise, at least before Step 3b on the final loop result
  - From Cursor-Innovation, Codex-Innovation: Run the shared post-apply pipeline once after the final successful auto-apply, or factor it into a script and invoke it from passive Gate B before Step 3b
  - From Cursor-Requirements, Codex-Requirements: Add the shared post-apply pipeline after every successful loop revision or before passive Gate B continues; test validator and Step 2b.5 execution after loop auto-apply

### FINDING_5: Single-pass compatibility contract conflicts with cap and convergence logic
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Edge, Codex-Edge, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements, Cursor-dyn-kv-surface-sync, Codex-dyn-kv-surface-sync
- **Severity**: important
- **Concern**: The plan promises backward-compatible `LOOP_STATUS=complete` behavior when `--round-cap` is omitted, but the new pseudocode can auto-apply and emit `converged` or `cap-hit` instead. Existing single-pass callers may observe new statuses and side effects despite the compatibility claim.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch, Codex-Arch: Track whether --round-cap was explicitly supplied; define legacy single-pass behavior separately, including whether revise runs and when complete is emitted
  - From Cursor-Edge, Codex-Edge: Add an explicit ROUND_CAP_ARG_SEEN/single_pass_mode contract: omitted --round-cap ignores env and preserves old complete/no-auto-loop behavior, while SKILL.md passes explicit production caps
  - From Cursor-Innovation, Codex-Innovation: Track whether --round-cap was explicitly provided; in omitted-cap single-pass mode preserve LOOP_STATUS=complete and current artifact behavior
  - From Cursor-Pragmatic, Codex-Pragmatic: Introduce an explicit legacy_single_pass mode when --round-cap is omitted, or remove the compatibility promise and update all tests/docs/callers to the new status and auto-apply semantics
  - From Cursor-Requirements, Codex-Requirements: Define the exact legacy-mode branch for omitted --round-cap, or remove complete from the contract and update all callers and tests
  - From Cursor-dyn-kv-surface-sync, Codex-dyn-kv-surface-sync: Add an explicit single_pass_compat flag set when --round-cap is omitted. In that mode, keep the current complete emissions for normal and empty single-pass exits, and document exactly when complete can still appear in plan-review-loop.md and the tests.

### FINDING_6: New integration harness is not wired into Makefile checks
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Concern**: The plan adds `scripts/test-design-multi-round-integration.sh` and treats it as acceptance coverage, but omits Makefile wiring needed for `.PHONY`, targets, and lint/test shards.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch, Codex-Arch: Add ### UPDATED: Makefile to the plan and specify the target plus test-harness shard wiring
  - From Cursor-Pragmatic, Codex-Pragmatic: Add Makefile to the plan with a phony test-design-multi-round-integration target and shard wiring; update docs/linting.md if target docs are expected
  - From Cursor-Requirements, Codex-Requirements: Add UPDATED: Makefile, wire test-design-multi-round-integration into a harness shard and .PHONY list, and update scripts/relevant-checks.sh if scoped checks must select it

### FINDING_7: Stale-round cleanup uses unchecked rm -rf path
- **Reviewer(s)**: Cursor-Edge, Codex-Edge
- **Severity**: important
- **Concern**: Proposed cleanup deletes `"$DESIGN_TMPDIR/plan-review/round-"*` without first validating that `plan-review` is a safe directory under the session tree. A symlink or swapped path could cause deletion outside the intended tempdir.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge, Codex-Edge: Before cleanup, reject symlink/non-directory plan-review paths, resolve the physical root, and delete only validated child directories under that root

### FINDING_8: Round summary schema is insufficient and can be stale
- **Reviewer(s)**: Cursor-Edge, Codex-Edge, Cursor-dyn-loop-state-ordering, Codex-dyn-loop-state-ordering, Cursor-dyn-kv-surface-sync, Codex-dyn-kv-surface-sync
- **Severity**: important
- **Concern**: `round-summary.env` omits loop outcome fields that passive Gate B needs, and it may be written before final degraded-state mutations such as revision failure. Gate B can therefore render incomplete or contradictory per-round summaries.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge, Codex-Edge: Add LOOP_STATUS, REASON, CONVERGENCE_STREAK, REVISE_STATUS, and revise tier/status fields to round-summary.env; write the final per-round state after revision outcome is known
  - From Cursor-dyn-loop-state-ordering, Codex-dyn-loop-state-ordering: Move DEGRADED_PANEL=1 before _write_round_summary on the revision-failed branch, then write the summary once after the final round status is known
  - From Cursor-dyn-kv-surface-sync, Codex-dyn-kv-surface-sync: Extend round-summary.env to include LOOP_STATUS, REASON, and CONVERGENCE_STREAK. Write the summary only after final status and degraded-panel mutations are complete, especially on revision-failed.

### FINDING_9: Manual Gate B contract is contradicted by inner-loop auto-apply
- **Reviewer(s)**: Cursor-Innovation, Codex-Innovation
- **Severity**: important
- **Concern**: Manual Gate B mode promises user choice over applying accepted findings, but unconditional inner-loop auto-apply can apply those findings before Gate B presents manual decisions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation, Codex-Innovation: Either disable inner-loop auto-apply when manual_gate_b=true, or explicitly make manual mode incompatible with multi-round auto-apply and change the prompt/contract

### FINDING_10: Tally errors can reuse stale accepted findings
- **Reviewer(s)**: Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic
- **Severity**: important
- **Concern**: The loop lacks an early `tally-error` branch before accepted-count, convergence, and revision logic. If tally fails before truncating accepted artifacts, a later round can count or re-apply stale findings from an earlier round.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation, Codex-Innovation: Clear session-root review artifacts at the start of each round or use round-scoped files, and branch on TALLY_PLAN_REVIEW_STATUS=tally-error before accepted-count, convergence, or revise
  - From Cursor-Pragmatic, Codex-Pragmatic: After each round, branch on TALLY_PLAN_REVIEW_STATUS=tally-error before snapshot/revise/convergence; emit KVs that let SKILL.md roll back review-round-count.txt and do not consume stale accepted artifacts

### FINDING_11: Main-agent vote path is not integrated with multi-round state
- **Reviewer(s)**: Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Concern**: The main-agent vote-required path remains outside the new auto-apply loop semantics. In later rounds or zero-external-voter cases, accepted findings may be written to the wrong classification path or may not have a defined route back into revision, loop resumption, or Gate B.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic, Codex-Pragmatic: Update the main-agent-vote-required path to pass --findings-classification-out "$DESIGN_TMPDIR/plan-review/round-$ROUNDS_COMPLETED/findings-classification.tsv" and define whether post-main-agent accepted findings are auto-applied or handled by Gate B
  - From Cursor-Requirements, Codex-Requirements: After main-agent tally, either call the revise helper and resume/exit the loop by the same rules, or explicitly document and test a manual Gate B exception

### FINDING_12: Dedup failure state is not reset per round
- **Reviewer(s)**: Cursor-Pragmatic, Codex-Pragmatic
- **Severity**: latent
- **Concern**: `_dedup_failed` remains global across internal rounds. A dedup failure in one round can mark later clean rounds degraded, breaking convergence streaks and forcing avoidable cap-hit behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic, Codex-Pragmatic: Move _dedup_failed initialization inside _run_plan_review_round before dedup runs, and add a regression where only the first round dedup fails

### FINDING_13: Zero-findings convergence can mask broken collection
- **Reviewer(s)**: Cursor-dyn-loop-state-ordering, Codex-dyn-loop-state-ordering
- **Severity**: important
- **Concern**: Zero-findings convergence is gated only on readable panel paths, not evidence that reviewer collection succeeded. A broken collector can produce empty findings and be misreported as clean convergence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-loop-state-ordering, Codex-dyn-loop-state-ordering: Track COLLECT_OK_COUNT and COLLECT_FAILURE_COUNT in _run_plan_review_round; allow zero-findings convergence only when collector evidence proves reviewers actually completed, and add a broken-collector zero-findings regression test

### FINDING_14: New loop KVs are parsed but not behaviorally specified
- **Reviewer(s)**: Cursor-dyn-kv-surface-sync, Codex-dyn-kv-surface-sync
- **Severity**: important
- **Concern**: The plan emits and documents `IMPORTANT_ACCEPTED_COUNT`, `CONVERGENCE_STREAK`, and `REASON`, but SKILL.md only promises parsing and branches primarily on `LOOP_STATUS`. Gate B behavior and warning text cannot reliably use these fields without a defined branch matrix and validation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-kv-surface-sync, Codex-dyn-kv-surface-sync: Add an explicit SKILL.md branch matrix for LOOP_STATUS plus REASON, IMPORTANT_ACCEPTED_COUNT, and CONVERGENCE_STREAK. Include the keys in the Bash case parser, initialize them, validate expected enum/range values, and define how each affects Gate B mode and warning text.

### FINDING_15: Parsed loop result is not durably handed off after the Bash fence
- **Reviewer(s)**: Cursor-dyn-kv-surface-sync, Codex-dyn-kv-surface-sync
- **Severity**: important
- **Concern**: SKILL.md parses loop KVs inside a Bash fence, but later prompt-side prose cannot rely on shell locals after the fence exits. Without a durable normalized result, subsequent Gate B branching can lose `LOOP_STATUS`, `REASON`, and related state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-kv-surface-sync, Codex-dyn-kv-surface-sync: Write a normalized env file such as $DESIGN_TMPDIR/.step3-plan-review-result.env and/or print the canonical parsed KVs after validation. Have later SKILL.md prose and Gate B read that durable result instead of relying on shell locals lost at fence exit.

### FINDING_16: Duplicate allowlist functions lack a shared ownership contract
- **Reviewer(s)**: Cursor-dyn-allowlist-drift-contract, Codex-dyn-allowlist-drift-contract
- **Severity**: important
- **Concern**: The plan introduces separate allowlist functions for loop snapshots and publishing without a shared source or update procedure. Future artifact changes can update only one side, causing publish failures or silent drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-allowlist-drift-contract, Codex-dyn-allowlist-drift-contract: Make one shared allowlist helper or generated list used by both scripts; if duplication remains, document that additions/removals are owned by the plan-review-loop contract and require synchronized edits to both scripts, both sibling docs, and the drift test in the same change

### FINDING_17: findings-classification.tsv contract is ambiguous
- **Reviewer(s)**: Cursor-dyn-allowlist-drift-contract, Codex-dyn-allowlist-drift-contract
- **Severity**: important
- **Concern**: `findings-classification.tsv` is described both as a canonical loop snapshot artifact and as a publish-only back-compat superset item. The loop and publish allowlists can diverge because the intended ownership is unclear.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-allowlist-drift-contract, Codex-dyn-allowlist-drift-contract: Choose and document one contract: either findings-classification.tsv remains a canonical loop-produced artifact, or it is legacy publish-only; update the loop allowlist, publish allowlist, docs, and golden fixtures to make that asymmetry explicit

### FINDING_18: Publish integration test does not assert exact artifact parity
- **Reviewer(s)**: Cursor-dyn-allowlist-drift-contract, Codex-dyn-allowlist-drift-contract
- **Severity**: important
- **Concern**: The proposed integration test checks selected expected and forbidden files, but not the exact source-to-published `plan-review` file set. It can miss extra allowed files or loop artifacts absent from the publish fixture.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-allowlist-drift-contract, Codex-dyn-allowlist-drift-contract: Build the integration test from actual loop output, publish that same tmpdir, and compare sorted relative file lists exactly after documented legacy exceptions; also assert the unknown-file case leaves PUBLISH_OK=false and no staged plan-review artifact
