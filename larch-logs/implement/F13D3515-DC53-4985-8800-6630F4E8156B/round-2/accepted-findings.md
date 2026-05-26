### FINDING_1: code-quality: skills/implement/SKILL.md:579-594
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Bootstrap mark_tracking_ledgers and SKILL both call token/timing mark Step 0 — tracking issue. Successful adopt/resume runs get duplicate ledger marks; timing segments collapse. Keep rehydrate in SKILL; remove duplicate marks from one side and update structure lint to match.
- **Suggested revision**: Address the concern above.


### FINDING_10: correctness: scripts/implement-bootstrap.sh:481-488
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] mark_tracking_ledgers runs when POSTED!=true and DEFERRED=true. Metadata post fails but ledgers show tracking adoption completed; contradicts DEFERRED and no sentinel. Omit mark_tracking_ledgers on the deferred branch or use a distinct mark label for deferred metadata.
- **Suggested revision**: Address the concern above.


### FINDING_12: correctness: scripts/implement-bootstrap.sh:395-402
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Fork get-issue-context requires both upstream repo and issue-number argv. Forked bootstrap with repo but no issue skips upstream fetch; plan/design note is untested. Add harness case or document that both flags are mandatory for the fetch.
- **Suggested revision**: Address the concern above.


### FINDING_13: risk-integration: skills/implement/scripts/test-implement-bootstrap.md:10-30
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Harness sibling case table omits seven round-1 cases (B2-plan B5-all B5-plan B5-branch1 B-sentinel-invalid-run-id B-empty-run-id-derivation GP-adopt-rename-fail). Maintainers or CI triage assume incomplete coverage; plan F13 doc parity fails. Add a table row for every # --- case block in test-implement-bootstrap.sh.
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


### FINDING_2: correctness: skills/implement/SKILL.md:579-594
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Post-bootstrap ledger block is unconditional. Fork/repo-unavailable/bail paths still record tracking-issue ledger marks without adoption. Gate marks on BRANCH_SELECTED or bail flags; align with bootstrap skip semantics.
- **Suggested revision**: Address the concern above.


### FINDING_21: security: scripts/implement-bootstrap.sh:416-429
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Branch 1 resume omits argv/sentinel issue match when --issue-number is empty. Stale parent-issue.md can resume and rename a different GitHub issue than the operator invoked. Require --issue-number for Branch 1 or refuse resume when argv issue is empty but sentinel exists.
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


### FINDING_29: correctness: scripts/implement-bootstrap.sh:395-401
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Fork upstream context skipped unless repo and issue both set forked_target with repo but no issue-number silently skips context fetch Warn or fail when fork mode lacks required upstream inputs
- **Suggested revision**: Address the concern above.


### FINDING_3: code-quality: scripts/implement-bootstrap.sh:481-488
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] mark_tracking_ledgers runs when POSTED=false (DEFERRED). Ledger shows tracking milestone without sentinel/rename/summary. Call mark_tracking_ledgers only after successful post or use a distinct deferred label.
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


### FINDING_5: code-quality: skills/implement/scripts/test-implement-bootstrap.md:10-30
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Harness sibling doc missing round-1 cases. Operators miss coverage for phase-skip and malformed-run-id paths. Sync case table with test-implement-bootstrap.sh.
- **Suggested revision**: Address the concern above.


### FINDING_6: code-quality: skills/implement/SKILL.md:603
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Fork table omits --issue-number requirement for get-issue-context. Doc readers expect repo-only upstream fetch. Update SKILL table or relax bootstrap guard consistently.
- **Suggested revision**: Address the concern above.


### FINDING_9: correctness: scripts/implement-bootstrap.sh:146-149,427,487,492 and skills/implement/SKILL.md:590-591
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Duplicate Step 0 tracking ledger marks: bootstrap mark_tracking_ledgers plus SKILL still marks after bootstrap. Successful Branch 2 adopt records two timing/token marks for the same milestone; Step 0 timing reports are wrong. Keep marks in one place only: remove SKILL marks or remove bootstrap mark_tracking_ledgers on success paths.
- **Suggested revision**: Address the concern above.


