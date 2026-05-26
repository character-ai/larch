### FINDING_1: code-quality: skills/implement/SKILL.md:579-594
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Bootstrap mark_tracking_ledgers and SKILL both call token/timing mark Step 0 — tracking issue. Successful adopt/resume runs get duplicate ledger marks; timing segments collapse. Keep rehydrate in SKILL; remove duplicate marks from one side and update structure lint to match.
- **Suggested revision**: Address the concern above.

### FINDING_2: correctness: skills/implement/SKILL.md:579-594
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Post-bootstrap ledger block is unconditional. Fork/repo-unavailable/bail paths still record tracking-issue ledger marks without adoption. Gate marks on BRANCH_SELECTED or bail flags; align with bootstrap skip semantics.
- **Suggested revision**: Address the concern above.

### FINDING_3: code-quality: scripts/implement-bootstrap.sh:481-488
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] mark_tracking_ledgers runs when POSTED=false (DEFERRED). Ledger shows tracking milestone without sentinel/rename/summary. Call mark_tracking_ledgers only after successful post or use a distinct deferred label.
- **Suggested revision**: Address the concern above.

### FINDING_4: architecture: skills/implement/SKILL.md:412-427
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Mandatory routing guard is comment-only case. Agents can run tracking ledger and later Step 0 blocks after bail. Add enforceable skip/exit or mirror plan-materialization skip guards before tracking block.
- **Suggested revision**: Address the concern above.

### FINDING_5: code-quality: skills/implement/scripts/test-implement-bootstrap.md:10-30
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Harness sibling doc missing round-1 cases. Operators miss coverage for phase-skip and malformed-run-id paths. Sync case table with test-implement-bootstrap.sh.
- **Suggested revision**: Address the concern above.

### FINDING_6: code-quality: skills/implement/SKILL.md:603
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Fork table omits --issue-number requirement for get-issue-context. Doc readers expect repo-only upstream fetch. Update SKILL table or relax bootstrap guard consistently.
- **Suggested revision**: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] code-quality: scripts/test-implement-structure.sh:332-351
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Structure test mandates SKILL-side tracking ledger marks. Blocks bootstrap-only ledger ownership. Update when resolving duplicate-mark finding.
- **Suggested revision**: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] code-quality: scripts/implement-bootstrap.sh:112-115
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] kv_value_from_block uses $1==key not anchored /^KEY=/. Unlikely with current helpers; fragile if output format drifts. Optionally align with F19 anchored awk pattern.
- **Suggested revision**: Address the concern above.

### FINDING_9: correctness: scripts/implement-bootstrap.sh:146-149,427,487,492 and skills/implement/SKILL.md:590-591
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Duplicate Step 0 tracking ledger marks: bootstrap mark_tracking_ledgers plus SKILL still marks after bootstrap. Successful Branch 2 adopt records two timing/token marks for the same milestone; Step 0 timing reports are wrong. Keep marks in one place only: remove SKILL marks or remove bootstrap mark_tracking_ledgers on success paths.
- **Suggested revision**: Address the concern above.

### FINDING_10: correctness: scripts/implement-bootstrap.sh:481-488
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] mark_tracking_ledgers runs when POSTED!=true and DEFERRED=true. Metadata post fails but ledgers show tracking adoption completed; contradicts DEFERRED and no sentinel. Omit mark_tracking_ledgers on the deferred branch or use a distinct mark label for deferred metadata.
- **Suggested revision**: Address the concern above.

### FINDING_11: architecture: skills/implement/SKILL.md:412-426,579-594
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Bail routing case block is comment-only; later Bash blocks are not shell-gated. Orchestrator executing all fenced blocks may ledger-mark and continue Step 0 after adopted-issue-closed bail. Wrap post-bootstrap Step 0 bash in a shell case guard on IMPLEMENT_BAIL_REASON and STALL_TRACKING.
- **Suggested revision**: Address the concern above.

### FINDING_12: correctness: scripts/implement-bootstrap.sh:395-402
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Fork get-issue-context requires both upstream repo and issue-number argv. Forked bootstrap with repo but no issue skips upstream fetch; plan/design note is untested. Add harness case or document that both flags are mandatory for the fetch.
- **Suggested revision**: Address the concern above.

