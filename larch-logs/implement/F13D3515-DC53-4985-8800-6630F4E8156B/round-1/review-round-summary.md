# Review Round 1

- Mode: `diff`
- 23 accepted, 9 rejected (8 exonerated)

## Accepted Findings

### FINDING_1: risk-integration: skills/implement/SKILL.md:556-560
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Step 0 collapse removed token/timing ledger marks for tracking that test-implement-structure.sh still requires. make lint / test-implement-structure fails on grep for token-ledger and timing-ledger Step 0 tracking issue strings. Move marks into phase_tracking and retarget the structure test, or restore minimal SKILL marks without separate adoption scripts.
- **Suggested revision**: Address the concern above.


### FINDING_10: correctness: scripts/implement-bootstrap.sh:523-525
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] emit_final_tail fallback emits ISSUE_NUMBER from argv on bail paths where BRANCH_SELECTED is empty. Downstream steps that test only non-empty ISSUE_NUMBER may treat a closed/PR bail as a successful adoption. Clear ISSUE_NUMBER on closed/PR bails or mandate IMPLEMENT_BAIL_REASON checks before any gh/plan Step 0 calls.
- **Suggested revision**: Address the concern above.


### FINDING_11: correctness: scripts/implement-bootstrap.sh:321-322
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Tracking-phase token/timing ledger marks removed; only preflight mark remains. Timing/token reports lose a distinct Step 0 tracking boundary vs pre-Phase-2 SKILL. Add tracking marks at end of phase_tracking success paths or document intentional merge into preflight.
- **Suggested revision**: Address the concern above.


### FINDING_12: code-quality: scripts/implement-bootstrap.sh:2
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Stale header comment still describes Phase 1 infra only. Misleading for maintainers reading the dispatcher entrypoint. Update top-of-file comment to include tracking phase.
- **Suggested revision**: Address the concern above.


### FINDING_14: risk-integration: skills/implement/scripts/test-implement-bootstrap.sh:426-472
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] F7 main() bail guard not tested under --up-to-phase plan or all. If guard regresses adopted-issue-closed becomes not-yet-implemented-phase-3 on plan boundary breaking SKILL bail routing. Add B2-plan-phase and B5-plan-phase cases asserting real bail reasons and absence of phase-3 stub overwrite.
- **Suggested revision**: Address the concern above.


### FINDING_15: risk-integration: skills/implement/scripts/test-implement-bootstrap.sh:341-352
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Branch 1 larch-log init failure (plan F8) untested. Branch-1 resume could stop setting tracking-init-failed while Branch 2 still passes B5. Add B5-branch1 with sentinel plus LARCH_TEST_LARCH_LOG_FAIL=true asserting branch-1-resume and stall KV.
- **Suggested revision**: Address the concern above.


### FINDING_16: risk-integration: skills/implement/scripts/test-implement-bootstrap.sh:326-324
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Empty RUN_ID derivation failure untested. Orchestrator without session-id could get silent wrong behavior vs documented tracking-init-failed bail. Add case with no --run-id no session-id empty token; assert tracking-init-failed and STALL_TRACKING=true.
- **Suggested revision**: Address the concern above.


### FINDING_17: risk-integration: skills/implement/scripts/test-implement-bootstrap.sh:247-256
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Rename failure best-effort path (plan F9) untested despite stub hook. rename_to_implementing or append-tool-failure wiring could break without CI signal. Add GP-adopt-rename-fail with LARCH_TEST_RENAME_FAILED=true; assert rc 0 and execution-issues log entry.
- **Suggested revision**: Address the concern above.


### FINDING_2: code-quality: scripts/implement-bootstrap.sh:321-322
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Only Step 0 preflight ledger marks remain; tracking issue sub-step marks were dropped. Timing and token reports no longer show a separate Step 0 tracking issue duration bucket. Add Step 0 tracking issue marks in phase_tracking on adoption paths, or document merged preflight timing and update report consumers.
- **Suggested revision**: Address the concern above.


