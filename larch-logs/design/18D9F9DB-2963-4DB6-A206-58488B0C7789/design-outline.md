## Proposed Design Outline

### Goals
- Restore end-to-end `/design` pause/resume in the larch dev repo by fixing all three defects together.
- Make pause-publish succeed when the driver has written `.completed/` phase sentinels.
- Make resume restore snapshot files despite `export-ignore`, and stop destroying the resume pointer on transient restore failure.

### Non-goals
- Do NOT weaken the committed `larch-logs/ export-ignore` (protects shipped plugin archives).
- No broader pause/resume re-architecture and no sentinel/turn restructuring (leave #3422's turn-folding capstone untouched).
- No consumer-repo behavior change beyond the fix (consumer repos without the gitattribute already resume fine).

### Approach sketch
- WI1: allowlist driver phase names (`emit_plan`, `tally`, `finalize`, `validate_plan_commands`) alongside `step-*` in `design-log-publish.sh`'s `.completed/` validation loop.
- WI2: replace `git archive | tar` in `design-pause-load.sh` with `git ls-tree -r <ref> -- larch-logs/design/<RUN_ID>/` enumeration + `git show <ref>:<path>` per file into staging (strip the 3-component prefix) — attribute-independent.
- WI3: in `design-pause-load.sh`, keep the marker on all restore/extract/snapshot failures; delete only after a successful install; surface (WARN) a post-success delete failure instead of swallowing it.
- Add/extend regression coverage for each defect (publisher harness + pause/resume harness).

### Surfaces in scope
- `scripts/design-log-publish.sh` (+ sibling `.md`, `scripts/test-design-log-publish.sh`)
- `scripts/design-pause-load.sh` (+ sibling `.md`)
- `skills/design/scripts/test-design-pause-resume.sh` (resume harness)

### Open questions
- None. (WI1/WI2/WI3 approaches were resolved in Step 1c.)
