### [Plan Review] FINDING_2

### FINDING_2: Helper edit-in-sync metadata still points to SKILL.md procedure
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The helper documentation’s Edit-in-sync lists still identify the Step 9a.1 procedure as living in SKILL.md even though the plan moves executable procedure to `skills/implement/references/oos-pipeline.md`, risking future helper/procedure drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Replace the Edit-in-sync Step 9a.1 procedure bullet in both helper .md files with skills/implement/references/oos-pipeline.md; keep the SKILL.md narrative bullet for triage policy only


### [Plan Review] FINDING_6

### FINDING_6: Security OOS routing predicate diverges from existing canonical token
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Concern**: The proposed security-routing predicate recognizes only dedicated `- **focus-area**:` field lines, while existing security policy and voting contracts define security OOS using unfenced `focus-area\s*=\s*security`, allowing some security-tagged OOS to be publicly filed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Keep Step 9a.1 aligned with SECURITY.md/lib-vote-tally for public-filing exclusion, or update SECURITY.md, voting-protocol.md, lib-vote-tally docs/tests, and the gate predicate together so there is one canonical security OOS predicate.


### [Plan Review] FINDING_8

### FINDING_8: Checkpoint script cannot accept arbitrary filed-URLs sidecar flag
- **Reviewer(s)**: Codex-dyn-cross-ref-integrity
- **Severity**: important
- **Concern**: `oos-disposition-checkpoint.sh` rejects unknown arguments and always forwards only `$IMPLEMENT_TMPDIR/oos-issues-created.md` to the gate, so documentation that instructs callers to pass `--filed-urls-file` to the checkpoint would fail before the gate sees the URLs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-cross-ref-integrity: Keep the new reference/test wording on fixed checkpoint-visible surfaces: write loose URL evidence to $IMPLEMENT_TMPDIR/oos-issues-created.md or rely on design - **Filed URL** lines; refer to --filed-urls-file only as a gate flag, not a checkpoint flag