### FINDING_13: risk-integration: skills/implement/scripts/test-implement-bootstrap.md:10-30
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Harness sibling case table omits seven round-1 cases (B2-plan B5-all B5-plan B5-branch1 B-sentinel-invalid-run-id B-empty-run-id-derivation GP-adopt-rename-fail). Maintainers or CI triage assume incomplete coverage; plan F13 doc parity fails. Add a table row for every # --- case block in test-implement-bootstrap.sh.
- **Suggested revision**: Address the concern above.

### FINDING_14: risk-integration: skills/implement/scripts/test-post-tracking-issue.sh:41-63
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] No test for new --run-id flag or precedence in real post-tracking-issue.sh. A change breaking --run-id > sentinel > session-id precedence ships with green make test-post-tracking-issue while bootstrap stub still passes. Add --run-id override invalid-arg and fallback cases to test-post-tracking-issue.sh.
- **Suggested revision**: Address the concern above.

### FINDING_15: risk-integration: scripts/implement-bootstrap.sh:654-657
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Non-OPEN non-CLOSED STATE exits 2 with STEP_FAILED=get-issue-state but harness never sets non-OPEN non-CLOSED STATE. If get-issue-state.sh ever returns an unexpected STATE gh may change behavior without harness failure. Add B7-non-open-state stub case expecting rc 2 and STEP_FAILED=get-issue-state.
- **Suggested revision**: Address the concern above.

### FINDING_16: risk-integration: scripts/implement-bootstrap.sh:812-825
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] New argv validators lack negative harness cases. Invalid --run-id or --upstream-repo might regress to silent wrong behavior without a failing test. Add die_usage exit-2 cases for invalid fork run-id and upstream-repo flags.
- **Suggested revision**: Address the concern above.

### FINDING_17: risk-integration: skills/implement/scripts/test-implement-bootstrap.sh:592-600
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Branch 1 rename failure path untested. Resume path rename regression only surfaces in production not in GP-adopt-rename-fail. Add GP2 + LARCH_TEST_RENAME_FAILED=true expecting exit 0 and execution-issues log line.
- **Suggested revision**: Address the concern above.

### FINDING_18: risk-integration: skills/implement/scripts/test-implement-bootstrap.sh:660-678
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Tracking breadcrumbs not covered by Edge-breadcrumb-count. Tracking breadcrumb duplication or absence on adopted runs is undetected. Add breadcrumb-count case on GP-adopt with LARCH_QUIET_BREADCRUMBS=1.
- **Suggested revision**: Address the concern above.

### FINDING_19: [OUT_OF_SCOPE] risk-integration: scripts/test-session-env-roundtrip.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] FORKED_TARGET not in session-env roundtrip harness. Fork flag validation bugs outside bootstrap path may slip through. Optional --forked-target cases in test-session-env-roundtrip.sh.
- **Suggested revision**: Address the concern above.

### FINDING_20: risk-integration: scripts/implement-bootstrap.sh:392-404
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Fork tracking skips hard-fail on upstream context fetch failure. /implement --forked can continue after gh/jq failure with no upstream title/body files while plan preflight already ran; agent may implement against incomplete fork context. Restore fail-closed on get-issue-context failure or set a bail when upstream context files are missing after fork skip.
- **Suggested revision**: Address the concern above.

### FINDING_21: security: scripts/implement-bootstrap.sh:416-429
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Branch 1 resume omits argv/sentinel issue match when --issue-number is empty. Stale parent-issue.md can resume and rename a different GitHub issue than the operator invoked. Require --issue-number for Branch 1 or refuse resume when argv issue is empty but sentinel exists.
- **Suggested revision**: Address the concern above.

### FINDING_22: security: scripts/implement-bootstrap.sh:407-433
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] rm -f on parent-issue.md is symlink-unsafe under tmpdir swap attacks. Writer in shared or compromised tmpdir can cause rm -f to delete arbitrary user-writable paths. Verify regular file under IMPLEMENT_TMPDIR before rm or use hardened sentinel creation.
- **Suggested revision**: Address the concern above.

