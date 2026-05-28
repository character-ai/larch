### FINDING_1: Launcher exit stub writes to wrong channel
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation
- **Severity**: important
- **Concern**: The planned `run_ship_pr_3134_vendor_exit0_no_commits` test may not exercise the intended launcher exit path because `ship-pr.sh` reads `LAUNCHER_EXIT` from launcher stdout captured in `fail_file`, while the described stub writes only to `--output`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch, Cursor-Innovation: New case should printf LAUNCHER_EXIT=0 to stdout (same pattern as scripts/test-ship-pr.sh:4389 and default make_repo launcher stub :250), optionally still write token-record to --output

### FINDING_2: New lint is missing from enforced pre-commit/CI path
- **Reviewer(s)**: Codex-Arch, Cursor-Edge, Codex-Edge, Codex-Innovation, Codex-Pragmatic, Codex-Requirements
- **Severity**: important
- **Concern**: The new awk multibyte-regex lint is planned only for Makefile/local wiring, not the pre-commit source of truth used by CI `make lint-only` and `relevant-checks`, so PR-time enforcement can miss violations.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add a local always_run pre-commit hook for scripts/lint-awk-multibyte-regex.sh beside lint-bare-grep-probe
  - From Cursor-Edge, Codex-Edge: Also add a local pre-commit hook for lint-awk-multibyte-regex with pass_filenames false and always_run true, mirroring lint-bare-grep-probe
  - From Codex-Innovation: Add a local pre-commit hook beside lint-bare-grep-probe with pass_filenames false and always_run true, or otherwise make the CI lint job invoke the new repo scan
  - From Codex-Pragmatic: Add a local always_run pre-commit hook for scripts/lint-awk-multibyte-regex.sh next to lint-bare-grep-probe with pass_filenames false, then keep the Makefile target as the local convenience wrapper
  - From Codex-Requirements: Add a .pre-commit-config.yaml always_run/pass_filenames:false hook for lint-awk-multibyte-regex or equivalent enforced CI/relevant-checks wiring, and update docs/linting.md to document the new linter contract and coverage.

### FINDING_3: Successful stage/push can still return failure after HEAD advances
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The planned HEAD comparison can make `run_ci_fix_vendor` return failure after a successful stage/push when baseline and final HEAD differ, because the failing equality test is the function’s last command.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: After the no-commit branch, add `return 0` (or `return` with captured `_stage_and_push_ci_fixes` rc)

### FINDING_4: HEAD non-advance check can mask stage/push failures
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The planned HEAD equality branch is not gated on `_stage_and_push_ci_fixes` success, so a failed lint-fix, stage, or push path with unchanged HEAD can be misreported as `first-fixer-non-health` exit-3 behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Only run the HEAD comparison when `_stage_and_push_ci_fixes` returns 0 (`if ! _stage_and_push_ci_fixes …; then return $?; fi` then HEAD check)
  - From Cursor-Pragmatic: Wrap the new logic in `if _stage_and_push_ci_fixes "$phase" ...; then` and only compare `baseline_head`/`final_head` inside that block; propagate `_stage` failure with `return 1` without setting `first-fixer-non-health`

### FINDING_5: New fix-loop regression test may not reach vendor fixer
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The planned `run_ship_pr_3134_vendor_exit0_no_commits` test omits sibling fix-loop preconditions, so default state can rerun CI and exit before `run_ci_fix_vendor`; breadcrumb assertions may also be ineffective without quiet breadcrumbs enabled.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Mirror sibling fix-loop cases: awk-patch state to `TRANSIENT_RETRIES=1` and `FAILED_RUN_ID=run3134` (or equivalent) before `run_subject`
  - From Cursor-Pragmatic: Mirror sibling fix-loop cases: seed `TRANSIENT_RETRIES=1` and `FAILED_RUN_ID=run3134` in the state file before invoking `ship-pr.sh`, run with `LARCH_QUIET_BREADCRUMBS=1`, and stub `run-relevant-checks-captured.sh`/`git-push.sh`/`lint-fix-loop.sh` like `vendor_verify_local_pass` (~3494-3503)

### FINDING_6: Test strategy names a likely non-violating file
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: latent
- **Concern**: The plan’s `make lint` failure claim appears to target `lint-readability-preamble.sh`, but that file’s em-dash is in a `grep -Ec` pattern rather than the planned awk regex surfaces, so the new lint likely will not flag it on current `main`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Revise testing strategy to name actual expected violators (post-#3144 awk sites) or drop the preamble claim

### FINDING_7: New lint scripts may fail agent-lint allowlist
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: The new lint quartet is not added to the `agent-lint.toml` allowlist, unlike sibling lint scripts, so `make agent-lint` or relevant checks can fail on the added lint and test files.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add the four new paths to `agent-lint.toml` with a short comment matching the `lint-bare-grep-probe` block (~143-146, ~878-881)

### FINDING_8: Lint scope misses the original dynamic POSIX-class awk failure
- **Reviewer(s)**: Cursor-Requirements, Cursor-dyn-detection-scope-fit, Codex-dyn-detection-scope-fit
- **Severity**: important
- **Concern**: The feature description’s fix target includes the mawk `[[:space:]]` dynamic-regex portability failure, but the planned lint primarily detects multibyte UTF-8/non-ASCII cases; ASCII-only POSIX bracket expressions in dynamic awk regexes could remain lint-clean.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Align lint scope with fix #1 (add a `[[:`-in-dynamic-awk rule or rename/issue-scope explicitly) or document that #3134 defers mawk class-portability to a follow-up
  - From Cursor-dyn-detection-scope-fit, Codex-dyn-detection-scope-fit: Revise the lint plan to target the root cause: detect POSIX bracket expressions such as `[[:space:]]` inside dynamic awk regex string arguments at `match`/`gsub`/`sub`/`split`/`~`/`!~`, and add an ASCII-only fixture for that case. Keep non-ASCII detection only if the plan explicitly justifies it as separate needed hardening.

### FINDING_9: Existing vendor success tests may now trip no-commit failure branch
- **Reviewer(s)**: Cursor-dyn-stage-push-reachability, Codex-dyn-stage-push-reachability
- **Severity**: important
- **Concern**: The plan adds a no-commit failure branch but does not adjust existing vendor tier-order success tests that currently exit 0 without advancing HEAD, so those happy-path tests may be rerouted to `first-fixer-non-health` and fail their rc 0 assertions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-stage-push-reachability, Codex-dyn-stage-push-reachability: Keep the new regression, but adjust the tier-order happy-path fixtures so the winning launcher produces a real commit, for example modify a tracked file and override git-commit.sh to run git commit, or otherwise isolate these tests from the new no-commit behavior while preserving their launcher-order assertions
