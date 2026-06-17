### FINDING_2: Finalize marker printing can abort before teardown under `set -e`
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: The plan folds marker printing with closing token/timing marks and `implement-finalize teardown` under the same `set -euo pipefail` script as retirees. A failed `cat` of `summary-final.md` (mirroring `step-16-17.sh` `print_summary_markers`) can exit before token/timing marks and teardown, leaving `$IMPLEMENT_TMPDIR` and session pointers uncleared (#3425 violation).
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Wrap marker printing in `set +e` (or `cat ... || true`) and always run closing marks, `_restore_finalize`, and teardown afterward, matching `step-16-17.sh` non-aborting marker behavior.


