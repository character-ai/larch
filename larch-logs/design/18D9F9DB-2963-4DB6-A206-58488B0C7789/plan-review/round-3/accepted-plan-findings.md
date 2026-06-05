### FINDING_1: Real-git export-ignore case omits cwd binding for git restore
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: In the real-git export-ignore harness case, `design-pause-load.sh` resolves `REPO_TOP` via `git rev-parse --show-toplevel` from the caller’s cwd while `--repo` only threads `gh`. A subshell that drops the git stub but does not `cd` into `$TMP/export-ignore-repo` can still run `git restore` against the wrong worktree, so the case may pass or fail for the wrong reason and never proves export-ignore independence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In the stub-free subshell, `cd` into the initialized export-ignore repo (or equivalent) before invoking `$LOAD`, and keep `gh` stubbed for issue-body IO


### FINDING_2: WI2 `ls-tree` failure not captured when using process substitution
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-dyn-bash-compat
- **Severity**: important
- **Concern**: WI2 mixes a pre-loop `ls-tree` failure guard with unguarded process substitution. Under `set -euo pipefail`, `while … done < <(git ls-tree …)` does not surface a non-zero `ls-tree` exit as the loop compound’s status: a failed `ls-tree` (bad ref or stub-forced failure) can yield an empty enumeration with exit status 0, so the loader reports `missing-restored-artifact` or an opaque `rc!=0` instead of the planned `snapshot-extract-failed`, bypassing failure-mode #4’s structured `ERROR` contract and contradicting the `GIT_STUB_LS_TREE_FAIL` fixture.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Spell out one pattern: run `git ls-tree` into a guarded temp/NUL buffer with `if ! …; then emit_load_fail …; fi`, then iterate that buffer; do not rely on substitution/pipefail alone for `ls-tree` failure
  - From Cursor-Innovation: Run ls-tree once with an explicit if ! git … ls-tree … guard (or capture its exit status before the read loop) and call emit_load_fail snapshot-extract-failed on non-zero before artifact checks treat an empty enumeration as missing-restored-artifact
  - From Cursor-dyn-bash-compat: Capture once to a mktemp file with an explicit `if ! git -C "$REPO_TOP" ls-tree -r -z --name-only "$archive_ref" -- "larch-logs/design/$RUN_ID/" >"$enum_tmp"; then emit_load_fail "snapshot-extract-failed"; fi`, then `while IFS= read -r -d '' path; do …; done <"$enum_tmp"` (same shape as `scripts/scrub-log-secrets.sh:176-185`); keep per-path `if ! git show …` guards as planned

---

**Merge notes (diagnostic):** FINDING_2–4 from the input all describe the same behavioral risk around `git ls-tree` + process substitution under `set -euo pipefail` in `scripts/design-pause-load.sh` (WI2); they were merged into a single `FINDING_2` with severity `important` (max across sources). FINDING_1 addresses a separate code path (export-ignore test cwd binding) and remains standalone.