### FINDING_23: risk-integration: scripts/implement-bootstrap.sh:392-402
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Fork mode does not require --upstream-repo at bootstrap argv layer. Orchestrator misconfiguration skips get-issue-context silently while fork flow continues. die_usage or bail when FORKED_TARGET=true and UPSTREAM_REPO_OPT is empty.
- **Suggested revision**: Address the concern above.

### FINDING_24: [OUT_OF_SCOPE] security: skills/implement/scripts/post-tracking-issue.sh:50-51
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] --implement-tmpdir lacks path hardening. Direct script invocation with crafted path can write sentinel outside session dir. Reuse write-session-env-style absolute path and character validation.
- **Suggested revision**: Address the concern above.

### FINDING_25: correctness: scripts/implement-bootstrap.sh:418-429
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Branch 1 mismatch guard requires non-empty --issue-number Stale sentinel #100 resumed when bootstrap omits --issue-number while operator targets #200 Wire mismatch check to mandatory target or fail closed when sentinel exists without argv issue
- **Suggested revision**: Address the concern above.

### FINDING_26: risk-integration: scripts/implement-bootstrap.sh:484-488
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] DEFERRED post-failure calls mark_tracking_ledgers Metadata post fails but ledgers record a completed tracking mark Skip ledger marks on DEFERRED/defer mark to orchestrator-only after confirmed POSTED=true
- **Suggested revision**: Address the concern above.

### FINDING_27: risk-integration: skills/implement/SKILL.md:579-593
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] SKILL duplicates Step 0 tracking ledger marks after bootstrap Success and deferred paths get duplicate token/timing marks Remove duplicate marks or gate on DEFERRED=false and empty bail
- **Suggested revision**: Address the concern above.

### FINDING_28: risk-integration: skills/implement/SKILL.md:412-426
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Routing guard case is comment-only Agent may run tracking/plan bash after adopted-issue-closed bail Emit and gate on a machine SKIP flag from bootstrap KV
- **Suggested revision**: Address the concern above.

### FINDING_29: correctness: scripts/implement-bootstrap.sh:395-401
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Fork upstream context skipped unless repo and issue both set forked_target with repo but no issue-number silently skips context fetch Warn or fail when fork mode lacks required upstream inputs
- **Suggested revision**: Address the concern above.

### FINDING_30: risk-integration: scripts/implement-bootstrap.sh:462-488
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] DEFERRED path keeps BRANCH_SELECTED=branch-2-adopt and ISSUE_NUMBER set Parser treats adopt complete despite missing sentinel and DEFERRED=true Use branch-2-deferred token or adjust ISSUE_NUMBER tail when deferred without sentinel
- **Suggested revision**: Address the concern above.

### FINDING_31: architecture: skills/implement/SKILL.md:412-417
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] tracking-init-failed shares routing case arm with non-stall bails Future edit to STALL_TRACKING default could affect wrong bail class Split case arms per bail reason
- **Suggested revision**: Address the concern above.

### FINDING_32: [OUT_OF_SCOPE] architecture: skills/implement/SKILL.md:412-660
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Step 0 routing is agent-prescribed not shell-enforced Agent continues past bail despite KV signals Add mechanical skip flags (pre-existing pattern)
- **Suggested revision**: Address the concern above.

### FINDING_33: [OUT_OF_SCOPE] code-quality: skills/implement/scripts/test-implement-bootstrap.sh
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit]  Missing tests for non-OPEN STATE exit 2 and Branch 1 without argv Add harness cases for documented edge paths
- **Suggested revision**: Address the concern above.

### FINDING_34: correctness: scripts/implement-bootstrap.sh:146-148,427,487-492; skills/implement/SKILL.md:590-591
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] phase_tracking and SKILL.md both mark Step 0 tracking ledgers Normal adopt/resume runs record two identical token/timing boundaries and diverge from the plan's absorbed calls #6-9 scope Remove mark_tracking_ledgers from implement-bootstrap.sh (and adjust GP-adopt invoke-log tests); keep a single post-bootstrap mark block in SKILL.md
- **Suggested revision**: Address the concern above.

### FINDING_35: correctness: skills/implement/SKILL.md:575-593
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Prose says tracking is fully bootstrap-owned while a separate fenced block still marks ledgers Contributors may re-add prompt-side adoption scripts or duplicate ledger work alongside bootstrap Clarify that only calls #6-9 moved into bootstrap; ledger marks stay as one orchestrator-only fenced block after KV parse
- **Suggested revision**: Address the concern above.

