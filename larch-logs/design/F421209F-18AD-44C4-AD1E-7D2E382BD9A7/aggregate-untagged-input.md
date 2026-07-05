### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/SKILL.md:692-698
- **Concern**: Sentinel-miss routing is left as stall or operator-bail. Scenario: After pre-fix emits NEXT_ACTION=continue, a missing .ship-pre-fix-rebase-ok can route to operator-bail and autonomous ci-fix repair on a checkout that never passed pre-fix
- **Proposed resolution**: Pin the guard to post-driver stall only (Step 16 with STALL_TRACKING, then Step 18), matching existing NEXT_ACTION=stall handling; do not use operator-bail for this mechanical failure

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/tests/implement/test_implement_dispatch.py:883-944
- **Concern**: Guard-order regression tests are incomplete. Scenario: An allowlisted phase14 flag could regress before the in-progress rebase probe and skip while a paused rebase should stall; the in-progress conflict branch also lacks PHASE=rebase state assertions after switching to _ship_pre_fix_write_conflict_state
- **Proposed resolution**: Add a test with allowlisted REASON plus rebase_in_progress=True and no conflict metadata expecting PRE_FIX_REBASE_STATUS=stall; extend test_ship_pre_fix_rebase_routes_existing_conflict_handoff to assert PHASE=rebase in ship-pr-state.sh

### FINDING_3:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/report/exec_issue_detail.py:290-302
- **Concern**: The execution-issues plan still switches sources instead of preserving both. Scenario: The plan says non-empty tmpdir markdown wins because it is always a superset, but the flush path clears execution-issues.md after writing NDJSON. If Step 7a flushes committed rows, then later failures append only new tmpdir rows, the final report drops the committed NDJSON rows.
- **Proposed resolution**: Change the helper plan to merge run-dir NDJSON groups with non-empty tmpdir markdown groups, or parse both and choose the richer combined result by event identity/count. Keep NDJSON-only and empty-tmpdir fallback.

### FINDING_4:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/references/ship-pr-exit-matrix.md:37-40
- **Concern**: The pre-fix freshness guard is missing from the mandatory Step 8 routing reference. Scenario: SKILL.md is planned to guard ci-fix and reship on .ship-pre-fix-rebase-ok, but Step 8 requires reading ship-pr-exit-matrix.md and says branch details live there. The matrix would still route NEXT_ACTION=continue directly to ship-pr-ci-fix.md or step-8-ship.sh when PRE_FIX_REBASE_REQUIRED=true and the sentinel is absent.
- **Proposed resolution**: Add the same PRE_FIX_REBASE_REQUIRED plus .ship-pre-fix-rebase-ok fail-closed check to the reship and ci-fix branch semantics in ship-pr-exit-matrix.md, or make that reference defer explicitly to the SKILL.md guard before continuing.

### FINDING_5:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/implement/dispatch_ship.py:610
- **Concern**: The phase14 skip plan does not require the parsed RESUME_PHASE metadata. Scenario: The plan allows skip when REASON is allowlisted, but does not require RESUME_PHASE=ship-pr-rrr-phase14. A truncated or stale flag with only REASON=mergeStateStatus=DIRTY can still bypass the pre-fix rebase despite lacking the producer-faithful handoff metadata from the accepted guard contract.
- **Proposed resolution**: Require both RESUME_PHASE=config.SHIP_PR_RRR_RESUME_PHASE and an allowlisted REASON before skip. Treat missing or mismatched RESUME_PHASE the same as empty, bare, conflict-shaped, or disallowed flags.

### FINDING_6:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/references/ship-pr-exit-matrix.md:37-39
- **Concern**: Mandatory Step 8 routing reference is left stale. Scenario: The plan updates SKILL.md with the fresh `.ship-pre-fix-rebase-ok` guard, but Step 8 also mandates reading `ship-pr-exit-matrix.md`, whose reship and ci-fix branches would still allow `NEXT_ACTION=continue` to proceed without checking the sentinel.
- **Proposed resolution**: Update `ship-pr-exit-matrix.md` reship and ci-fix branch semantics to require the same sentinel check when `PRE_FIX_REBASE_REQUIRED=true` before stale-handoff clear or loading `ship-pr-ci-fix.md`.

### FINDING_7:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/report/exec_issue_detail.py:290-303
- **Concern**: Execution-issue plan still chooses one source instead of preserving both. Scenario: The plan says non-empty tmpdir markdown wins because it is always a superset, but `flush_execution_issues` clears `execution-issues.md` after flushing to NDJSON, so later tmpdir-only entries are a delta. Returning only tmpdir markdown would drop committed NDJSON entries.
- **Proposed resolution**: Merge run-dir NDJSON and non-empty tmpdir markdown when both exist, with dedupe if needed. Keep the NDJSON fallback only when tmpdir markdown is absent or empty.

