### FINDING_1: Removing lint-bash32 from make lint drops untracked shell-file coverage
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Codex-Edge, Codex-Pragmatic
- **Severity**: important
- **Concern**: The plan removes the direct `lint-bash32` prerequisite from `make lint`, but the replacement pre-commit path is not equivalent because `pre-commit run --all-files` covers tracked files while the existing linter also scans untracked non-ignored shell files.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch, Codex-Arch: Keep lint-bash32 in the lint target for this PR; wire the pre-commit hook for CI and commit-time coverage without changing the broader local make lint contract
  - From Codex-Edge: Keep lint-bash32 in the lint target, or add an equivalent untracked-aware local gate before dropping it; accepting a small duplicate local run is the minimum-change fix
  - From Codex-Pragmatic: Keep lint-bash32 in the lint target and accept the small duplicate local run, or add an equivalent untracked-file scan before removing it


### FINDING_2: Positional harness paths contradict scan_file ROOT-relative behavior
- **Reviewer(s)**: Cursor-Edge, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Concern**: The planned positional tests pass absolute fixture paths outside `$ROOT` while `scan_file` still reads `$ROOT/$rel`. This can skip the fixtures or scan nonexistent paths, causing violation cases to false-pass. The outside-root fallback also adds complexity that pre-commit integration does not require unless `scan_file` is explicitly changed to support it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Invoke positional harness cases as `bash "$LINT" --root "$TMPROOT" scripts/good.sh` (etc.), or teach `scan_file` to use absolute `path` when `rel` is absolute / outside `$ROOT` (plan’s fallback is not spelled as a `scan_file` edit)
  - From Cursor-Innovation: Invoke bash "$LINT" --root "$TMPROOT" scripts/good.sh (relative positionals under --root), matching pre-commit’s repo-relative argv with ROOT at repo root
  - From Codex-Innovation: Keep positional mode scoped to files under ROOT, convert only those to root-relative paths, and adjust the new harness calls to pass fixture files under --root
  - From Cursor-Pragmatic: In scan_file (or the positional branch), if the resolved file is absolute or not under $ROOT, set path to that absolute path; otherwise set rel relative to $ROOT and path="$ROOT/$rel". Align harness invocations with the contract (e.g. cd "$TMPROOT" && bash "$LINT" --root . scripts/good.sh, or pass --root "$TMPROOT" with paths under that root)
  - From Codex-Pragmatic: Drop outside-root support from the plan/tests; exercise positional mode with --root TMPROOT and relative paths so scan_file keeps its existing relative contract
  - From Cursor-Requirements, Codex-Requirements: In harness, pass --root "$TMPROOT" and repo-relative paths (e.g. scripts/good.sh) from TMPROOT cwd, or extend scan_file to read absolute paths when rel is absolute; drop the keep-contract wording unless scan_file is updated


### FINDING_3: Canonical linting docs would be stale
- **Reviewer(s)**: Codex-Innovation, Cursor-dyn-doc-sync, Codex-dyn-doc-sync
- **Severity**: important
- **Concern**: The plan changes Bash 3.2 lint wiring but does not update `docs/linting.md`, leaving canonical docs describing the old direct `make lint` dependency chain and omitting the new pre-commit hook caller.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Add a minimal docs/linting.md edit stating the hook runs through pre-commit/lint-only and make lint-bash32 remains the direct full-repo target
  - From Cursor-dyn-doc-sync, Codex-dyn-doc-sync: Add docs/linting.md to the plan and update the Bash 3.2 row plus CI/local usage paragraph to say lint-bash32 is a pre-commit hook under lint-only/CI/relevant checks, with make lint-bash32 retained as the explicit whole-repo target


### FINDING_4: Missing positional .inc.bash harness coverage
- **Reviewer(s)**: Codex-Requirements, Cursor-dyn-test-inc-bash, Codex-dyn-test-inc-bash
- **Severity**: important
- **Concern**: The proposed harness cases do not include a positional `.inc.bash` violation case, despite the failure-mode text treating `.inc.bash` positional coverage as an expected signal. Existing coverage only proves `.inc.bash` is found by whole-root enumeration, so positional or pre-commit regex regressions for `.inc.bash` could pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add a positional .inc.bash violation case reusing the helper-bad.inc.bash fixture pattern, or revise the failure-mode wording to make .inc.bash validation manual-only via the pre-commit fixture step
  - From Cursor-dyn-test-inc-bash: Align the plan: either add one positional violation case reusing the `helper-bad.inc.bash` fixture pattern from :139–144, or revise Failure modes §1 and the “earliest signal” sentence to state that `.inc.bash` positional coverage is manual-only (Testing strategy :103) and that case 2 targets `.sh` argv handling only
  - From Codex-dyn-test-inc-bash: Minimum-change fix: retarget the proposed positional violation case to bad-unsuppressed.inc.bash, or add one dedicated positional .inc.bash violation case. If the intent is to validate the pre-commit files regex itself, keep the line-103 pre-commit --files .inc.bash check as an explicit required test rather than treating the direct script harness or .md skip case as sufficient.

