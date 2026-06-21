### FINDING_1: Per-hook FD-3 inline contract missing for SessionStart and Stop hooks
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic
- **Severity**: blocking
- **Concern**: The plan fully specifies the per-hook FD-3 contract only for `deny-edit-write.sh`. If `lib-quiet.sh` is removed without equivalent per-hook routing, `sessionstart-health.sh` (conditional `larch_quiet_init` / stdout fallback in stripped-PATH harness runs), `hook-stop-fail-close.sh` (always quiet-inits then `emit()` for Stop `decision:block` JSON), and related hook contract streams break: SessionStart advisories, `make test-sessionstart-health` stdout cases, and post-`/review` halt protection via Stop block output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Extend the blocking hook FD-3 section to cover sessionstart-health.sh (conditional redirect plus stdout fallback when init skipped) and skills/implement/scripts/hook-stop-fail-close.sh (inline exec 3>&1 plus hook_emit for block JSON); keep make test-sessionstart-health and hooks.json Stop behavior in Testing strategy
  - From Cursor-Pragmatic: Extend the `hook-stop-fail-close.sh` ### UPDATED section with the same minimal per-hook FD-3 inline contract as `deny-edit-write.sh` (one-time stdout dup to FD 3, local `hook_emit`, route every `emit` call through it); document in SECURITY.md alongside deny-edit-write


### FINDING_3: lint-awk-multibyte-regex scope conflicts with preserved .awk coverage
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: The plan narrows `lint-awk-multibyte-regex` discovery to residual Bash manifest paths, but the manifest only lists `.sh` and `.inc.bash` while the test plan says to preserve standalone `.awk` coverage. Implemented literally, standalone `.awk` files stop being scanned or the preserved harness fails.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Revise the linter plan to scan residual manifest .sh/.inc.bash plus existing tracked .awk targets, or explicitly delete/retire all standalone .awk files and update the test/doc contract accordingly.