### FINDING_8:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/references/ship-pr-exit-matrix.md:37-39
- **Concern**: Normative ci-fix/reship branch text still omits the `.ship-pre-fix-rebase-ok` consumer guard. Scenario: Accepted FINDING_1 adds the guard only in `skills/implement/SKILL.md`, but Step 8+ prose says branch semantics live in `ship-pr-exit-matrix.md` and that file still routes `NEXT_ACTION=continue` straight into `ship-pr-ci-fix.md` with no freshness check when `PRE_FIX_REBASE_REQUIRED=true`
- **Proposed resolution**: A `### UPDATED:` `skills/implement/references/ship-pr-exit-matrix.md` entry: after `ship pre-fix-rebase` returns `NEXT_ACTION=continue`, require `.ship-pre-fix-rebase-ok` when `PRE_FIX_REBASE_REQUIRED=true` before stale-handoff clear or `ship-pr-ci-fix.md`; stall/operator-bail if absent. Mirror on `reship`.

### FINDING_9:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/implement/dispatch_ship.py
- **Concern**: Approach bullets omit sentinel write on allowlisted phase14 skip even though tests require it. Scenario: Allowlisted phase14 skip still emits `NEXT_ACTION=continue`. If implementers follow only "continue or conflict-fix" in the approach section, they may skip writing `.ship-pre-fix-rebase-ok` on the skip path and the new ci-fix guard will stall legitimate no-checks reships
- **Proposed resolution**: Unify contract language: write `.ship-pre-fix-rebase-ok` on physical rebase success, allowlisted phase14 skip (`PRE_FIX_REBASE_STATUS=skip`), and conflict-fix routing. Keep regression tests explicit for the skip branch.

### FINDING_10:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/tests/report/test_exec_issue_detail.py:98-110
- **Concern**: Planned precedence tests reuse disjoint tmpdir/NDJSON fixtures that are not a flushed superset. Scenario: The loader change prefers any non-empty tmpdir markdown over run-dir NDJSON. Current fixtures give markdown one warning and NDJSON a different failure; updating expectations to "markdown wins" would encode dropping committed NDJSON rows instead of preserving post-flush appends
- **Proposed resolution**: Model superset fixtures: markdown contains flushed NDJSON content plus newer tmpdir-only rows. Assert combined counts/listings include both committed and post-flush entries; keep empty-markdown NDJSON fallback coverage separate. schema_version scope severity focus_area location what scenario_or_breakage suggested_fix

### FINDING_11:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/references/ship-pr-exit-matrix.md:37-39
- **Concern**: Normative ci-fix/reship branch text still omits the `.ship-pre-fix-rebase-ok` consumer guard. Scenario: Accepted FINDING_1 adds the guard only in `skills/implement/SKILL.md`, but Step 8+ prose says branch semantics live in `ship-pr-exit-matrix.md` and that file still routes `NEXT_ACTION=continue` straight into `ship-pr-ci-fix.md` with no freshness check when `PRE_FIX_REBASE_REQUIRED=true`
- **Proposed resolution**: Add `### UPDATED: skills/implement/references/ship-pr-exit-matrix.md`: after `ship pre-fix-rebase` returns `NEXT_ACTION=continue`, require `.ship-pre-fix-rebase-ok` when `PRE_FIX_REBASE_REQUIRED=true` before stale-handoff clear or `ship-pr-ci-fix.md`; stall/operator-bail if absent. Mirror on `reship`.

### FINDING_12:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/implement/dispatch_ship.py
- **Concern**: Approach bullets omit sentinel write on allowlisted phase14 skip even though tests require it. Scenario: Allowlisted phase14 skip still emits `NEXT_ACTION=continue`. If implementers follow only "continue or conflict-fix" in the approach section, they may skip writing `.ship-pre-fix-rebase-ok` on the skip path and the new ci-fix guard will stall legitimate no-checks reships
- **Proposed resolution**: Unify contract language: write `.ship-pre-fix-rebase-ok` on physical rebase success, allowlisted phase14 skip (`PRE_FIX_REBASE_STATUS=skip`), and conflict-fix routing. Keep regression tests explicit for the skip branch.

