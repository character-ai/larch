Verifying the cited code so normalized findings match the implementation.
Two independent correctness risks in the proposed `test-review-and-fix.sh` harness changes; they are not merged because they need different fixes and exercise different failure modes.

### FINDING_1: GNU-only `find -printf` breaks macOS local runs
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: Post-coder-head and 0444 mode checks treat `find -printf` as portable. `find -printf` is GNU-only; on macOS (common for this repo), `test-review-and-fix.sh` can fail spuriously when developers run the harness locally.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Pin the existing dual-stat idiom used elsewhere (`stat -c %a` OR `stat -f %Lp`, e.g. `scripts/test-relevant-checks-byte-budget.sh:23-26`); do not rely on `find -printf` alone

### FINDING_2: In-repo relocation case missing round parent before snapshot helper
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: The proposed in-repo relocation case does not create the round parent before calling `pre_coder_snapshot_dir`. `parent_abs` uses `cd "$(dirname "$round_dir")" && pwd -P`; without `mkdir -p` for `$PWD/implement` (or `round-1`), `cd` fails, `parent_abs` stays a relative `implement`, the `$PWD` match may not apply, and assertions that `snap_dir` lives under `${TMPDIR}/larch-pre-coder-snapshots/` can fail or hit the default branch instead of the relocation path under test.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add `mkdir -p "$PWD/implement/round-1"` (or at least `$PWD/implement`) after `cd` into the work repo and before `eval`/`pre_coder_snapshot_dir`
