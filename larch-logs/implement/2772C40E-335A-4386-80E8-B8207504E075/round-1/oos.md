### FINDING_16: [OUT_OF_SCOPE] External-coder round_dir write access to snapshots
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Codex dispatch grants write access to `$round_dir` alongside the repo root, so snapshot files written immediately before dispatch are not integrity-protected against a hostile external coder.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Out of scope for #3272; a defense-in-depth improvement would snapshot to a read-only location the coder cannot reach, or re-read/recompute `pre-coder-head` and snapshots from git state after dispatch instead of trusting on-disk artifacts.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_17: [OUT_OF_SCOPE] Session tmpdir cleanup deletes secrets without redaction
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: Session tmpdirs under `~/.cache/larch/sessions/` may contain secrets and raw `CMD_JSON` argv; cleanup still deletes by age without redaction (documented in `SECURITY.md`).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Pre-existing operational posture; not introduced by this branch’s enumeration-warning change.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_18: [OUT_OF_SCOPE] Enumeration failure warns and skips deletion (intentional fail-safe)
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Enumeration failure now warns and skips instead of silent fail-open. Stale cache/tmp dirs may persist until find works; intentional fail-safe. Out of scope: intentional #3274 behavior with tests and SECURITY.md sync.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_19: [OUT_OF_SCOPE] LARCH_DESIGN_CONVERGENCE_THRESHOLD removal
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Removed `LARCH_DESIGN_CONVERGENCE_THRESHOLD`; hardcoded non-nit max 5. Operators with old env exports see no effect; convergence semantics changed in prior work. Out of scope: intentional #3285 dead-config removal.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_20: [OUT_OF_SCOPE] #3272 does not address #3227 clean-tree manual-commit overlap
- **Reviewer(s)**: dyn-flag-removal-completeness-output.txt
- **Severity**: nit
- **Concern**: The branch correctly aligns the guard with `round_coder_delta_paths` for **dispatch-time** carryover; it does not change `run-step5-review.sh`. Failures from a fully clean tree after a manual commit (only committed overlap, no pre-dispatch porcelain) are a different mechanism and are not addressed here—consistent with the implementation plan.
- **Suggested revisions (informational for voters; coder decides)**:

Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected

### FINDING_4: [OUT_OF_SCOPE] Duplicate enumeration loops in cleanup.sh
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: #3285 duplicates mktemp/find/read loops for cache and /tmp. Future enumeration changes must be applied twice on that file.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extract a shared enumeration helper when editing cleanup.sh again.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

