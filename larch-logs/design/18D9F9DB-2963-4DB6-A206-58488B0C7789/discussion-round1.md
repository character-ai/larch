## Decision 1: Scope — all three work items in one plan
- **Question**: Should the design cover all 3 pause/resume defects, or a subset?
- **Resolution**: One plan covering all 3 work items (publisher sentinel rejection, git-archive export-ignore, marker-deletion policy). They are one issue ("pause/resume broken end-to-end") and must land together to restore end-to-end resume in the larch dev repo.
- **Source**: codebase + issue

## Decision 2: WI1 fix approach — allowlist driver phase names in the publisher
- **Question**: How should `design-log-publish.sh` stop rejecting the driver's `.completed/` phase sentinels (`emit_plan`, `tally`, `finalize`, `validate_plan_commands`)?
- **Resolution**: Allowlist the known driver phase names alongside `step-*` in `design-log-publish.sh`'s `.completed/` validation. Single-file fix; phase sentinels stay published & restored (preserves driver resume fidelity). `design-driver.sh` and `test-design-driver.sh` untouched. (`design-pause-save.sh`'s resume walk only reads `.completed/step-N` registry steps, so it is unaffected by either choice.)
- **Source**: user

## Decision 3: WI2 fix approach — attribute-independent extraction via git ls-tree + git show
- **Question**: How should snapshot restore avoid `git archive` honoring `larch-logs/ export-ignore`?
- **Resolution**: Replace `git archive | tar` with `git ls-tree -r <ref> -- larch-logs/design/<RUN_ID>/` enumeration + `git show <ref>:<path>` per file into the staging tmpdir (stripping the 3-component `larch-logs/design/<RUN_ID>/` prefix). Attribute-independent, scoped to the snapshot subtree. The committed `larch-logs/ export-ignore` MUST NOT be weakened.
- **Source**: user

## Decision 4: WI3 marker-deletion policy — keep on failure, delete on success
- **Question**: What marker-deletion policy should `design-pause-load.sh` use?
- **Resolution**: Never delete the pause marker on any restore/extract/snapshot-content failure (all retryable — preserve the resume pointer). Delete the marker only after a successful install, and surface a post-success delete failure as a WARN instead of swallowing it. Matches the documented `design-pause-load.md` contract. (`design-route.sh` relies on the loader to delete the marker; it does not delete it itself.)
- **Source**: user

## Hard constraints (must not break)
- Do NOT weaken the committed `larch-logs/ export-ignore` in `.gitattributes` (it protects shipped plugin archives).
- Keep `test-design-driver.sh` (fixtures `.completed/emit_plan`) and `test-design-pause-resume.sh` green / consistent with the chosen sentinel handling.
- Preserve driver resume fidelity: published `.completed/` phase sentinels must restore correctly so `design-driver.sh`'s skip-on-replay logic for FINALIZE/TALLY stays correct.
- Single-runner / single-`/design` invariants and existing `design-log-publish.sh` security validations (no symlinks under `.completed/`, path-within-root) must remain intact.

## Testing requirement (must-have)
- Add regression coverage for each defect: publisher accepts driver phase sentinels; restore extracts snapshot files despite `export-ignore`; marker survives a transient restore/extract failure and is deleted (with surfaced failure) on success.
