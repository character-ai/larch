### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: architecture
- **Location**: skills/implement/scripts/step-8-ship.md:31-33
- **Concern**: Missing runtime contract retarget for Step 8 ship edit-in-sync (G-Cfg-3). Scenario: The issue firm headings require updating step-8-ship.md alongside the other runtime contract docs. The plan updates step-5-review.md and step-18.md but has no ### UPDATED: skills/implement/scripts/step-8-ship.md row. After test-step-8-ship.sh is deleted, the Edit-in-sync block will still name the retired harness as the coverage owner, violating acceptance that removed paths leave no documentation references and breaking G-Cfg-3 writer/selector alignment.
- **Proposed resolution**: Add ### UPDATED: skills/implement/scripts/step-8-ship.md: replace test-step-8-ship.sh in Edit-in-sync with python/tests/implement/test_implement_shell_scripts.py and the Step 8 node group (static pins, seeder argv, rejoin, handoff, guard, merge-result fail-closed cases).

### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: correctness
- **Location**: skills/implement/scripts/test-step-18.sh:316-326
- **Concern**: Step 18 finalize output-ordering assertions are coupled to the restore-mismatch stub log. Scenario: The Bash harness reads line order from `$TMP_ROOT/restore-mismatch.log` produced by the immediately preceding restore-mismatch finalize run, not from a standalone invocation. Splitting ordering into an isolated pytest node without that shared log (or an equivalent re-run) drops five ordering assertions while still passing other Step 18 ports.
- **Proposed resolution**: In the Step 18 port list, state that ordering nodes execute against the restore-mismatch finalize stub log (same coupling as `test-step-18.sh:294-326`) or fold ordering checks into that scenario.

### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: correctness
- **Location**: skills/implement/scripts/test-implement-review-token-propagation.md:11-16
- **Concern**: Token propagation contract still documents the wrong review-and-fix entrypoint. Scenario: The harness exercises `python/cli.py review-and-fix step5 --mode single` (see `test-implement-review-token-propagation.sh:18,145-151`), but the contract Coverage and Edit-in-sync sections still name `review-and-fix apply-findings`. A straight rewrite that retargets paths but keeps the old verb misleads future edit-in-sync work.
- **Proposed resolution**: In the `### UPDATED: skills/implement/scripts/test-implement-review-token-propagation.md` step, explicitly require Coverage and Edit-in-sync to document `review-and-fix step5 --mode single` (and drop `apply-findings`).

### FINDING_5:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: correctness
- **Location**: skills/implement/scripts/test-implement-review-token-propagation.md:11-16
- **Concern**: The token-propagation contract rewrite does not require fixing the exercised CLI verb.. Scenario: The live harness calls `python/cli.py review-and-fix step5`, but the contract Coverage and Edit-in-sync sections still document `review-and-fix apply-findings`. A title-and-module-only retarget can preserve the wrong verb and mislead future edit-in-sync work.
- **Proposed resolution**: In the `### UPDATED: skills/implement/scripts/test-implement-review-token-propagation.md` step, require Coverage and Edit-in-sync to name `review-and-fix step5` (and the real `review core` stub path) and remove `apply-findings` references.

### FINDING_6:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: minor
- **Focus area**: correctness
- **Location**: skills/implement/scripts/test-implement-review-token-propagation.md:11,16
- **Concern**: Token contract still documents `review-and-fix apply-findings` instead of the exercised `review-and-fix step5` path. Scenario: The harness runs `python3 …/cli.py review-and-fix step5` (see `test-implement-review-token-propagation.sh:18`), but the contract Coverage and Edit-in-sync sections still name `apply-findings`. The plan only retitles the doc and points at the new pytest module, so the wrong subcommand can survive migration and misdirect future edit-in-sync work.
- **Proposed resolution**: In the `### UPDATED: skills/implement/scripts/test-implement-review-token-propagation.md` step, require rewriting Coverage and Edit-in-sync to `review-and-fix step5`, matching the harness and planned pytest nodes. ## Findings 1. **correctness** — `skills/implement/scripts/test-implement-review-token-propagation.md:11,16`: The contract still documents `python/cli.py review-and-fix apply-findings`, while the legacy harness and planned pytest port exercise `review-and-fix step5`. The plan’s doc update only retitles the file and references the new module; it does not require correcting the exercised CLI path. After migration, edit-in-sync guidance can still point maintainers at the wrong entrypoint. **Suggested revision:** In the `test-implement-review-token-propagation.md` update step, explicitly replace `apply-findings` with `step5` in both Coverage and Edit-in-sync, aligned with `test-implement-review-token-propagation.sh` and the new pytest node group. Accepted prior items (calibration fixture literals, `test-write-final-report.sh` comment) are already covered in the plan. Other ledger items (seeder-only coverage, step7a transcript skip, symlink net-new tests, delegated Step 5 pytest suites, monolithic module layout) are either addressed by the plan’s global parity rule, required by binding acceptance, or were already rejected/OOS.
