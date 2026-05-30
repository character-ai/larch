### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: Duplicated marketplace remove + sparse add branches
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `upgrade-larch.sh` duplicates marketplace remove + sparse add in fallback and else branches. Future edits may update one branch only and diverge silently. Extract a shared `sparse_marketplace_readd` helper used by both branches and recovery banners.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: Sparse vs legacy clone detection is heuristic and brittle
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-sparse-clone-detection-output.txt
- **Severity**: latent
- **Concern**: Steady-state vs migration is inferred mainly from absence of `larch-logs/` (and related directory heuristics), not verified sparse-checkout state. Legacy full clones with `larch-logs/` removed, file/symlink paths named `larch-logs`, or pulls that re-materialize excluded trees can take `marketplace update` instead of one-time `remove` + `add --sparse`, leaving fat installs, ambiguous cones, or committed run logs copied back into the plugin cache. Detection should key off git sparse-checkout (or explicit markers/secondary legacy signals), not directory presence alone.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-sparse-clone-detection-output.txt: Treat any existing `larch-logs` path as legacy, e.g. `[ -e "$MARKETPLACE_CLONE/larch-logs" ]` in the `else` branch condition (or combine `! -d` with `[ -f ]` / `[ -L ]` checks), or probe git sparse-checkout state (`git -C "$MARKETPLACE_CLONE" sparse-checkout list`) instead of inferring from filesystem shape alone.
  - From dyn-sparse-clone-detection-output.txt: Add secondary legacy signals the sparse cone will never have after migration—e.g. `[ -e "$MARKETPLACE_CLONE/package.json" ]` or `[ -d "$MARKETPLACE_CLONE/mermaid-lint" ]` on pre-migration trees—or require `git -C "$MARKETPLACE_CLONE" sparse-checkout list` to succeed and show the expected cone before taking the update path; otherwise force the `remove` + `add --sparse` branch.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

