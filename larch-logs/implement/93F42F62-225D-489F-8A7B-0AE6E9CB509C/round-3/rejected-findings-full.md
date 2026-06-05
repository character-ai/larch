### [rejected] FINDING_13

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_13: Marker-delete failure after successful restore can reintroduce stale-marker resume loops
- **Reviewer(s)**: dyn-resume-state-output.txt, dyn-pr-identity-output.txt
- **Severity**: important
- **Concern**: If restore succeeds but pause-marker deletion fails, `LOAD_OK=true` / `MARKER_CLEARED=false` still allows `ROUTE=resume@*`, leaving GitHub issue state stale and enabling later invocations to re-load old snapshots.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-resume-state-output.txt: Either treat post-success marker-delete failure as a hard operator gate (`LOAD_OK=false` with a dedicated `ERROR=marker-delete-failed` while keeping restored files), or have `design-route.sh` skip re-load when `.resume-loaded` is already present in the active tmpdir and the marker still exists.
  - From dyn-pr-identity-output.txt: Treat `MARKER_CLEARED=false` as a hard integration gate before `ROUTE=resume@*` (fail closed with a loud operator-visible warning and manual marker-repair instructions), or have `design-route.sh` retry `clear_pause_marker` once before routing; at minimum, surface `**⚠ ... marker-delete-failed; clear larch:design-pause manually before continuing**` in the orchestrator resume path.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_21

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_21: Restore destination lacks canonical containment check
- **Reviewer(s)**: dyn-git-restore-output.txt
- **Severity**: important
- **Concern**: The per-file restore assembles destination paths manually and filters obvious traversal, but does not prove canonical parent containment under the staging directory.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-git-restore-output.txt: After building `dest`, reject unless `realpath`/`pwd -P` containment proves the resolved parent directory stays under `$restore_tmp`, mirroring the publish-side ancestor guard.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_6: Restore path handling may execute unsafe tree path content
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: Per-file restore uses git tree paths in shell contexts without a strict safe-character validation step, raising a command-substitution risk from malicious snapshot path names.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Validate each relative path against a strict safe-character allowlist before any double-quoted use, or restore via git checkout-index/read-tree without per-path shell expansion; add a regression test with a committed $(…) path component.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0

