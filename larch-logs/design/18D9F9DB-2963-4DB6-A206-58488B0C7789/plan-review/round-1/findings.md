### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/test-design-pause-resume.sh:781-790
- **Concern**: WI3 harness gap: unloadable-snapshot case still asserts marker deletion on failure. Scenario: Plan removes emit_load_fail delete-on-failure but leaves the unloadable snapshot test expecting a cleared marker; make lint fails after WI3 lands or the regression silently re-encodes the old polarity
- **Proposed resolution**: Rename/rewrite the unloadable-snapshot block to assert the marker remains on snapshot-extract-failed; add it explicitly to the WI3 test bullets alongside the missing-restored-artifact case

### FINDING_2:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/design-pause-load.sh:233-235
- **Concern**: WI2 loop must not let set -e bypass emit_load_fail. Scenario: Under set -euo pipefail a failing git ls-tree or mid-loop git show exits the script with rc!=0 instead of LOAD_OK=false ERROR=snapshot-extract-failed exit 0; design-route records design-pause-load-failed and loses the structured ERROR token
- **Proposed resolution**: Add an explicit WI2 note: wrap ls-tree and each git show in if ! ...; then emit_load_fail snapshot-extract-failed; fi or disable set -e inside the extraction loop

### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/test-design-pause-resume.sh:781-791
- **Concern**: WI3 harness omits the unloadable-snapshot case that still expects marker deletion and snapshot-extract-failed. Scenario: After ls-tree/show restore, deleting the snapshot tree yields empty enumeration and missing-restored-artifact while WI3 keeps the marker; the harness still fails on the inverted contract
- **Proposed resolution**: Rename/rewrite the case to assert marker retention and ERROR=missing-restored-artifact (or a forced extract failure if that path is still tested separately)

### FINDING_4:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: SECURITY.md:88-104
- **Concern**: WI3 inverts failure-path marker deletion and WI2 replaces git archive restore but the plan omits SECURITY.md. Scenario: SECURITY.md still says the loader deletes the marker before install and best-effort clears it on snapshot-not-found/extract/missing-artifact failures; post-PR docs contradict runtime and AGENTS.md requires security-doc updates for this behavior
- **Proposed resolution**: Add ### UPDATED: SECURITY.md: revise the pause/resume binding paragraph to match install-then-delete on success, keep-marker-on-retryable failure, ls-tree/show restore, and WARN=marker-delete-failed

### FINDING_5:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/test-design-pause-resume.sh:781-790
- **Concern**: WI3 harness gap for snapshot-extract-failed marker retention. Scenario: Plan inverts marker lifecycle but still leaves unloadable snapshot clears marker asserting deletion on ERROR=snapshot-extract-failed; implementing WI3 breaks this test or reintroduces defect #3
- **Proposed resolution**: Add explicit WI3 step: rename/flip this case to assert marker is kept on snapshot-extract-failed (mirror missing-restored-artifact retention)

### FINDING_6:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/test-design-pause-resume.sh:514-521
- **Concern**: WI3 harness gap for successful body-drift load. Scenario: WI3 deletes marker after any successful install; body-drift path is LOAD_OK=true so marker must be removed, but plan only lists flipping line 192 and omits this case
- **Proposed resolution**: Extend WI3 regression bullets: assert marker absent after successful body-drift restore (LOAD_OK=true WARN=body-drift)

### FINDING_7:
- **Reviewer(s)**: Cursor-dyn-contract-sync
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/test-design-pause-resume.sh:514-521
- **Concern**: WI3 regression plan names only the round-trip assertion at line 192; it omits the body-drift success case that also asserts the pause marker remains after LOAD_OK=true. Scenario: After WI3 deletes the marker on every successful load, the body-drift test still expects the marker in the issue body and will fail make lint / test-design-pause-resume
- **Proposed resolution**: Add the body-drift block to the WI3 harness bullet: assert the marker is absent after LOAD_OK=true with WARN=body-drift (mirror the line 192 flip)

### FINDING_8:
- **Reviewer(s)**: Cursor-dyn-call-site-completeness
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/test-design-pause-resume.sh:781-791
- **Concern**: WI3 test plan omits unloadable-snapshot block that asserts marker cleared on snapshot-extract-failed. Scenario: Correct WI3 loader keeps marker on extract failure but harness still expects deletion at line 790; CI fails or implementer must discover the gap ad hoc
- **Proposed resolution**: Add to plan WI3 test bullets: rename/update === unloadable snapshot clears marker === to assert LOAD_OK=false ERROR=snapshot-extract-failed and marker remains (invert line 790 assertion)

### FINDING_9:
- **Reviewer(s)**: Cursor-dyn-call-site-completeness
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/test-design-pause-resume.sh:521
- **Concern**: WI3 test plan omits body-drift success marker assertion. Scenario: Successful load with body-drift WARN deletes marker per WI3 but line 521 still requires marker kept
- **Proposed resolution**: Add to plan WI3 test bullets: flip body-drift block to assert marker removed after LOAD_OK=true (same polarity as line 192 round-trip flip)

### FINDING_10:
- **Reviewer(s)**: Cursor-dyn-bash-portability
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/design-pause-load.sh:4-15
- **Concern**: WI2 does not pin a set -euo pipefail-safe enumeration loop; piping ls-tree into while read runs the loop in a subshell and can abort on read EOF. Scenario: The loader uses set -euo pipefail (line 4). A common git ls-tree … | while IFS= read -r -d '' path loop makes emit_load_fail exit only the subshell (parent continues with a partial restore_tmp), and with pipefail an EOF read after the last NUL record can make the pipeline non-zero and abort before missing-restored-artifact — including when enumeration is empty
- **Proposed resolution**: In WI2 spell the loop as while IFS= read -r -d '' path; do …; done < <(git -C "$REPO_TOP" ls-tree -r -z --name-only "$archive_ref" -- "larch-logs/design/$RUN_ID/") (same pattern as scripts/design-log-publish.sh:609), wrap each git show in if ! …; then emit_load_fail snapshot-extract-failed; fi, and pin prefix strip as prefix=larch-logs/design/${RUN_ID}/ then rel=${path#"$prefix"} with [[ "$rel" == "$path" ]] && emit_load_fail snapshot-extract-failed before writing
