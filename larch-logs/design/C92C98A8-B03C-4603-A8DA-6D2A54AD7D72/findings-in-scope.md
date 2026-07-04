### FINDING_1: Wire writer-parity lint into the pre-commit/CI path
- **Reviewer(s)**: Codex-Arch, Codex-Innovation, Cursor-Pragmatic, Codex-Requirements, Codex-dyn-Bg Wait Marker Integrity
- **Severity**: important
- **Concern**: The new writer-parity lint is only covered by the direct CLI/Makefile path in the plan, so CI and pre-commit-driven lint runs can miss it. That leaves a gap where a drifted bg-wait writer can still pass the normal PR enforcement path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add a local pre-commit hook for python3 python/cli.py lint bg-wait-writer-parity with pass_filenames false and always_run true, or an equivalent trigger that runs under make lint-only, CI, and relevant-checks
  - From Codex-Innovation: Add a pre-commit hook near `lint-bg-wait-coverage` for `python3 python/cli.py lint bg-wait-writer-parity` with `pass_filenames: false` and an appropriate files filter. Keep the Makefile target as the manual wrapper.
  - From Cursor-Pragmatic: Add a ### UPDATED: .pre-commit-config.yaml entry mirroring lint-bg-wait-coverage (always_run or a files glob covering the inventory paths) beside the Makefile lint-bg-wait-writer-parity target.
  - From Codex-Requirements: Add `.pre-commit-config.yaml` to the firm files and register `python3 python/cli.py lint bg-wait-writer-parity` near `lint-bg-wait-coverage` with `pass_filenames: false` and a file trigger or `always_run` suitable for the explicit inventory.
  - From Codex-dyn-Bg Wait Marker Integrity: Add `### UPDATED: .pre-commit-config.yaml` with a `lint-bg-wait-writer-parity` hook using `python3 python/cli.py lint bg-wait-writer-parity` and `pass_filenames: false`; keep the Makefile target as the local direct entry.

### FINDING_2: Make the accept suite cover indirect marker writers and local CLONE_PATH evidence
- **Reviewer(s)**: Cursor-Innovation, Cursor-Requirements, Codex-Requirements, Cursor-dyn-Bg Wait Marker Integrity
- **Severity**: important
- **Concern**: The lint contract and tests need to recognize real writer shapes, including temp-file-plus-mv marker writes, and they need to assert marker-local CLONE_PATH evidence rather than a naive direct-redirect or whole-file substring check. Without that, the parity lint can false-fail real writers or pass synthetic stubs that do not reflect the actual code paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Define writer evidence as co-occurrence of .bg-wait-active and a CLONE_PATH= emission anywhere in the inventoried file (plus frozen inventory membership). Add an accept test that copies the real design-step3-review.sh and design_core.py marker snippets.
  - From Cursor-Requirements: Require the accept pytest to run the lint against the real nine-file inventory (or full copied fixtures), explicitly including design-step3-review.sh. Define writer evidence as co-located .bg-wait-active reference plus CLONE_PATH= emission in the same file, not only literal redirect-to-.bg-wait-active patterns.
  - From Codex-Requirements: Require the accept pytest to run against the real nine-file inventory (or full copied fixtures), explicitly including design-step3-review.sh. Define writer evidence as same-file .bg-wait-active reference plus CLONE_PATH= emission, not only literal redirect-to-.bg-wait-active patterns; drop or narrow the pure-helper alternative.
  - From Cursor-dyn-Bg Wait Marker Integrity: Require CLONE_PATH in the same function/block as the .bg-wait-active write (printf/write_text/template joined by the writer-evidence match), not anywhere in the file.

### FINDING_3: Do not let a fixed inventory hide future bg-wait writers
- **Reviewer(s)**: Codex-dyn-Bg Wait Marker Integrity
- **Severity**: important
- **Concern**: A parity lint that only checks a frozen list of inventoried files can miss newly added `.bg-wait-active` writers outside that list. That creates a blind spot where future writer paths can bypass the CLONE_PATH requirement entirely.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-Bg Wait Marker Integrity: Keep the explicit inventory to avoid hook/test false positives, but add a static writer-discovery check over runtime writer surfaces that finds actual `.bg-wait-active` write shapes and fails when a writer is not in the inventory or lacks marker-local CLONE_PATH emission; exclude docs, hooks, cleanup-only unlink/rm, and tests.

