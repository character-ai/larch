### FINDING_1: WI3 harness gap — unloadable-snapshot still asserts marker deletion on extract failure
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Requirements, Cursor-dyn-call-site-completeness
- **Severity**: important
- **Concern**: The WI3 plan inverts marker lifecycle (keep marker on retryable failure) but the unloadable-snapshot regression block in `skills/design/scripts/test-design-pause-resume.sh` (~781–791) still expects the marker to be cleared on `ERROR=snapshot-extract-failed`. After WI3 lands, `make lint` / `test-design-pause-resume` will fail or the implementer will silently re-encode the old delete-on-failure polarity.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Rename/rewrite the unloadable-snapshot block to assert the marker remains on snapshot-extract-failed; add it explicitly to the WI3 test bullets alongside the missing-restored-artifact case
  - From Cursor-Innovation: Rename/rewrite the case to assert marker retention and ERROR=missing-restored-artifact (or a forced extract failure if that path is still tested separately)
  - From Cursor-Requirements: Add explicit WI3 step: rename/flip this case to assert marker is kept on snapshot-extract-failed (mirror missing-restored-artifact retention)
  - From Cursor-dyn-call-site-completeness: Add to plan WI3 test bullets: rename/update === unloadable snapshot clears marker === to assert LOAD_OK=false ERROR=snapshot-extract-failed and marker remains (invert line 790 assertion)


### FINDING_2: WI2 extraction loop unsafe under `set -euo pipefail` — structured `emit_load_fail` bypassed
- **Reviewer(s)**: Cursor-Edge, Cursor-dyn-bash-portability
- **Severity**: important
- **Concern**: WI2’s `git ls-tree` / `git show` restore loop in `scripts/design-pause-load.sh` (~233–235 and header `set -euo pipefail`) is not pinned to a failure-safe enumeration pattern. Under `set -e`, a failing `git ls-tree` or mid-loop `git show` can exit the script with `rc!=0` instead of `LOAD_OK=false ERROR=snapshot-extract-failed` exit 0; piping `ls-tree` into `while read` runs the loop in a subshell (parent may continue with a partial `restore_tmp`), and with `pipefail` an EOF read after the last NUL record can abort the pipeline before `missing-restored-artifact` handling — including on empty enumeration — so `design-route` records `design-pause-load-failed` and loses the structured `ERROR` token.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Add an explicit WI2 note: wrap ls-tree and each git show in if ! ...; then emit_load_fail snapshot-extract-failed; fi or disable set -e inside the extraction loop
  - From Cursor-dyn-bash-portability: In WI2 spell the loop as while IFS= read -r -d '' path; do …; done < <(git -C "$REPO_TOP" ls-tree -r -z --name-only "$archive_ref" -- "larch-logs/design/$RUN_ID/") (same pattern as scripts/design-log-publish.sh:609), wrap each git show in if ! …; then emit_load_fail snapshot-extract-failed; fi, and pin prefix strip as prefix=larch-logs/design/${RUN_ID}/ then rel=${path#"$prefix"} with [[ "$rel" == "$path" ]] && emit_load_fail snapshot-extract-failed before writing


### FINDING_3: SECURITY.md not updated for inverted marker lifecycle and ls-tree/show restore
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: WI3 inverts failure-path marker deletion and WI2 replaces `git archive` restore, but the plan omits `SECURITY.md`. `SECURITY.md` (~88–104) still documents delete-before-install and best-effort marker clearing on snapshot-not-found/extract/missing-artifact failures; post-PR docs would contradict runtime behavior, and `AGENTS.md` requires security-doc updates for security-relevant behavior changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add ### UPDATED: SECURITY.md: revise the pause/resume binding paragraph to match install-then-delete on success, keep-marker-on-retryable failure, ls-tree/show restore, and WARN=marker-delete-failed


### FINDING_4: WI3 harness gap — successful body-drift load still asserts marker retention
- **Reviewer(s)**: Cursor-Requirements, Cursor-dyn-contract-sync, Cursor-dyn-call-site-completeness
- **Severity**: important
- **Concern**: WI3 deletes the marker after any successful install (`LOAD_OK=true`), but the body-drift success case in `skills/design/scripts/test-design-pause-resume.sh` (~514–521) still asserts the pause marker remains after `LOAD_OK=true` with `WARN=body-drift`. The WI3 regression plan names only the round-trip assertion flip at line 192 and omits this case; after WI3, the harness will fail `make lint` / `test-design-pause-resume` or force ad-hoc discovery of the gap.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Extend WI3 regression bullets: assert marker absent after successful body-drift restore (LOAD_OK=true WARN=body-drift)
  - From Cursor-dyn-contract-sync: Add the body-drift block to the WI3 harness bullet: assert the marker is absent after LOAD_OK=true with WARN=body-drift (mirror the line 192 flip)
  - From Cursor-dyn-call-site-completeness: Add to plan WI3 test bullets: flip body-drift block to assert marker removed after LOAD_OK=true (same polarity as line 192 round-trip flip)

