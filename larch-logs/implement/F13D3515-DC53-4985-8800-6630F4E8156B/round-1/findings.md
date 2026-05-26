### FINDING_1: risk-integration: skills/implement/SKILL.md:556-560
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Step 0 collapse removed token/timing ledger marks for tracking that test-implement-structure.sh still requires. make lint / test-implement-structure fails on grep for token-ledger and timing-ledger Step 0 tracking issue strings. Move marks into phase_tracking and retarget the structure test, or restore minimal SKILL marks without separate adoption scripts.
- **Suggested revision**: Address the concern above.

### FINDING_2: code-quality: scripts/implement-bootstrap.sh:321-322
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Only Step 0 preflight ledger marks remain; tracking issue sub-step marks were dropped. Timing and token reports no longer show a separate Step 0 tracking issue duration bucket. Add Step 0 tracking issue marks in phase_tracking on adoption paths, or document merged preflight timing and update report consumers.
- **Suggested revision**: Address the concern above.

### FINDING_3: code-quality: skills/implement/scripts/test-implement-bootstrap.sh:463-472
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] No harness case for Branch 1 larch-log init failure (plan F8). Regression in branch-1-resume init bail could ship undetected. Add sentinel resume case with LARCH_TEST_LARCH_LOG_FAIL=true asserting tracking-init-failed and preserved issue/run ids.
- **Suggested revision**: Address the concern above.

### FINDING_4: correctness: scripts/implement-bootstrap.sh:382-388
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Fork upstream context fetch requires both upstream repo and issue-number argv. Fork bootstrap without --issue-number skips get-issue-context despite best-effort fork semantics. Call get-issue-context with repo only when issue absent, or require issue-number for forked-target in die_usage.
- **Suggested revision**: Address the concern above.

### FINDING_5: code-quality: scripts/implement-bootstrap.sh:611-637
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Triplicated bail/stall guard before later phase stubs. Harder to maintain as plan/coder phases grow. Extract tracking_allows_later_phases helper used by plan/coder/all branches.
- **Suggested revision**: Address the concern above.

### FINDING_6: code-quality: scripts/implement-bootstrap.sh:2
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Stale Phase 1-only file header comment. Misleading for future editors. Update header to mention infra + tracking phases.
- **Suggested revision**: Address the concern above.

### FINDING_7: code-quality: scripts/implement-bootstrap.md:67-68
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Contradictory Future phases breadcrumb note. Doc readers may think tracking breadcrumbs are not shipped. Remove stale Future phases sentence.
- **Suggested revision**: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] architecture: docs/linting.md:238
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] test-implement-bootstrap doc still says calls 1-5 only. Operators misread harness coverage after Phase 2. Update linting.md when touching docs (not in this PR file list).
- **Suggested revision**: Address the concern above.

### FINDING_9: correctness: skills/implement/SKILL.md:410-618
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Bootstrap bail routing is prose-only; no bash gate before later Step 0 work. /implement on CLOSED issue: bootstrap exit 0 with IMPLEMENT_BAIL_REASON=adopted-issue-closed and ISSUE_NUMBER=123; orchestrator may still run snapshot-untracked and gh issue view per anti-halt sequential flow. Add foreground bash after KV parse: if IMPLEMENT_BAIL_REASON in {adopted-issue-closed,adopted-issue-is-pr,tracking-init-failed} or STALL_TRACKING=true then skip to Step 18 before plan materialization.
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

### FINDING_13: risk-integration: skills/implement/scripts/test-post-tracking-issue.sh:41-63
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] No --run-id or precedence-chain tests for post-tracking-issue.sh change. A regression in --run-id handling could ship while CI stays green; bootstrap would write wrong RUN_ID into parent-issue.md. Add harness cases for --run-id override invalid --run-id and missing RUN_ID; update test-post-tracking-issue.md.
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

