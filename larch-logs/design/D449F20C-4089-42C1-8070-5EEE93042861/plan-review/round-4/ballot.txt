### FINDING_1: Assessor Harness Owns Gate B Prose Assertion
- **Reviewer(s)**: Codex-Arch
- **Severity**: latent
- **Concern**: Gate B passive-summary prose assertions are planned for the assessor script harness, coupling `test-assess-plan-round.sh` to approval-gate prose instead of assessor behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Move the passive-summary Continue structural assertion to `scripts/test-design-structure.sh`, which already owns SKILL.md and approval-gates.md prose pins; keep `test-assess-plan-round.sh` focused on cursor, snapshot, and assessor behavior

### FINDING_2: Re-Tally Classification Output Not Pinned To Active Round
- **Reviewer(s)**: Cursor-Edge, Codex-Edge
- **Severity**: important
- **Concern**: MainAgent re-tally refreshes Step 3 state without explicitly writing findings classification to the active round, so round 2+ paths can overwrite round 1 and leave current-round classification stale.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge, Codex-Edge: Add to the proposed MainAgent clauses in SKILL.md and approval-gates.md that the re-tally must pass --findings-classification-out "$DESIGN_TMPDIR/plan-review/round-${ROUNDS_COMPLETED:-$ROUND_NUM}/findings-classification.tsv" before refreshing .step3-plan-review-result.env

### FINDING_3: Step 3.5 Entry Text Misses Gate-B-Bypass Short-Circuits
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The Step 3.5 entry blockquote still exempts only `cap-reached`, while other tally short-circuits are planned to bypass Gate B and Step 3.6 before Step 3b.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Extend the blockquote exception to all Gate-B-bypass short-circuits (or cross-reference the branch matrix) and state that those paths bypass Step 3.5 and Step 3.6 before Step 3b

### FINDING_4: Test Helper Duplicates Production Cursor Logic
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: nit
- **Concern**: The planned integration test inlines Step 3 cursor arithmetic already implemented by `snapshot-plan-round.sh`, creating drift risk between the harness and production behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Call snapshot-plan-round.sh read-cursor / write-cursor in the case instead of inlining cursor arithmetic

### FINDING_5: Cap-Reached Per-Tier Paragraph Still Implies Direct Gate C
- **Reviewer(s)**: Cursor-dyn-cross-doc-sync, Codex-dyn-cross-doc-sync
- **Severity**: latent
- **Concern**: The plan updates cap-reached routing lists but leaves a per-tier cap paragraph implying Step 3 short-circuits directly to Gate C, conflicting with the planned Step 3b -> Step 4 -> Gate C route and Step 3.6 skip.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-cross-doc-sync, Codex-dyn-cross-doc-sync: Include the cap-reached Step 3b -> Step 4 -> Gate C route and Step 3.6 skip in the per-tier cap paragraph, or replace the direct-Gate-C wording with the same route used in Gate C When.

### FINDING_6: Passive-Summary Continue Wording Drifts Across Files
- **Reviewer(s)**: Cursor-dyn-cross-doc-sync, Codex-dyn-cross-doc-sync
- **Severity**: latent
- **Concern**: The planned SKILL.md and approval-gates.md wording for passive-summary Continue is not identical, leaving ambiguity about Step 3.6, Step 3b, Gate C, and later re-run ordering.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-cross-doc-sync, Codex-dyn-cross-doc-sync: Use one shared sentence in both files, e.g. Passive-summary Continue routes through Step 3.6 before Step 3b, then Step 4 and Gate C; any Gate C re-run is a later fresh Step 3 entry.

### FINDING_7: Branch Matrix Omits Step 3.6 Dispositions For Some LOOP_STATUS Values
- **Reviewer(s)**: Cursor-dyn-status-matrix, Codex-dyn-status-matrix
- **Severity**: important
- **Concern**: The plan does not explicitly assign Step 3.6 routing for `LOOP_STATUS=complete`, `revision-failed`, and `emit-plan-failed`, despite requiring every Step 3 exit path to have a disposition.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-status-matrix, Codex-dyn-status-matrix: Add one minimal route-through bullet naming LOOP_STATUS=complete|revision-failed|emit-plan-failed as Gate B-settled paths that proceed through Step 3.6 after Gate B and Step 2b.5 return.

### FINDING_8: Tally-Only Statuses Missing Step 3.6 Routing
- **Reviewer(s)**: Cursor-dyn-status-matrix, Codex-dyn-status-matrix
- **Severity**: important
- **Concern**: The plan omits explicit Step 3.6 dispositions for `TALLY_PLAN_REVIEW_STATUS=skipped-empty-findings` and `skipped-cap-reached`, leaving all-empty review output and cap-entry bypass routing incomplete.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-status-matrix, Codex-dyn-status-matrix: Add TALLY_PLAN_REVIEW_STATUS=skipped-empty-findings to the zero-findings route-through text, and TALLY_PLAN_REVIEW_STATUS=skipped-cap-reached to the cap-reached skip text.
