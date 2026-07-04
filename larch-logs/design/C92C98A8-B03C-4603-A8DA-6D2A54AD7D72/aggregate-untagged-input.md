### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: .pre-commit-config.yaml:667-672
- **Concern**: Plan wires the new writer-parity lint through CLI and Makefile only, but not the pre-commit source of truth. Scenario: CI lint-local and /implement relevant-checks run make lint-only/pre-commit, not the direct Makefile lint target, so a future bg-wait writer edit can pass without the required drift guard
- **Proposed resolution**: Add a local pre-commit hook for python3 python/cli.py lint bg-wait-writer-parity with pass_filenames false and always_run true, or an equivalent trigger that runs under make lint-only, CI, and relevant-checks

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

### FINDING_7:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: .pre-commit-config.yaml:667-672; Makefile:150-151; Makefile:37
- **Concern**: Writer-parity lint is wired only into make lint; sibling lint-bg-wait-coverage is also registered in pre-commit, and CI runs make lint-only (= pre-commit run --all-files).. Scenario: A merged change can drop CLONE_PATH= from a writer inventory file and pass CI until someone runs full make lint locally.
- **Proposed resolution**: Add a ### UPDATED: .pre-commit-config.yaml entry mirroring lint-bg-wait-coverage (always_run or a files glob covering the inventory paths) beside the Makefile lint-bg-wait-writer-parity target.

### FINDING_11:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/tests/lint/test_lint_bg_wait_writer_parity.py (planned) / skills/design/scripts/design-step3-review.sh:147-169
- **Concern**: Accept-case contract is underspecified for indirect marker writers: design-step3-review.sh writes via _bg_wait_marker temp file + mv, not a direct >.bg-wait-active redirect.. Scenario: A lint implemented as only direct-write greps can false-fail the real inventory or pass minimal synthetic stubs that omit this pattern, letting the parity lint ship broken.
- **Proposed resolution**: Require the accept pytest to run the lint against the real nine-file inventory (or full copied fixtures), explicitly including design-step3-review.sh. Define writer evidence as co-located .bg-wait-active reference plus CLONE_PATH= emission in the same file, not only literal redirect-to-.bg-wait-active patterns.

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