### FINDING_18: risk-integration: skills/implement/scripts/test-implement-bootstrap.sh:556-575
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Edge-breadcrumb-count no longer tests dedicated LARCH_QUIET_BREADCRUMB_FD stream. Non-stdout breadcrumb FD regressions would not be caught in CI. Restore FD 9 (or separate) breadcrumb stream test in addition to FD 1.
- **Suggested revision**: Address the concern above.

### FINDING_19: risk-integration: skills/implement/scripts/test-implement-bootstrap.sh:326-472
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Tracking-phase breadcrumbs not counted when LARCH_QUIET_BREADCRUMBS=1. Wrong or duplicate tracking breadcrumb strings could reach operators unnoticed. Add tracking breadcrumb count cases for adopt and skip branches.
- **Suggested revision**: Address the concern above.

### FINDING_20: security: scripts/implement-bootstrap.sh:403-414
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] Sentinel ISSUE_NUMBER/RUN_ID are not newline- or format-validated before emit_kv and GitHub rename. A crafted parent-issue.md can embed a newline in ISSUE_NUMBER so bootstrap stdout contains a forged IMPLEMENT_BAIL_REASON line; the orchestrator KV scanner applies it and routes to Step 18 or skips work without a real closed issue. Reject sentinel values with \r \n or spaces; require numeric issue and valid_run_id before branch-1-resume; otherwise rm sentinel and fall through to Branch 2.
- **Suggested revision**: Address the concern above.

### FINDING_21: risk-integration: scripts/implement-bootstrap.sh:379-388
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Fork upstream context fetch is best-effort with || true. Failed gh fetch leaves empty upstream context files but the run continues under --forked, risking implementation against an incomplete upstream view. Emit UPSTREAM_CONTEXT_OK=false on failure and let SKILL abort or warn; or hard-bail when repo and issue were provided but fetch failed.
- **Suggested revision**: Address the concern above.

### FINDING_22: security: scripts/implement-bootstrap.sh:403-407
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Branch 1 mismatch check is gated on non-empty --issue-number. Omitting --issue-number while a sentinel exists resumes the sentinel issue number with no argv binding. Require --issue-number for Branch 1 or treat sentinel+empty argv as malformed.
- **Suggested revision**: Address the concern above.

### FINDING_23: [OUT_OF_SCOPE] security: scripts/get-issue-state.sh:46-57
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] get-issue-state.sh does not validate --issue as numeric. Direct invocation with metacharacters in --issue could reach gh if a future caller drops quoting. Mirror post-tracking-issue numeric validation.
- **Suggested revision**: Address the concern above.

### FINDING_24: [OUT_OF_SCOPE] security: scripts/tracking-issue-read.sh:269-278
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Sentinel parser does not validate ISSUE_NUMBER or RUN_ID format. Malformed sentinel values reach new phase_tracking logic until downstream tools fail. Add newline and charset validation in tracking-issue-read sentinel branch.
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

### FINDING_28: risk-integration: scripts/implement-bootstrap.sh:460-472
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] POSTED=false after successful larch-log init leaves orphan manifest without parent-issue.md sentinel. Deferred retry may create duplicate manifests or inconsistent RUN_ID across session retries. Document deferred orphan semantics or roll back manifest on POSTED failure.
- **Suggested revision**: Address the concern above.

### FINDING_29: architecture: scripts/implement-bootstrap.sh:382-388
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Fork upstream context fetch requires both upstream repo and issue argv; failures are silent. forked_target=true without --upstream-repo skips context fetch with no hard error despite SKILL requiring UPSTREAM_REPO from implement-fork-env. die_usage or loud stderr when forked without upstream repo; align bootstrap validation with Protocol preflight.
- **Suggested revision**: Address the concern above.

### FINDING_30: [OUT_OF_SCOPE] code-quality: scripts/implement-bootstrap.md:237
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Stale note claims tracking breadcrumbs are future work. Misleading operators reading contract doc only. Update breadcrumb section to list emitted tracking lines.
- **Suggested revision**: Address the concern above.

