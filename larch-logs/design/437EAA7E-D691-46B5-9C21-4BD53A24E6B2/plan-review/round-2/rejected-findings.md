### [Plan Review] FINDING_3

### FINDING_3: Residue path extraction may diverge from pre-commit guard on renames/quotes
- **Reviewer(s)**: Cursor-Edge
- **Severity**: latent
- **Concern**: Planned post-commit residue in `round_has_non_carryover_tracked_residue` (`review-and-fix.sh:63-82`) parses porcelain with `path=${line:3}` while the pre-commit guard uses `capture_round_tracked_paths`. On rename or quoted paths (e.g. `R/old -> new`), residue can be mis-parsed or missed by `grep -Fxq` against the manifest while still appearing in `git diff`, so follow-up/skip behavior diverges from the guard.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Accept as #3272 out-of-scope only if documented; otherwise align extraction with capture_round_tracked_paths for residue checks or document rename/space paths as unsupported