### FINDING_36: architecture: skills/implement/scripts/test-implement-bootstrap.md:12-30
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Sibling harness doc omits round-1 test cases present in the shell harness Maintainers cannot see full regression coverage from the contract file alone Add rows for B2-plan, B5-all, B5-plan, B5-branch1, B-sentinel-invalid-run-id, B-empty-run-id-derivation, and GP-adopt-rename-fail
- **Suggested revision**: Address the concern above.

### FINDING_37: **correctness** `skills/implement/scripts/test-implement-bootstrap.sh:471-485` — B4’s “no sentinel” check is vacuous on the current fixture: the run starts with no `parent-issue.md`, the `post-tracking-issue.sh` stub only writes the sentinel when `LARCH_TEST_POSTED=true`, and `phase_tracking`’s `rm -f "$sentinel"` (see `scripts/implement-bootstrap.sh:484-486`) is therefore never exercised. A regression that dropped the `rm -f` while leaving the stub unchanged would still pass B4. The sentinel path (`$IMPLEMENT_TMPDIR/parent-issue.md`, i.e. `$SANDBOX_TMP/parent-issue.md`) matches production, but the case does not prove cleanup of a stale sentinel after `POSTED=false`. **Suggested fix:** Seed a deliberately wrong `parent-issue.md` before invoking B4 (e.g. `ISSUE_NUMBER=999` / `RUN_ID=stale`), keep `LARCH_TEST_POSTED=false`, and assert the file is absent afterward (or replaced only after a later successful post). Optionally add `assert_contains "DEFERRED=true"` plus `assert_not_contains "STALL_TRACKING=true"` and `assert_not_contains "IMPLEMENT_BAIL_REASON=tracking-init-failed"` to lock the deferred (non-stall) path.
- **Reviewer**: dyn-test-contract-output.txt
- **Concern**: - **correctness** `skills/implement/scripts/test-implement-bootstrap.sh:471-485` — B4’s “no sentinel” check is vacuous on the current fixture: the run starts with no `parent-issue.md`, the `post-tracking-issue.sh` stub only writes the sentinel when `LARCH_TEST_POSTED=true`, and `phase_tracking`’s `rm -f "$sentinel"` (see `scripts/implement-bootstrap.sh:484-486`) is therefore never exercised. A regression that dropped the `rm -f` while leaving the stub unchanged would still pass B4. The sentinel path (`$IMPLEMENT_TMPDIR/parent-issue.md`, i.e. `$SANDBOX_TMP/parent-issue.md`) matches production, but the case does not prove cleanup of a stale sentinel after `POSTED=false`. **Suggested fix:** Seed a deliberately wrong `parent-issue.md` before invoking B4 (e.g. `ISSUE_NUMBER=999` / `RUN_ID=stale`), keep `LARCH_TEST_POSTED=false`, and assert the file is absent afterward (or replaced only after a later successful post). Optionally add `assert_contains "DEFERRED=true"` plus `assert_not_contains "STALL_TRACKING=true"` and `assert_not_contains "IMPLEMENT_BAIL_REASON=tracking-init-failed"` to lock the deferred (non-stall) path.
- **Suggested revision**: Address the concern above.

### FINDING_38: **correctness** `skills/implement/scripts/test-implement-bootstrap.sh:238-242,475-478` — The `post-tracking-issue.sh` stub’s failure mode (`exit 1` plus `POSTED=false` on stdout) aligns with `phase_tracking`’s `if [ "$post_rc" -ne 0 ] || [ "$posted" != "true" ]` branch (`scripts/implement-bootstrap.sh:482-488`): command substitution still captures stdout on non-zero exit, so B4 correctly exercises DECISION_1 deferred behavior rather than `tracking-init-failed`. No change required for that pairing; the gap above is missing negative setup, not stub/production divergence on exit code.
- **Reviewer**: dyn-test-contract-output.txt
- **Concern**: - **correctness** `skills/implement/scripts/test-implement-bootstrap.sh:238-242,475-478` — The `post-tracking-issue.sh` stub’s failure mode (`exit 1` plus `POSTED=false` on stdout) aligns with `phase_tracking`’s `if [ "$post_rc" -ne 0 ] || [ "$posted" != "true" ]` branch (`scripts/implement-bootstrap.sh:482-488`): command substitution still captures stdout on non-zero exit, so B4 correctly exercises DECISION_1 deferred behavior rather than `tracking-init-failed`. No change required for that pairing; the gap above is missing negative setup, not stub/production divergence on exit code.
- **Suggested revision**: Address the concern above.