### FINDING_31: [OUT_OF_SCOPE] risk-integration: skills/implement/SKILL.md
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Removed Step 0 tracking token-ledger mark when collapsing tracking bash. Token reports may attribute Step 0 tracking work to preflight bucket only. Re-add mark inside phase_tracking or document intentional boundary shift.
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

### FINDING_37: [OUT_OF_SCOPE] **Bash 3.2 portability (scout checklist):** The new `[[ "$UPSTREAM_REPO_OPT" =~ ... ]]` check at `scripts/implement-bootstrap.sh:603` is acceptable on the macOS Bash 3.2 target (`=~` in `[[ ]]` since 3.0; not listed in `BASH_AUTHORING.md` / `scripts/lint-bash32.sh` forbidden constructs). No Bash 4+ tokens (`declare -A`, `mapfile`, `${var,,}`, `&>>`, etc.) appear in the new/changed bodies of `scripts/implement-bootstrap.sh`, `scripts/write-session-env.sh`, or `skills/implement/scripts/post-tracking-issue.sh`.
- **Reviewer**: dyn-bash-portability-output.txt
- **Concern**: - **Bash 3.2 portability (scout checklist):** The new `[[ "$UPSTREAM_REPO_OPT" =~ ... ]]` check at `scripts/implement-bootstrap.sh:603` is acceptable on the macOS Bash 3.2 target (`=~` in `[[ ]]` since 3.0; not listed in `BASH_AUTHORING.md` / `scripts/lint-bash32.sh` forbidden constructs). No Bash 4+ tokens (`declare -A`, `mapfile`, `${var,,}`, `&>>`, etc.) appear in the new/changed bodies of `scripts/implement-bootstrap.sh`, `scripts/write-session-env.sh`, or `skills/implement/scripts/post-tracking-issue.sh`.
- **Suggested revision**: Address the concern above.

### FINDING_38: [OUT_OF_SCOPE] **`run_larch_log_init` temp hygiene:** `init_err` from `mktemp` is removed on both failure (159) and success (163) paths before `tracking_init_failed` / `return`; `rename_to_implementing` uses a fixed `$IMPLEMENT_TMPDIR/tracking-rename.stderr.log` path (no `mktemp` leak despite plan prose mentioning a temp rename log).
- **Reviewer**: dyn-bash-portability-output.txt
- **Concern**: - **`run_larch_log_init` temp hygiene:** `init_err` from `mktemp` is removed on both failure (159) and success (163) paths before `tracking_init_failed` / `return`; `rename_to_implementing` uses a fixed `$IMPLEMENT_TMPDIR/tracking-rename.stderr.log` path (no `mktemp` leak despite plan prose mentioning a temp rename log).
- **Suggested revision**: Address the concern above.

### FINDING_39: [OUT_OF_SCOPE] **Exit-code capture:** `init_rc=$?` immediately follows the `init_out=$(... 2>"$init_err")` assignment with no intervening commands; stdout and stderr are not mixed in that call (stderr goes to `init_err` only).
- **Reviewer**: dyn-bash-portability-output.txt
- **Concern**: - **Exit-code capture:** `init_rc=$?` immediately follows the `init_out=$(... 2>"$init_err")` assignment with no intervening commands; stdout and stderr are not mixed in that call (stderr goes to `init_err` only).
- **Suggested revision**: Address the concern above.

### FINDING_40: [OUT_OF_SCOPE] **Pre-existing patterns in the same files:** `phase_infra` already uses the same `mktemp` + `rm -f` pattern for `gate_err` (203–226) without checking `mktemp` success; `write-session-env.sh` already uses multiple `[[ =~ ]]` validators unchanged by this branch’s `--forked-target` addition.
- **Reviewer**: dyn-bash-portability-output.txt
- **Concern**: - **Pre-existing patterns in the same files:** `phase_infra` already uses the same `mktemp` + `rm -f` pattern for `gate_err` (203–226) without checking `mktemp` success; `write-session-env.sh` already uses multiple `[[ =~ ]]` validators unchanged by this branch’s `--forked-target` addition.
- **Suggested revision**: Address the concern above.

