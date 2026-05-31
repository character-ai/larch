Verifying cited locations to normalize merged concerns accurately.
### FINDING_1: manifest-outside-orchestrator fixture conflicts with carryover guard
- **Reviewer(s)**: Cursor-Arch, Cursor-Edge, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The testing strategy keeps `manifest-outside-orchestrator` (`skills/review-and-fix/scripts/test-review-and-fix.sh:482-501`) expecting exit 2, `CODER_STATUS=failed`, and no round commit, but the proposed production path passes `round_dir` and snapshots pre-dispatch dirty `other.txt` at `review-and-fix.sh:1235-1237`, then excludes unchanged carryover from the manifest guard. With the same setup as planned `work_carryover_orchestrator` (pre-dispatch dirty `other.txt`, coder only touches `src/main.py`), production should succeed (exit 0, `CODER_STATUS=applied`, scoped commit on `src/main.py` only). After the fix, `make test-review-and-fix` fails or duplicates a passing carryover case even when production behavior is correct; implementers may chase a spurious regression unless the fixture and testing-strategy bullets are updated.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Repurpose manifest-outside-orchestrator to assert genuine outside-manifest fail-closed (e.g. clean other.txt at dispatch and a TEST_AGENT_BEHAVIOR stub that dirties a tracked path not present in coder-stage-paths.txt, or break the carryover snapshot so other.txt is dirty but not carryover); drop the Testing strategy claim that this case stays unchanged
  - From Cursor-Edge: Repurpose manifest-outside-orchestrator (e.g. custom stub also mutates other.txt so diff ≠ snapshot, or add a non-snapshotted dirty path) to keep an integration fail-closed case; drop the "unchanged manifest-outside-orchestrator" line from the testing strategy
  - From Cursor-Pragmatic: Repurpose manifest-outside-orchestrator to expect exit 0, CODER_STATUS=applied, round commit on src/main.py only, and carryover warning (or delete it as redundant with carryover-orchestrator). Update the Testing strategy bullet that says this case stays unchanged. Keep fail-closed coverage via unchanged single-arg manifest-outside-guard plus extracted negative control (snapshot deleted / path mutated)

### FINDING_2: Post-commit residue helper must not skip manifest-listed hook dirt
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: Planned `round_has_non_carryover_tracked_residue` (`review-and-fix.sh:564-577` integration) skips every manifest-listed path via `grep -Fxq "$path" "$manifest" && continue`, but post-commit follow-up must still run when a manifest path is dirty again (e.g. pre-commit hook re-touch on `src/main.py` after the scoped primary commit). If the helper returns 1 for that residue, lines 564-577 skip follow-up and line 574 never fails—regressing `round-hook-residue` / `round-persistent-hook-residue` while the plan claims hook behavior is preserved.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Remove the manifest `grep` skip from the post-commit helper; warn-and-continue only for `path_is_pre_coder_carryover`. Prefer walking `capture_round_tracked_paths` (same source as the pre-commit guard) instead of porcelain `${line:3}`. Update `review-and-fix.md` residue text to match

### FINDING_3: Residue path extraction may diverge from pre-commit guard on renames/quotes
- **Reviewer(s)**: Cursor-Edge
- **Severity**: latent
- **Concern**: Planned post-commit residue in `round_has_non_carryover_tracked_residue` (`review-and-fix.sh:63-82`) parses porcelain with `path=${line:3}` while the pre-commit guard uses `capture_round_tracked_paths`. On rename or quoted paths (e.g. `R/old -> new`), residue can be mis-parsed or missed by `grep -Fxq` against the manifest while still appearing in `git diff`, so follow-up/skip behavior diverges from the guard.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Accept as #3272 out-of-scope only if documented; otherwise align extraction with capture_round_tracked_paths for residue checks or document rename/space paths as unsupported
