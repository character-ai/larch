### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review-and-fix/scripts/test-review-and-fix.sh:38-45
- **Concern**: Post-coder-head and 0444 mode checks allow `find -printf` as a portable pattern. Scenario: `find -printf` is GNU-only; developers on macOS (common for this repo) hit false failures when running `test-review-and-fix.sh` locally
- **Proposed resolution**: Pin the existing dual-stat idiom used elsewhere (`stat -c %a` OR `stat -f %Lp`, e.g. `scripts/test-relevant-checks-byte-budget.sh:23-26`); do not rely on `find -printf` alone

### FINDING_2:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review-and-fix/scripts/test-review-and-fix.sh:38-39
- **Concern**: Proposed in-repo relocation case omits creating the round parent before `pre_coder_snapshot_dir`. Scenario: `parent_abs` uses `cd "$(dirname "$round_dir")" && pwd -P`; without `mkdir -p` for `$PWD/implement` (or `round-1`), `cd` fails, `parent_abs` stays a relative `implement`, the `$PWD` case may not match, and assertions that `snap_dir` lives under `${TMPDIR}/larch-pre-coder-snapshots/` can fail or exercise the default branch instead of relocation
- **Proposed resolution**: Add `mkdir -p "$PWD/implement/round-1"` (or at least `$PWD/implement`) after `cd` into the work repo and before `eval`/`pre_coder_snapshot_dir`
