### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan approach §1; skills/implement/scripts/run-step-checks.sh:60-74; python/larch/implement/dispatch_commit_route.py:75-88
- **Concern**: [SCOPE-REDUCTION] Plan frames run-step-checks.sh as the Step 3 marker writer but live /implement Step 3 uses checks-commit-route which already stamps CLONE_PATH. Scenario: After the shell edit the plan reads complete while every live Step 3 run already wrote CLONE_PATH via dispatch_commit_route._write_bg_wait_marker; the issue’s cross-clone exposure is not on the active path on current main
- **Proposed resolution**: Reconcile Approach/Testing: name dispatch_commit_route.py as the live Step 3 writer (already covered by test_dispatch_bg_wait_marker_copies_keepalive_clone_path); treat run-step-checks.sh as legacy-only parity; keep the writer-parity lint as the main recurrence guard



### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: .pre-commit-config.yaml:667-672
- **Concern**: Plan wires the new writer-parity lint through CLI and Makefile only, but not the pre-commit source of truth. Scenario: CI lint-local and /implement relevant-checks run make lint-only/pre-commit, not the direct Makefile lint target, so a future bg-wait writer edit can pass without the required drift guard
- **Proposed resolution**: Add a local pre-commit hook for python3 python/cli.py lint bg-wait-writer-parity with pass_filenames false and always_run true, or an equivalent trigger that runs under make lint-only, CI, and relevant-checks



### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:440-441
- **Concern**: [SCOPE-REDUCTION] Firm run-step-checks.sh CLONE_PATH work targets a dead Step 3 writer; live path already stamps CLONE_PATH. Scenario: Green-path Step 3 arms implement-step3-checks only via python/cli.py implement checks-commit-route (_optional_bg_wait_marker → dispatch_commit_route._write_bg_wait_marker at python/larch/implement/dispatch_commit_route.py:75-88), which already emits CLONE_PATH and is covered by test_dispatch_bg_wait_marker_copies_keepalive_clone_path. skills/implement/scripts/run-step-checks.sh is not invoked from SKILL.md; run-step-checks.md:7-8 documents legacy-only use. Shell edits do not change production markers.
- **Proposed resolution**: Drop ### UPDATED: run-step-checks.sh and run-step-checks.md CLONE_PATH contract changes, or replace with deleting the orphaned SITE=step3 marker block. Keep writer-parity lint. Add an explicit verification step that dispatch_commit_route already passes before any shell churn.



### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/larch/lint/lint_bg_wait_writer_parity.py
- **Concern**: Writer-evidence heuristic must tolerate atomic tmp+mv marker writes, not only direct .bg-wait-active redirection. Scenario: design-step3-review.sh writes via $_bg_wait_tmp then mv to $_bg_wait_marker (skills/design/scripts/design-step3-review.sh:155-169); design_core.py uses tmp.write_text then tmp.replace(marker) (python/larch/design/design_core.py:175-193). A naive grep for >.bg-wait-active or write_text(.*bg-wait-active on one line will false-fail two inventory writers that already stamp CLONE_PATH.
- **Proposed resolution**: Define writer evidence as co-occurrence of .bg-wait-active and a CLONE_PATH= emission anywhere in the inventoried file (plus frozen inventory membership). Add an accept test that copies the real design-step3-review.sh and design_core.py marker snippets.



### FINDING_5:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: .pre-commit-config.yaml:1-7, .github/workflows/ci.yaml:121-127
- **Concern**: Writer-parity lint is not wired into pre-commit/CI. Scenario: The plan adds a Makefile target, but CI and relevant checks run `make lint-only` through pre-commit. A future writer missing `CLONE_PATH=` can pass CI unless someone manually runs the direct Make target.
- **Proposed resolution**: Add a pre-commit hook near `lint-bg-wait-coverage` for `python3 python/cli.py lint bg-wait-writer-parity` with `pass_filenames: false` and an appropriate files filter. Keep the Makefile target as the manual wrapper.



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
- **Focus area**: risk-integration
- **Location**: .pre-commit-config.yaml:667-672; Makefile:150-151; Makefile:37
- **Concern**: Writer-parity lint is wired only into make lint; sibling lint-bg-wait-coverage is also registered in pre-commit, and CI runs make lint-only (= pre-commit run --all-files).. Scenario: A merged change can drop CLONE_PATH= from a writer inventory file and pass CI until someone runs full make lint locally.
- **Proposed resolution**: Add a ### UPDATED: .pre-commit-config.yaml entry mirroring lint-bg-wait-coverage (always_run or a files glob covering the inventory paths) beside the Makefile lint-bg-wait-writer-parity target.



### FINDING_8:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/implement/scripts/run-step-checks.sh:56-74
- **Concern**: [SCOPE-REDUCTION] Firm plan patches CLONE_PATH into a step3-only marker block that run-step-checks.md already documents as unused on active Step 3; keeping the block also preserves a stale TIMEOUT_S=10800 vs 15600 on the live composite path.. Scenario: Patching dead marker code adds ~10 lines and perpetual inventory maintenance without protecting any current orchestration path; reactivation would still be wrong-site relative to checks-commit-route.
- **Proposed resolution**: Prefer removing the SITE=step3 if block and stale comment, document that Step 3 markers are owned by dispatch_commit_route.py, and omit run-step-checks.sh from the writer inventory unless a real caller is restored.



### FINDING_9:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:22-69
- **Concern**: [SCOPE-REDUCTION] New writer-parity lint, CLI registry entry, Makefile targets, and pytest suite exceed the single-writer bug fix scope. Scenario: The binding bug is fixed once run-step-checks.sh stamps CLONE_PATH and the wrapper doc reflects it; adding a maintained inventory linter and new CLI surface creates failure and drift modes unrelated to restoring the missing marker field
- **Proposed resolution**: Remove Approach items 3-5 and the NEW/UPDATED lint, CLI, Makefile, and pytest deliverables; keep the run-step-checks.sh and run-step-checks.md updates, and track writer-parity lint separately if desired



### FINDING_10:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:441 / python/larch/implement/dispatch_commit_route.py:75-88 / skills/implement/scripts/run-step-checks.sh:60-73
- **Concern**: [SCOPE-REDUCTION] Plan frames run-step-checks.sh as the Step 3 production writer, but active /implement Step 3 launches checks-commit-route, whose _write_bg_wait_marker already emits CLONE_PATH= (see python/tests/implement/test_implement_dispatch.py::test_dispatch_bg_wait_marker_copies_keepalive_clone_path); run-step-checks.sh is legacy-only per run-step-checks.md and has no in-repo callers.. Scenario: Issue acceptance targets Step 3 on every /implement, but shipping only the shell printf change does not alter live marker behavior; operators may close the bug while production path was already compliant, or over-invest in a dead writer.
- **Proposed resolution**: Add an upfront verification step: confirm live Step 3 marker already carries CLONE_PATH via checks-commit-route; document that outcome in the plan/issue closure. Keep the shell alignment only as legacy parity (or drop it if minimum-change wins). Retain the writer-parity lint as the durable guard.



### FINDING_11:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/tests/lint/test_lint_bg_wait_writer_parity.py (planned) / skills/design/scripts/design-step3-review.sh:147-169
- **Concern**: Accept-case contract is underspecified for indirect marker writers: design-step3-review.sh writes via _bg_wait_marker temp file + mv, not a direct >.bg-wait-active redirect.. Scenario: A lint implemented as only direct-write greps can false-fail the real inventory or pass minimal synthetic stubs that omit this pattern, letting the parity lint ship broken.
- **Proposed resolution**: Require the accept pytest to run the lint against the real nine-file inventory (or full copied fixtures), explicitly including design-step3-review.sh. Define writer evidence as co-located .bg-wait-active reference plus CLONE_PATH= emission in the same file, not only literal redirect-to-.bg-wait-active patterns.



### FINDING_12:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:441 / python/larch/implement/dispatch_commit_route.py:75-88 / skills/implement/scripts/run-step-checks.sh:60-73
- **Concern**: [SCOPE-REDUCTION] Plan frames run-step-checks.sh as the Step 3 production writer, but active /implement Step 3 launches checks-commit-route, whose _write_bg_wait_marker already emits CLONE_PATH= (python/tests/implement/test_implement_dispatch.py::test_dispatch_bg_wait_marker_copies_keepalive_clone_path); run-step-checks.sh is legacy-only per run-step-checks.md and has no in-repo callers.. Scenario: Issue acceptance targets Step 3 on every /implement, but shipping only the shell printf change does not alter live marker behavior; the bug may already be fixed on the production path while the plan still reads as correcting it.
- **Proposed resolution**: Add an upfront verification step: confirm the live Step 3 marker already carries CLONE_PATH via checks-commit-route and record that in closure notes. Treat the shell edit as legacy parity only, or drop it if minimum-change wins. Keep the writer-parity lint as the durable anti-drift guard.



### FINDING_13:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/tests/lint/test_lint_bg_wait_writer_parity.py (planned) / skills/design/scripts/design-step3-review.sh:147-169
- **Concern**: Accept-case contract allows a pure-helper/synthetic path that can skip real inventory files; design-step3-review.sh writes via _bg_wait_marker temp+mv, not a direct >.bg-wait-active redirect.. Scenario: If implementers take the synthetic-helper shortcut, the lint can pass minimal stubs yet false-fail or miss indirect writers like design-step3-review.sh, shipping a broken parity ratchet.
- **Proposed resolution**: Require the accept pytest to run against the real nine-file inventory (or full copied fixtures), explicitly including design-step3-review.sh. Define writer evidence as same-file .bg-wait-active reference plus CLONE_PATH= emission, not only literal redirect-to-.bg-wait-active patterns; drop or narrow the pure-helper alternative.



### FINDING_14:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: .pre-commit-config.yaml:667-672
- **Concern**: Writer-parity lint is not wired into pre-commit/CI. Scenario: The plan adds the lint to CLI and Makefile, but CI lint jobs run pre-commit via `make lint-only`; without a pre-commit hook, the new drift guard is not enforced in PR CI.
- **Proposed resolution**: Add `.pre-commit-config.yaml` to the firm files and register `python3 python/cli.py lint bg-wait-writer-parity` near `lint-bg-wait-coverage` with `pass_filenames: false` and a file trigger or `always_run` suitable for the explicit inventory.



### FINDING_15:
- **Reviewer(s)**: Cursor-dyn-Bg Wait Marker Integrity
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:440-441
- **Concern**: [SCOPE-REDUCTION] Firm run-step-checks.sh CLONE_PATH work targets an orphaned Step 3 writer; live /implement Step 3 already stamps CLONE_PATH via checks-commit-route. Scenario: Live Step 3 arms implement-step3-checks through python/cli.py implement checks-commit-route (skills/implement/SKILL.md:441), which wraps _optional_bg_wait_marker → _write_bg_wait_marker with CLONE_PATH={_read_keepalive_clone_path(...)} (python/larch/implement/dispatch_commit_route.py:75-88,897-898). run-step-checks.md:7 says SKILL no longer invokes the shell wrapper for active Step 3; run_step_checks_main forwards to checks run-relevant with no marker write (dispatch_commit_route.py:1108-1115). test_dispatch_bg_wait_marker_copies_keepalive_clone_path already covers the live writer (python/tests/implement/test_implement_dispatch.py:49-55). Shell edits fix only the legacy block at run-step-checks.sh:72-73.
- **Proposed resolution**: Drop the firm UPDATED run-step-checks.sh entry (or demote to optional parity) and center the plan on the writer-parity lint plus dispatch_commit_route.py inventory coverage; if legacy parity is kept, state explicitly that checks-commit-route is the live writer.



### FINDING_16:
- **Reviewer(s)**: Cursor-dyn-Bg Wait Marker Integrity
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/larch/lint/lint_bg_wait_writer_parity.py (planned)
- **Concern**: Lint contract does not operationalize local CLONE_PATH emission next to the marker write. Scenario: Approach item 3 requires marker-writer evidence and a local CLONE_PATH= emission, but the NEW module spec only says to fail on missing CLONE_PATH= or missing writer evidence. A whole-file substring check could pass a comment-only CLONE_PATH= while the .bg-wait-active body omits it (design-step3-review.sh:161-168 and step-5-review.sh:78-79 tie CLONE_PATH to the write block).
- **Proposed resolution**: Require CLONE_PATH in the same function/block as the .bg-wait-active write (printf/write_text/template joined by the writer-evidence match), not anywhere in the file.



### FINDING_17:
- **Reviewer(s)**: Codex-dyn-Bg Wait Marker Integrity
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:14-28; <TMPDIR>/plan.txt:79-88; skills/implement/scripts/run-step-checks.sh:72-73; python/larch/implement/dispatch_commit_route.py:75-88
- **Concern**: The planned writer-parity lint only checks a fixed inventory, so it does not discover new marker writers outside that list. Scenario: The plan enumerates known writer files and checks only each listed file. A future wrapper can write >"$IMPLEMENT_TMPDIR/.bg-wait-active" like run-step-checks.sh or write_text to ".bg-wait-active" like dispatch_commit_route.py without being in the inventory; the lint still passes, so it does not prevent future marker writers from omitting marker-local CLONE_PATH stamps.
- **Proposed resolution**: Keep the explicit inventory to avoid hook/test false positives, but add a static writer-discovery check over runtime writer surfaces that finds actual `.bg-wait-active` write shapes and fails when a writer is not in the inventory or lacks marker-local CLONE_PATH emission; exclude docs, hooks, cleanup-only unlink/rm, and tests.



### FINDING_18:
- **Reviewer(s)**: Codex-dyn-Bg Wait Marker Integrity
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: <TMPDIR>/plan.txt:29-32; <TMPDIR>/plan.txt:72-77; .pre-commit-config.yaml:1-7; .pre-commit-config.yaml:667-672; .github/workflows/ci.yaml:121-127; Makefile:37
- **Concern**: The new lint is not wired into the pre-commit/CI path. Scenario: The plan registers the CLI and Makefile target, but `.pre-commit-config.yaml` says CI uses `make lint-only` via pre-commit and relevant checks use `pre-commit run --files`; CI lint-local also runs `make lint-only`. Existing bg-wait coverage has a pre-commit hook, while the planned writer-parity lint would only run when someone manually runs the Makefile target or full local `make lint`, so future drift can pass CI.
- **Proposed resolution**: Add `### UPDATED: .pre-commit-config.yaml` with a `lint-bg-wait-writer-parity` hook using `python3 python/cli.py lint bg-wait-writer-parity` and `pass_filenames: false`; keep the Makefile target as the local direct entry.