### FINDING_13:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/tests/report/test_exec_issue_detail.py:98-110
- **Concern**: Planned precedence tests reuse disjoint tmpdir/NDJSON fixtures that are not a flushed superset. Scenario: The loader change prefers any non-empty tmpdir markdown over run-dir NDJSON. Current fixtures give markdown one warning and NDJSON a different failure; updating expectations to "markdown wins" would encode dropping committed NDJSON rows instead of preserving post-flush appends
- **Proposed resolution**: Model superset fixtures: markdown contains flushed NDJSON content plus newer tmpdir-only rows. Assert combined counts/listings include both committed and post-flush entries; keep empty-markdown NDJSON fallback coverage separate. ### Findings 1. **risk-integration** — `skills/implement/references/ship-pr-exit-matrix.md:37-39`: The sentinel consumer guard is planned only in `SKILL.md`, but ci-fix/reship semantics are normative in `ship-pr-exit-matrix.md`. Without updating that reference, implementers can still reach autonomous repair without the freshness check. 2. **correctness** — `python/larch/implement/dispatch_ship.py`: Approach text says write `.ship-pre-fix-rebase-ok` only on "continue or conflict-fix," while the testing section requires it on allowlisted skip too. That gap can stall valid phase14 skip paths once the ci-fix guard lands. 3. **correctness** — `python/tests/report/test_exec_issue_detail.py:98-110`: Disjoint tmpdir/NDJSON fixtures do not model the flushed-superset contract. Tests updated to prefer non-empty markdown would validate dropping committed NDJSON rows instead of preserving post-flush appends.

### FINDING_14:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/report/exec_issue_detail.py:290-304
- **Concern**: Prior execution-issues fix is incomplete: the plan makes non-empty tmpdir markdown win instead of merging it with run-dir NDJSON.. Scenario: Step 7a flush can append committed NDJSON and clear execution-issues.md; a later Step 8 warning makes markdown non-empty but no longer contains the earlier NDJSON-only failure, so final_report drops committed failures.
- **Proposed resolution**: When both sources exist and tmpdir markdown is non-empty, parse both and merge/dedupe detail groups, with NDJSON-only fallback for empty markdown and degraded legacy rows preserved.

### FINDING_15:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/references/ship-pr-exit-matrix.md:22-39
- **Concern**: Prior freshness-sentinel fix is incomplete: the mandatory Step 8+ reference is not listed for update, so it still permits old phase14 and ci-fix/reship routing without the .ship-pre-fix-rebase-ok guard.. Scenario: Step 8+ always loads this reference before routing; leaving it stale can tell the orchestrator to read ship-pr-ci-fix.md on NEXT_ACTION=continue even when PRE_FIX_REBASE_REQUIRED=true lacks fresh proof, or to treat any pending phase14 flag as reship.
- **Proposed resolution**: Add the same no-checks REASON allowlist, conflict-metadata routing, and PRE_FIX_REBASE_REQUIRED plus sentinel guard to this reference, matching SKILL.md and dispatch_ship.

### FINDING_16:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/test-write-final-report.sh:380-390
- **Concern**: Makefile wires the bash harness into CI but the dual-artifact scenario still expects NDJSON-over-markdown precedence. Scenario: After `load_issue_detail_groups(..., prefer_run_dir=True)` prefers non-empty tmpdir markdown, the case that keeps both `execution-issues.md` and run-dir NDJSON will assert Exec issues 0 / Warnings 1 from NDJSON; live markdown has an External Reviewer Issues row, so counts should come from markdown and `make test-write-final-report` will fail once the Makefile change lands
- **Proposed resolution**: Add `### UPDATED: skills/implement/scripts/test-write-final-report.sh`: revise the dual-artifact block to expect tmpdir markdown counts when both files exist; keep the existing NDJSON-only fallback case after removing markdown; add a second dual-artifact case if both sources must contribute to the summary

### FINDING_17:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/report/exec_issue_detail.py:290-298
- **Concern**: Accepted execution-issues fix still drops run-dir rows. Scenario: `flush_execution_issues` clears `execution-issues.md` after appending NDJSON, so later tmpdir warnings make markdown non-empty but not a superset; the planned markdown-wins rule loses already flushed NDJSON entries in the final summary.
- **Proposed resolution**: When both artifacts exist, parse both and merge or collapse by dedupe key; only fall back to one source when the other is absent or empty. Update the planned tests to assert the union.

### FINDING_18:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/implement/dispatch_ship.py:606-611
- **Concern**: Accepted phase14 skip fix still trusts a stale allowed flag without current no-checks handoff metadata. Scenario: A prior no-checks phase14 run can leave `REASON=mergeStateStatus=DIRTY`; a later `ci-fix` handoff clears only `.ship-pre-fix-rebase-ok`, so pre-fix can skip rebase, write a fresh sentinel, and let `ship-pr-ci-fix.md` run without the required guarded rebase.
- **Proposed resolution**: Allow the phase14 skip only when the current `.ship-route-exit-handoff.env` proves `NEXT_ACTION=reship` for `DETAIL=no-ci-checks-observed` plus the allowlisted flag reason, or clear the phase14 flag on every non-no-checks handoff.