### FINDING_39: [OUT_OF_SCOPE] **Stub / production alignment (scout checks, no defect):** `larch-log.sh` stub `LARCH_TEST_LARCH_LOG_FAIL=true` → `exit 1` is exercised by `run_larch_log_init` via `init_rc -ne 0` (`scripts/implement-bootstrap.sh:165-166`); B5/B5-branch1/B5-all/B5-plan assertions match `tracking-init-failed` + `STALL_TRACKING=true`, not the deferred path.
- **Reviewer**: dyn-test-contract-output.txt
- **Concern**: - **Stub / production alignment (scout checks, no defect):** `larch-log.sh` stub `LARCH_TEST_LARCH_LOG_FAIL=true` → `exit 1` is exercised by `run_larch_log_init` via `init_rc -ne 0` (`scripts/implement-bootstrap.sh:165-166`); B5/B5-branch1/B5-all/B5-plan assertions match `tracking-init-failed` + `STALL_TRACKING=true`, not the deferred path.
- **Suggested revision**: Address the concern above.

### FINDING_40: [OUT_OF_SCOPE] **Stub / production alignment (scout checks, no defect):** `Edge-breadcrumb-count` (`skills/implement/scripts/test-implement-bootstrap.sh:660-678`) sets `LARCH_QUIET_DISABLE=1` (harness line 6, mirrored in `implement-bootstrap.sh`), `LARCH_QUIET_BREADCRUMBS=1`, and `LARCH_QUIET_BREADCRUMB_FD=1`. Under disable mode, `emit_breadcrumb` in `scripts/lib-quiet.sh:204-214` writes to FD 1 when breadcrumbs are enabled, so counting `→ step0: infra ready` in `$out` is valid.
- **Reviewer**: dyn-test-contract-output.txt
- **Concern**: - **Stub / production alignment (scout checks, no defect):** `Edge-breadcrumb-count` (`skills/implement/scripts/test-implement-bootstrap.sh:660-678`) sets `LARCH_QUIET_DISABLE=1` (harness line 6, mirrored in `implement-bootstrap.sh`), `LARCH_QUIET_BREADCRUMBS=1`, and `LARCH_QUIET_BREADCRUMB_FD=1`. Under disable mode, `emit_breadcrumb` in `scripts/lib-quiet.sh:204-214` writes to FD 1 when breadcrumbs are enabled, so counting `→ step0: infra ready` in `$out` is valid.
- **Suggested revision**: Address the concern above.

### FINDING_41: [OUT_OF_SCOPE] **Doc drift:** The harness includes cases not listed in `skills/implement/scripts/test-implement-bootstrap.md` (e.g. `B2-plan`, `B5-all`, `B5-plan`, `B5-branch1`, `B-sentinel-invalid-run-id`, `B-empty-run-id-derivation`, `GP-adopt-rename-fail`).
- **Reviewer**: dyn-test-contract-output.txt
- **Concern**: - **Doc drift:** The harness includes cases not listed in `skills/implement/scripts/test-implement-bootstrap.md` (e.g. `B2-plan`, `B5-all`, `B5-plan`, `B5-branch1`, `B-sentinel-invalid-run-id`, `B-empty-run-id-derivation`, `GP-adopt-rename-fail`).
- **Suggested revision**: Address the concern above.

### FINDING_42: [OUT_OF_SCOPE] **Commits on branch:** `fc4d783b` (implement phase tracking), `6d635cd2` (larch-logs flush), `438ab338` (round-1 review feedback).
- **Reviewer**: dyn-test-contract-output.txt
- **Concern**: - **Commits on branch:** `fc4d783b` (implement phase tracking), `6d635cd2` (larch-logs flush), `438ab338` (round-1 review feedback).
- **Suggested revision**: Address the concern above.