### FINDING_4:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan approach §1; skills/implement/scripts/run-step-checks.sh:60-74; python/larch/implement/dispatch_commit_route.py:75-88
- **Concern**: [SCOPE-REDUCTION] Plan frames run-step-checks.sh as the Step 3 marker writer but live /implement Step 3 uses checks-commit-route which already stamps CLONE_PATH. Scenario: After the shell edit the plan reads complete while every live Step 3 run already wrote CLONE_PATH via dispatch_commit_route._write_bg_wait_marker; the issue’s cross-clone exposure is not on the active path on current main
- **Proposed resolution**: Reconcile Approach/Testing: name dispatch_commit_route.py as the live Step 3 writer (already covered by test_dispatch_bg_wait_marker_copies_keepalive_clone_path); treat run-step-checks.sh as legacy-only parity; keep the writer-parity lint as the main recurrence guard

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:440-441
- **Concern**: [SCOPE-REDUCTION] Firm run-step-checks.sh CLONE_PATH work targets a dead Step 3 writer; live path already stamps CLONE_PATH. Scenario: Green-path Step 3 arms implement-step3-checks only via python/cli.py implement checks-commit-route (_optional_bg_wait_marker → dispatch_commit_route._write_bg_wait_marker at python/larch/implement/dispatch_commit_route.py:75-88), which already emits CLONE_PATH and is covered by test_dispatch_bg_wait_marker_copies_keepalive_clone_path. skills/implement/scripts/run-step-checks.sh is not invoked from SKILL.md; run-step-checks.md:7-8 documents legacy-only use. Shell edits do not change production markers.
- **Proposed resolution**: Drop ### UPDATED: run-step-checks.sh and run-step-checks.md CLONE_PATH contract changes, or replace with deleting the orphaned SITE=step3 marker block. Keep writer-parity lint. Add an explicit verification step that dispatch_commit_route already passes before any shell churn.

### FINDING_6:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/implement/dispatch_commit_route.py:75-86; skills/implement/SKILL.md:441
- **Concern**: [SCOPE-REDUCTION] Plan treats run-step-checks.sh as the live Step 3 marker fix, but green /implement Step 3 uses checks-commit-route and dispatch_commit_route._write_bg_wait_marker already emits CLONE_PATH=; the shell SITE=step3 block is orphaned (no SKILL or harness caller; run_step_checks_main skips shell marker logic).. Scenario: Implementer can ship the shell patch and lint while believing production Step 3 clone scoping was broken; the stated cross-clone exposure on the highest-traffic path is already closed in dispatch_commit_route.py.
- **Proposed resolution**: Reframe Approach/Files: mark shell work as legacy parity only, or delete the dead SITE=step3 marker block and drop run-step-checks.sh from the lint inventory; keep writer-parity lint as the primary recurrence guard for the eight live writers.

### FINDING_7:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/implement/scripts/run-step-checks.sh:56-74
- **Concern**: [SCOPE-REDUCTION] Firm plan patches CLONE_PATH into a step3-only marker block that run-step-checks.md already documents as unused on active Step 3; keeping the block also preserves a stale TIMEOUT_S=10800 vs 15600 on the live composite path.. Scenario: Patching dead marker code adds ~10 lines and perpetual inventory maintenance without protecting any current orchestration path; reactivation would still be wrong-site relative to checks-commit-route.
- **Proposed resolution**: Prefer removing the SITE=step3 if block and stale comment, document that Step 3 markers are owned by dispatch_commit_route.py, and omit run-step-checks.sh from the writer inventory unless a real caller is restored.

