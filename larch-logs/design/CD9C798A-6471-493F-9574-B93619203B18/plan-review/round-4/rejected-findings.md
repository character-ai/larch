### [Plan Review] FINDING_2

### FINDING_2: In-repo relocation case missing round parent before snapshot helper
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: The proposed in-repo relocation case does not create the round parent before calling `pre_coder_snapshot_dir`. `parent_abs` uses `cd "$(dirname "$round_dir")" && pwd -P`; without `mkdir -p` for `$PWD/implement` (or `round-1`), `cd` fails, `parent_abs` stays a relative `implement`, the `$PWD` match may not apply, and assertions that `snap_dir` lives under `${TMPDIR}/larch-pre-coder-snapshots/` can fail or hit the default branch instead of the relocation path under test.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add `mkdir -p "$PWD/implement/round-1"` (or at least `$PWD/implement`) after `cd` into the work repo and before `eval`/`pre_coder_snapshot_dir`

