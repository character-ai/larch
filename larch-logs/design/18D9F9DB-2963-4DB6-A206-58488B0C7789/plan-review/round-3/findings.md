### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/test-design-pause-resume.sh:140-40
- **Concern**: Real-git export-ignore case omits cwd binding for git restore. Scenario: `design-pause-load.sh` resolves `REPO_TOP` via `git rev-parse --show-toplevel` from the caller cwd; `--repo` only threads `gh`. A subshell that drops the git stub but does not `cd` into `$TMP/export-ignore-repo` still restores from the wrong worktree, so the case may pass/fail for the wrong reason and never prove export-ignore independence
- **Proposed resolution**: In the stub-free subshell, `cd` into the initialized export-ignore repo (or equivalent) before invoking `$LOAD`, and keep `gh` stubbed for issue-body IO

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/design-pause-load.sh:13-17
- **Concern**: WI2 mixes pre-loop `ls-tree` failure guard with unguarded process substitution. Scenario: The plan requires `emit_load_fail "snapshot-extract-failed"` before enumeration when `ls-tree` fails, but the proposed loop uses bare `< <(git ls-tree …)` while only `git show` gets an explicit `if !`. Under `set -euo pipefail` that pattern can still exit with opaque `rc!=0` (failure mode 4)
- **Proposed resolution**: Spell out one pattern: run `git ls-tree` into a guarded temp/NUL buffer with `if ! …; then emit_load_fail …; fi`, then iterate that buffer; do not rely on substitution/pipefail alone for `ls-tree` failure

### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/design-pause-load.sh:233-235
- **Concern**: WI2 prescribes ls-tree via process substitution but does not spell out how to capture a non-zero ls-tree exit under set -euo pipefail. Scenario: A failed ls-tree in while … done < <(git ls-tree …) can yield an empty loop with exit status 0 so the loader reports missing-restored-artifact instead of snapshot-extract-failed contradicting the dedicated GIT_STUB_LS_TREE_FAIL fixture and failure-mode #4
- **Proposed resolution**: Run ls-tree once with an explicit if ! git … ls-tree … guard (or capture its exit status before the read loop) and call emit_load_fail snapshot-extract-failed on non-zero before artifact checks treat an empty enumeration as missing-restored-artifact

### FINDING_4:
- **Reviewer(s)**: Cursor-dyn-bash-compat
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/design-pause-load.sh:233-235
- **Concern**: Proposed WI2 loop uses only `while … done < <(git ls-tree …)` but also requires a pre-loop `ls-tree` failure guard that process substitution cannot provide. Scenario: Under `set -euo pipefail`, `git ls-tree` non-zero inside `< <(…)>` is not the while compound’s exit status; a bad ref or stub-forced failure yields empty enumeration and `ERROR=missing-restored-artifact` instead of the planned `snapshot-extract-failed`, and failure-mode #4’s structured `ERROR` contract is bypassed
- **Proposed resolution**: Capture once to a mktemp file with an explicit `if ! git -C "$REPO_TOP" ls-tree -r -z --name-only "$archive_ref" -- "larch-logs/design/$RUN_ID/" >"$enum_tmp"; then emit_load_fail "snapshot-extract-failed"; fi`, then `while IFS= read -r -d '' path; do …; done <"$enum_tmp"` (same shape as `scripts/scrub-log-secrets.sh:176-185`); keep per-path `if ! git show …` guards as planned
