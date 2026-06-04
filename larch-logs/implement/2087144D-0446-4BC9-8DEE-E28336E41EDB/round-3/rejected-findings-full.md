### [rejected] FINDING_12

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_12: `lib-quiet.sh` is still sourced from the active cache
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-sparse-cone-output.txt
- **Severity**: latent
- **Concern**: Sparse policy is sourced from `SCRIPT_ROOT`, but `lib-quiet.sh` still comes from `PLUGIN_ROOT` / active cache. A stale or tampered cache helper can run before reinstall refreshes the tree, splitting policy and operational helper sources.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From dyn-sparse-cone-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_13: Cache root validation lacks canonicalization
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `is_cache_shaped_larch_root` checks prefix and basename only. A symlink under the cache version dir can pass validation while later file operations follow the symlink outside the cache parent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_14: Release machine-flag parsing can be spoofed by unanchored output text
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: Step 7 parses `LARCH_*=true` via substring over captured upgrade output, so unrelated or spoofed CLI text could force unnecessary restart instructions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_17

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_17: SessionStart sparse-cone drift probe is unnecessarily gated on jq
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Sparse-cone drift detection only needs git, but it runs inside a `jq && git` gate. Hosts with git but no jq miss cone-drift warnings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: Sparse-cone comparison logic is duplicated
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `sessionstart-health.sh` and `upgrade-larch.sh` duplicate marketplace sparse-cone comparison logic instead of sharing one helper with `lib-sparse-dirs.sh`, creating drift risk for future allowlist or normalization changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_30

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_30: SessionStart drift compare assumes sed and sort exist
- **Reviewer(s)**: dyn-hook-failopen-output.txt
- **Severity**: latent
- **Concern**: The new sparse drift compare uses `sed` and `sort` without PATH guards. In stripped PATHs, this can produce repeated false advisories even if the hook exits successfully.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-hook-failopen-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