### FINDING_8:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:22-69
- **Concern**: [SCOPE-REDUCTION] New writer-parity lint, CLI registry entry, Makefile targets, and pytest suite exceed the single-writer bug fix scope. Scenario: The binding bug is fixed once run-step-checks.sh stamps CLONE_PATH and the wrapper doc reflects it; adding a maintained inventory linter and new CLI surface creates failure and drift modes unrelated to restoring the missing marker field
- **Proposed resolution**: Remove Approach items 3-5 and the NEW/UPDATED lint, CLI, Makefile, and pytest deliverables; keep the run-step-checks.sh and run-step-checks.md updates, and track writer-parity lint separately if desired

### FINDING_9:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:441 / python/larch/implement/dispatch_commit_route.py:75-88 / skills/implement/scripts/run-step-checks.sh:60-73
- **Concern**: [SCOPE-REDUCTION] Plan frames run-step-checks.sh as the Step 3 production writer, but active /implement Step 3 launches checks-commit-route, whose _write_bg_wait_marker already emits CLONE_PATH= (see python/tests/implement/test_implement_dispatch.py::test_dispatch_bg_wait_marker_copies_keepalive_clone_path); run-step-checks.sh is legacy-only per run-step-checks.md and has no in-repo callers.. Scenario: Issue acceptance targets Step 3 on every /implement, but shipping only the shell printf change does not alter live marker behavior; operators may close the bug while production path was already compliant, or over-invest in a dead writer.
- **Proposed resolution**: Add an upfront verification step: confirm live Step 3 marker already carries CLONE_PATH via checks-commit-route; document that outcome in the plan/issue closure. Keep the shell alignment only as legacy parity (or drop it if minimum-change wins). Retain the writer-parity lint as the durable guard.

### FINDING_10:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:441 / python/larch/implement/dispatch_commit_route.py:75-88 / skills/implement/scripts/run-step-checks.sh:60-73
- **Concern**: [SCOPE-REDUCTION] Plan frames run-step-checks.sh as the Step 3 production writer, but active /implement Step 3 launches checks-commit-route, whose _write_bg_wait_marker already emits CLONE_PATH= (python/tests/implement/test_implement_dispatch.py::test_dispatch_bg_wait_marker_copies_keepalive_clone_path); run-step-checks.sh is legacy-only per run-step-checks.md and has no in-repo callers.. Scenario: Issue acceptance targets Step 3 on every /implement, but shipping only the shell printf change does not alter live marker behavior; the bug may already be fixed on the production path while the plan still reads as correcting it.
- **Proposed resolution**: Add an upfront verification step: confirm the live Step 3 marker already carries CLONE_PATH via checks-commit-route and record that in closure notes. Treat the shell edit as legacy parity only, or drop it if minimum-change wins. Keep the writer-parity lint as the durable anti-drift guard.

### FINDING_11:
- **Reviewer(s)**: Cursor-dyn-Bg Wait Marker Integrity
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:440-441
- **Concern**: [SCOPE-REDUCTION] Firm run-step-checks.sh CLONE_PATH work targets an orphaned Step 3 writer; live /implement Step 3 already stamps CLONE_PATH via checks-commit-route. Scenario: Live Step 3 arms implement-step3-checks through python/cli.py implement checks-commit-route (skills/implement/SKILL.md:441), which wraps _optional_bg_wait_marker → _write_bg_wait_marker with CLONE_PATH={_read_keepalive_clone_path(...)} (python/larch/implement/dispatch_commit_route.py:75-88,897-898). run-step-checks.md:7 says SKILL no longer invokes the shell wrapper for active Step 3; run_step_checks_main forwards to checks run-relevant with no marker write (dispatch_commit_route.py:1108-1115). test_dispatch_bg_wait_marker_copies_keepalive_clone_path already covers the live writer (python/tests/implement/test_implement_dispatch.py:49-55). Shell edits fix only the legacy block at run-step-checks.sh:72-73.
- **Proposed resolution**: Drop the firm UPDATED run-step-checks.sh entry (or demote to optional parity) and center the plan on the writer-parity lint plus dispatch_commit_route.py inventory coverage; if legacy parity is kept, state explicitly that checks-commit-route is the live writer.