### FINDING_20: security: scripts/implement-bootstrap.sh:403-414
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] Sentinel ISSUE_NUMBER/RUN_ID are not newline- or format-validated before emit_kv and GitHub rename. A crafted parent-issue.md can embed a newline in ISSUE_NUMBER so bootstrap stdout contains a forged IMPLEMENT_BAIL_REASON line; the orchestrator KV scanner applies it and routes to Step 18 or skips work without a real closed issue. Reject sentinel values with \r \n or spaces; require numeric issue and valid_run_id before branch-1-resume; otherwise rm sentinel and fall through to Branch 2.
- **Suggested revision**: Address the concern above.


### FINDING_25: correctness: skills/implement/SKILL.md:408-668
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Bootstrap emits empty ISSUE_NUMBER on repo-unavailable-skip but plan materialization still calls gh issue view "$ISSUE_NUMBER" without a repo_unavailable carve-out. After REPO_UNAVAILABLE=true, export clears ISSUE_NUMBER; gh issue view runs with empty issue or wrong repo, breaking local-only runs that already have plan text in PREFLIGHT_TMPDIR. Skip gh issue view when repo_unavailable=true or keep TARGET_ISSUE_NUMBER in tail for local-only context only.
- **Suggested revision**: Address the concern above.


### FINDING_26: risk-integration: skills/implement/SKILL.md:412-419
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Step 0 tracking bail routing is table-only after Bash collapse; no mechanical post-bootstrap guard on IMPLEMENT_BAIL_REASON or STALL_TRACKING. Anti-halt default continuation can reach plan materialization after adopted-issue-closed or tracking-init-failed despite documented skip-to-Step-18 routing. Add a foreground Bash gate after KV parse or restore explicit control-flow blocks per bail reason.
- **Suggested revision**: Address the concern above.


### FINDING_27: correctness: scripts/implement-bootstrap.sh:411-414
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] No harness case for Branch 1 larch-log init failure after sentinel resume. Branch-1 init fail preserves sentinel and sets STALL_TRACKING but behavior is untested; regression could resume with branch-1-resume while logs are missing. Add harness case: sentinel present + LARCH_TEST_LARCH_LOG_FAIL=true; assert stall flags and preserved ISSUE_NUMBER.
- **Suggested revision**: Address the concern above.


### FINDING_3: code-quality: skills/implement/scripts/test-implement-bootstrap.sh:463-472
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] No harness case for Branch 1 larch-log init failure (plan F8). Regression in branch-1-resume init bail could ship undetected. Add sentinel resume case with LARCH_TEST_LARCH_LOG_FAIL=true asserting tracking-init-failed and preserved issue/run ids.
- **Suggested revision**: Address the concern above.


### FINDING_32: correctness: skills/implement/scripts/post-tracking-issue.md:18
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Documented RUN_ID precedence omits LARCH_TOKEN_SESSION_ID required by plan F5. A standalone post-tracking-issue call without --run-id and without session-id but with LARCH_TOKEN_SESSION_ID in session-env would fail or document the wrong contract. Add session-env LARCH_TOKEN_SESSION_ID fallback in post-tracking-issue.sh and document the full four-step precedence chain.
- **Suggested revision**: Address the concern above.


### FINDING_33: correctness: scripts/implement-bootstrap.md:67
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Breadcrumb section contradicts itself about tracking breadcrumbs being future-only. Operators reading the contract may think tracking breadcrumbs are not yet shipped. Delete or narrow line 67 to Phase 3/4 breadcrumbs only.
- **Suggested revision**: Address the concern above.


### FINDING_34: correctness: skills/implement/scripts/test-implement-bootstrap.sh
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] F8 Branch 1 larch-log init failure is implemented but not harnessed. A regression breaking Branch 1 init-fail handling could ship while B5 still passes on Branch 2 only. Add a sentinel-resume + LARCH_TEST_LARCH_LOG_FAIL=true case asserting branch-1-resume stall semantics.
- **Suggested revision**: Address the concern above.