### FINDING_41: **architecture** `skills/implement/SKILL.md:408-624` — Emit/parse alignment for the new tracking KVs is complete: `emit_final_tail` in `scripts/implement-bootstrap.sh:527-536` emits `ISSUE_NUMBER`, `RUN_ID`, `BRANCH_SELECTED`, `DEFERRED`, `STALL_TRACKING`, and `IMPLEMENT_BAIL_REASON`; `_ib_kv_scan` in `skills/implement/SKILL.md:389-394` parses all six; `export` at `skills/implement/SKILL.md:408` includes them. `emit_infra_kv_block` keys match the infra arm of the same scanner (`skills/implement/SKILL.md:371-388`). However, after the bootstrap Bash block ends, the skill flows straight into “Session untracked baseline” and “Plan materialization” (`skills/implement/SKILL.md:607-641`) with no Bash guard on `IMPLEMENT_BAIL_REASON` or `STALL_TRACKING`. The removed inline Step 0 blocks (see diff around old `get-issue-state.sh` / CLOSED / IS_PR paths) previously said “skip to Step 18” per failure; that enforcement now lives only in markdown tables (`skills/implement/SKILL.md:412-419`, `566-577`). An orchestrator that parses KVs correctly but does not apply the table can still run plan materialization on `adopted-issue-closed` or ignore `STALL_TRACKING=true` on `tracking-init-failed`—a silent protocol break at the consumer layer, amplified by this consolidation. **Suggested fix:** Add a mandatory Bash routing block immediately after the KV export (before `snapshot-untracked.sh`) that branches on `IMPLEMENT_BAIL_REASON` / `STALL_TRACKING` (e.g. `adopted-issue-closed` and `adopted-issue-is-pr` → Step 18; `tracking-init-failed` → Step 18 with `STALL_TRACKING` already set from stdout; empty bail + `DEFERRED=true` → continue), mirroring the bootstrap script’s own `main()` guard at `scripts/implement-bootstrap.sh:617-635`.
- **Reviewer**: dyn-kv-protocol-consistency-output.txt
- **Concern**: - **architecture** `skills/implement/SKILL.md:408-624` — Emit/parse alignment for the new tracking KVs is complete: `emit_final_tail` in `scripts/implement-bootstrap.sh:527-536` emits `ISSUE_NUMBER`, `RUN_ID`, `BRANCH_SELECTED`, `DEFERRED`, `STALL_TRACKING`, and `IMPLEMENT_BAIL_REASON`; `_ib_kv_scan` in `skills/implement/SKILL.md:389-394` parses all six; `export` at `skills/implement/SKILL.md:408` includes them. `emit_infra_kv_block` keys match the infra arm of the same scanner (`skills/implement/SKILL.md:371-388`). However, after the bootstrap Bash block ends, the skill flows straight into “Session untracked baseline” and “Plan materialization” (`skills/implement/SKILL.md:607-641`) with no Bash guard on `IMPLEMENT_BAIL_REASON` or `STALL_TRACKING`. The removed inline Step 0 blocks (see diff around old `get-issue-state.sh` / CLOSED / IS_PR paths) previously said “skip to Step 18” per failure; that enforcement now lives only in markdown tables (`skills/implement/SKILL.md:412-419`, `566-577`). An orchestrator that parses KVs correctly but does not apply the table can still run plan materialization on `adopted-issue-closed` or ignore `STALL_TRACKING=true` on `tracking-init-failed`—a silent protocol break at the consumer layer, amplified by this consolidation. **Suggested fix:** Add a mandatory Bash routing block immediately after the KV export (before `snapshot-untracked.sh`) that branches on `IMPLEMENT_BAIL_REASON` / `STALL_TRACKING` (e.g. `adopted-issue-closed` and `adopted-issue-is-pr` → Step 18; `tracking-init-failed` → Step 18 with `STALL_TRACKING` already set from stdout; empty bail + `DEFERRED=true` → continue), mirroring the bootstrap script’s own `main()` guard at `scripts/implement-bootstrap.sh:617-635`.
- **Suggested revision**: Address the concern above.

