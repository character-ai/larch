### [Plan Review] FINDING_1

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


### [Plan Review] FINDING_2

### FINDING_2: Make the accept suite cover indirect marker writers and local CLONE_PATH evidence
- **Reviewer(s)**: Cursor-Innovation, Cursor-Requirements, Codex-Requirements, Cursor-dyn-Bg Wait Marker Integrity
- **Severity**: important
- **Concern**: The lint contract and tests need to recognize real writer shapes, including temp-file-plus-mv marker writes, and they need to assert marker-local CLONE_PATH evidence rather than a naive direct-redirect or whole-file substring check. Without that, the parity lint can false-fail real writers or pass synthetic stubs that do not reflect the actual code paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Define writer evidence as co-occurrence of .bg-wait-active and a CLONE_PATH= emission anywhere in the inventoried file (plus frozen inventory membership). Add an accept test that copies the real design-step3-review.sh and design_core.py marker snippets.
  - From Cursor-Requirements: Require the accept pytest to run the lint against the real nine-file inventory (or full copied fixtures), explicitly including design-step3-review.sh. Define writer evidence as co-located .bg-wait-active reference plus CLONE_PATH= emission in the same file, not only literal redirect-to-.bg-wait-active patterns.
  - From Codex-Requirements: Require the accept pytest to run against the real nine-file inventory (or full copied fixtures), explicitly including design-step3-review.sh. Define writer evidence as same-file .bg-wait-active reference plus CLONE_PATH= emission, not only literal redirect-to-.bg-wait-active patterns; drop or narrow the pure-helper alternative.
  - From Cursor-dyn-Bg Wait Marker Integrity: Require CLONE_PATH in the same function/block as the .bg-wait-active write (printf/write_text/template joined by the writer-evidence match), not anywhere in the file.


### [Plan Review] FINDING_3

### FINDING_3: Do not let a fixed inventory hide future bg-wait writers
- **Reviewer(s)**: Codex-dyn-Bg Wait Marker Integrity
- **Severity**: important
- **Concern**: A parity lint that only checks a frozen list of inventoried files can miss newly added `.bg-wait-active` writers outside that list. That creates a blind spot where future writer paths can bypass the CLONE_PATH requirement entirely.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-Bg Wait Marker Integrity: Keep the explicit inventory to avoid hook/test false positives, but add a static writer-discovery check over runtime writer surfaces that finds actual `.bg-wait-active` write shapes and fails when a writer is not in the inventory or lacks marker-local CLONE_PATH emission; exclude docs, hooks, cleanup-only unlink/rm, and tests.


### [Plan Review] FINDING_7

### FINDING_7:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/implement/scripts/run-step-checks.sh:56-74
- **Concern**: [SCOPE-REDUCTION] Firm plan patches CLONE_PATH into a step3-only marker block that run-step-checks.md already documents as unused on active Step 3; keeping the block also preserves a stale TIMEOUT_S=10800 vs 15600 on the live composite path.. Scenario: Patching dead marker code adds ~10 lines and perpetual inventory maintenance without protecting any current orchestration path; reactivation would still be wrong-site relative to checks-commit-route.
- **Proposed resolution**: Prefer removing the SITE=step3 if block and stale comment, document that Step 3 markers are owned by dispatch_commit_route.py, and omit run-step-checks.sh from the writer inventory unless a real caller is restored.


### [Plan Review] FINDING_8

### FINDING_8:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:22-69
- **Concern**: [SCOPE-REDUCTION] New writer-parity lint, CLI registry entry, Makefile targets, and pytest suite exceed the single-writer bug fix scope. Scenario: The binding bug is fixed once run-step-checks.sh stamps CLONE_PATH and the wrapper doc reflects it; adding a maintained inventory linter and new CLI surface creates failure and drift modes unrelated to restoring the missing marker field
- **Proposed resolution**: Remove Approach items 3-5 and the NEW/UPDATED lint, CLI, Makefile, and pytest deliverables; keep the run-step-checks.sh and run-step-checks.md updates, and track writer-parity lint separately if desired


