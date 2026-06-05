### [Plan Review] FINDING_2

### FINDING_2: Codex-primary reviewer `.txt.json` sidecars remain publishable
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Concern**: The plan omits `codex-primary-plan-*-output*.txt.json` from the design artifact denylist. Waterfall phase-2 and retry paths can produce Codex-primary output files that Cursor processes, and `launch-review.sh` copies Cursor bytes to `${OUTPUT}.json`; those JSON sidecars can still be committed after transcript exclusion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Add codex-primary-plan-*-output*.txt.json to the new deny branch; pin codex-primary-plan-arch-output-phase2.txt.json (or -ns-retry) in scripts/test-design-log-publish.sh; update design-log-publish.md / SECURITY.md; drop the dead-pattern claim in the plan Edge cases section


### [Plan Review] FINDING_3

### FINDING_3: Dirty-tree auxiliary sidecars are not covered
- **Reviewer(s)**: Codex-dyn-artifact-taxonomy
- **Severity**: latent
- **Concern**: Dirty-tree auxiliary files such as `${OUTPUT}.dirty-tree.tracked-paths` and `${OUTPUT}.dirty-tree.new-untracked-paths` are producer-backed operational path artifacts but are not matched by the existing `*.dirty-tree` / `*.untracked-baseline` denylist or the proposed sidecar list.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-artifact-taxonomy: Add *.dirty-tree.tracked-paths and *.dirty-tree.new-untracked-paths to the existing suffix denylist, or add prefix-scoped cursor-plan-*-output*.txt.dirty-tree.tracked-paths and .new-untracked-paths arms, with publish-test fixtures


### [Plan Review] FINDING_6

### FINDING_6: Sidecar deny patterns may miss phased output names
- **Reviewer(s)**: Cursor-dyn-fixture-realism
- **Severity**: important
- **Concern**: The planned sidecar deny arms do not explicitly require the `*-output*.txt.<suffix>` anchor used by real transcript names. If implemented as `*-output.txt.<suffix>`, phased names such as `cursor-plan-arch-output-phase2.txt.meta` and `codex-primary-plan-arch-output-phase2.txt.tsv` would remain publishable.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-fixture-realism: State in design_artifact_excluded() that every new sidecar arm uses cursor-plan-*-output*.txt.<suffix> / codex-primary-plan-*-output*.txt.<suffix> / claude-plan-*-output*.txt.<suffix>, not *-output.txt.<suffix>