### FINDING_42: **architecture** `skills/implement/SKILL.md:414-419` — The compact “Bootstrap tracking bail routing” table covers all three script-emitted bail reasons (`adopted-issue-closed`, `adopted-issue-is-pr`, `tracking-init-failed` from `scripts/implement-bootstrap.sh:435-440` and `tracking_init_failed` at `138-141`), but it does not document the non-bail exit-2 path for unknown `STATE` (`scripts/implement-bootstrap.sh:442-444`), which is only described in the behavior map (`skills/implement/SKILL.md:577`) and exit-2 prose (`296-300`, `348-351`). That split is logically correct (no `IMPLEMENT_BAIL_REASON` on exit 2), yet an operator searching only the bail table may miss that `STATE=MERGED` (or any non-OPEN/non-CLOSED value) aborts via `STEP_FAILED=get-issue-state` rather than a bail token. **Suggested fix:** Add one row to the bail-routing table (or a sibling “exit 2” sub-table) stating “unknown/non-OPEN issue state → `STEP_FAILED=get-issue-state`, exit 2, abort Step 0” so all tracking outcomes are discoverable in one place.
- **Reviewer**: dyn-kv-protocol-consistency-output.txt
- **Concern**: - **architecture** `skills/implement/SKILL.md:414-419` — The compact “Bootstrap tracking bail routing” table covers all three script-emitted bail reasons (`adopted-issue-closed`, `adopted-issue-is-pr`, `tracking-init-failed` from `scripts/implement-bootstrap.sh:435-440` and `tracking_init_failed` at `138-141`), but it does not document the non-bail exit-2 path for unknown `STATE` (`scripts/implement-bootstrap.sh:442-444`), which is only described in the behavior map (`skills/implement/SKILL.md:577`) and exit-2 prose (`296-300`, `348-351`). That split is logically correct (no `IMPLEMENT_BAIL_REASON` on exit 2), yet an operator searching only the bail table may miss that `STATE=MERGED` (or any non-OPEN/non-CLOSED value) aborts via `STEP_FAILED=get-issue-state` rather than a bail token. **Suggested fix:** Add one row to the bail-routing table (or a sibling “exit 2” sub-table) stating “unknown/non-OPEN issue state → `STEP_FAILED=get-issue-state`, exit 2, abort Step 0” so all tracking outcomes are discoverable in one place.
- **Suggested revision**: Address the concern above.

### FINDING_43: [OUT_OF_SCOPE] architecture
- **Reviewer**: dyn-kv-protocol-consistency-output.txt
- **Concern**: - **architecture** `skills/implement/SKILL.md:336-353` — Exit-2 handling in the bootstrap Bash block still only special-cases `session-entry-gate`, `session-setup`, and `get-issue-state`; `scripts/implement-bootstrap.sh` can also exit 2 with `STEP_FAILED=create-branch` or `STEP_FAILED=write-session-env` (`198-199`, `318-319`). That predates the tracking phase and is unchanged by this branch.
- **Suggested revision**: Address the concern above.

### FINDING_44: [OUT_OF_SCOPE] architecture
- **Reviewer**: dyn-kv-protocol-consistency-output.txt
- **Concern**: - **architecture** `skills/implement/SKILL.md:30` — Load-bearing invariant #4 still describes `deferred=true` in prose while the wire protocol exports uppercase `DEFERRED`; the bootstrap behavior map uses `DEFERRED=true`. Harmless if the orchestrator uses parsed `DEFERRED`, but the mixed naming predates this branch’s table work.
- **Suggested revision**: Address the concern above.