### FINDING_35: correctness: skills/implement/scripts/test-implement-bootstrap.sh:354-364
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] GP3 does not verify fork upstream context fetch. Removing get-issue-context invocation in fork mode would not fail CI. Assert upstream-context artifacts or stub invocation when fork flags and issue are set.
- **Suggested revision**: Address the concern above.


### FINDING_36: **correctness** `scripts/implement-bootstrap.sh:403-414` — Branch 1 resume treats any non-empty sentinel `RUN_ID` as usable, while Branch 2 explicitly gates with `valid_run_id` at lines 455–458. A hand-edited or corrupted sentinel whose `RUN_ID` contains spaces or characters outside `^[A-Za-z0-9._-]+$` still enters the Branch 1 path, fails inside `run_larch_log_init`, and surfaces `IMPLEMENT_BAIL_REASON=tracking-init-failed` with `STALL_TRACKING=true` instead of clearing the sentinel and falling through to Branch 2 re-adoption (the behavior used for other malformed sentinel cases at 416–418). **Suggested fix:** After assigning `RUN_ID=$sentinel_run_id`, call `valid_run_id "$RUN_ID"`; on failure, emit the same operator-visible warning used for malformed sentinels, `rm -f` the sentinel, and fall through to Branch 2 rather than calling `run_larch_log_init`.
- **Reviewer**: dyn-bash-portability-output.txt
- **Concern**: - **correctness** `scripts/implement-bootstrap.sh:403-414` — Branch 1 resume treats any non-empty sentinel `RUN_ID` as usable, while Branch 2 explicitly gates with `valid_run_id` at lines 455–458. A hand-edited or corrupted sentinel whose `RUN_ID` contains spaces or characters outside `^[A-Za-z0-9._-]+$` still enters the Branch 1 path, fails inside `run_larch_log_init`, and surfaces `IMPLEMENT_BAIL_REASON=tracking-init-failed` with `STALL_TRACKING=true` instead of clearing the sentinel and falling through to Branch 2 re-adoption (the behavior used for other malformed sentinel cases at 416–418). **Suggested fix:** After assigning `RUN_ID=$sentinel_run_id`, call `valid_run_id "$RUN_ID"`; on failure, emit the same operator-visible warning used for malformed sentinels, `rm -f` the sentinel, and fall through to Branch 2 rather than calling `run_larch_log_init`.
- **Suggested revision**: Address the concern above.


### FINDING_41: **architecture** `skills/implement/SKILL.md:408-624` — Emit/parse alignment for the new tracking KVs is complete: `emit_final_tail` in `scripts/implement-bootstrap.sh:527-536` emits `ISSUE_NUMBER`, `RUN_ID`, `BRANCH_SELECTED`, `DEFERRED`, `STALL_TRACKING`, and `IMPLEMENT_BAIL_REASON`; `_ib_kv_scan` in `skills/implement/SKILL.md:389-394` parses all six; `export` at `skills/implement/SKILL.md:408` includes them. `emit_infra_kv_block` keys match the infra arm of the same scanner (`skills/implement/SKILL.md:371-388`). However, after the bootstrap Bash block ends, the skill flows straight into “Session untracked baseline” and “Plan materialization” (`skills/implement/SKILL.md:607-641`) with no Bash guard on `IMPLEMENT_BAIL_REASON` or `STALL_TRACKING`. The removed inline Step 0 blocks (see diff around old `get-issue-state.sh` / CLOSED / IS_PR paths) previously said “skip to Step 18” per failure; that enforcement now lives only in markdown tables (`skills/implement/SKILL.md:412-419`, `566-577`). An orchestrator that parses KVs correctly but does not apply the table can still run plan materialization on `adopted-issue-closed` or ignore `STALL_TRACKING=true` on `tracking-init-failed`—a silent protocol break at the consumer layer, amplified by this consolidation. **Suggested fix:** Add a mandatory Bash routing block immediately after the KV export (before `snapshot-untracked.sh`) that branches on `IMPLEMENT_BAIL_REASON` / `STALL_TRACKING` (e.g. `adopted-issue-closed` and `adopted-issue-is-pr` → Step 18; `tracking-init-failed` → Step 18 with `STALL_TRACKING` already set from stdout; empty bail + `DEFERRED=true` → continue), mirroring the bootstrap script’s own `main()` guard at `scripts/implement-bootstrap.sh:617-635`.
- **Reviewer**: dyn-kv-protocol-consistency-output.txt
- **Concern**: - **architecture** `skills/implement/SKILL.md:408-624` — Emit/parse alignment for the new tracking KVs is complete: `emit_final_tail` in `scripts/implement-bootstrap.sh:527-536` emits `ISSUE_NUMBER`, `RUN_ID`, `BRANCH_SELECTED`, `DEFERRED`, `STALL_TRACKING`, and `IMPLEMENT_BAIL_REASON`; `_ib_kv_scan` in `skills/implement/SKILL.md:389-394` parses all six; `export` at `skills/implement/SKILL.md:408` includes them. `emit_infra_kv_block` keys match the infra arm of the same scanner (`skills/implement/SKILL.md:371-388`). However, after the bootstrap Bash block ends, the skill flows straight into “Session untracked baseline” and “Plan materialization” (`skills/implement/SKILL.md:607-641`) with no Bash guard on `IMPLEMENT_BAIL_REASON` or `STALL_TRACKING`. The removed inline Step 0 blocks (see diff around old `get-issue-state.sh` / CLOSED / IS_PR paths) previously said “skip to Step 18” per failure; that enforcement now lives only in markdown tables (`skills/implement/SKILL.md:412-419`, `566-577`). An orchestrator that parses KVs correctly but does not apply the table can still run plan materialization on `adopted-issue-closed` or ignore `STALL_TRACKING=true` on `tracking-init-failed`—a silent protocol break at the consumer layer, amplified by this consolidation. **Suggested fix:** Add a mandatory Bash routing block immediately after the KV export (before `snapshot-untracked.sh`) that branches on `IMPLEMENT_BAIL_REASON` / `STALL_TRACKING` (e.g. `adopted-issue-closed` and `adopted-issue-is-pr` → Step 18; `tracking-init-failed` → Step 18 with `STALL_TRACKING` already set from stdout; empty bail + `DEFERRED=true` → continue), mirroring the bootstrap script’s own `main()` guard at `scripts/implement-bootstrap.sh:617-635`.
- **Suggested revision**: Address the concern above.


### FINDING_6: code-quality: scripts/implement-bootstrap.sh:2
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Stale Phase 1-only file header comment. Misleading for future editors. Update header to mention infra + tracking phases.
- **Suggested revision**: Address the concern above.


### FINDING_7: code-quality: scripts/implement-bootstrap.md:67-68
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Contradictory Future phases breadcrumb note. Doc readers may think tracking breadcrumbs are not shipped. Remove stale Future phases sentence.
- **Suggested revision**: Address the concern above.


### FINDING_9: correctness: skills/implement/SKILL.md:410-618
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Bootstrap bail routing is prose-only; no bash gate before later Step 0 work. /implement on CLOSED issue: bootstrap exit 0 with IMPLEMENT_BAIL_REASON=adopted-issue-closed and ISSUE_NUMBER=123; orchestrator may still run snapshot-untracked and gh issue view per anti-halt sequential flow. Add foreground bash after KV parse: if IMPLEMENT_BAIL_REASON in {adopted-issue-closed,adopted-issue-is-pr,tracking-init-failed} or STALL_TRACKING=true then skip to Step 18 before plan materialization.
- **Suggested revision**: Address the concern above.


