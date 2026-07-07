### [rejected] FINDING_2

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_2: concurrent starts can clobber registry state
- **Reviewer(s)**: cursor-specialist-correctness, dyn-dyn-bgjob-lifecycle
- **Severity**: major
- **Concern**: A second `start` for the same logical key can overwrite the registry row that the first daemon still expects, so one launch can delete or hide the other's tracking state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Fail start on live registry collision or use per-launch registry/result paths; unlink only when daemon identity matches
  - From dyn-dyn-bgjob-lifecycle: Fail closed on start when an identity-valid registry row already exists for the same key, or use exclusive create (`O_EXCL`) / a per-launch unique registry name and teach wait which row is authoritative.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** dismissed (0 YES)

### FINDING_3: hook deny logic is not tied to actual liveness
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases
- **Severity**: major
- **Concern**: The deny hook keys off registry rows, but it does not verify liveness before denying and it also has an allow window when no registry exists, so stale or missing rows can both misclassify background launches.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Check registry daemon/child liveness before deny; reap stale rows inline
  - From cursor-specialist-edge-cases: Tie deny to eager registry or recent start marker


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** dismissed (0 YES)

### FINDING_4: daemon start failures can exit silently
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: minor
- **Concern**: The start path can exit without emitting `BGJOB_ERROR` when fork/pipe setup fails, which leaves callers with a bare rc2 and no diagnostic.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Print BGJOB_ERROR on all start failure paths


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** dismissed (0 YES)

### FINDING_9: migration allowlist still leaves live `run_in_background` launch sites
- **Reviewer(s)**: codex-specialist-correctness, codex-specialist-edge-cases, cursor-specialist-testing
- **Severity**: major
- **Concern**: Allowlisted launch sites and live skill prose still point at `run_in_background`, so the migration remains incomplete at the call-site layer.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Migrate planned launch sites to bgjob start/wait and shrink the allowlist.
  - From codex-specialist-edge-cases: Migrate planned call sites to bgjob start and wait, then shrink the allowlist to true legacy docs only.
  - From cursor-specialist-testing: Migrate all inventory call sites to bgjob start/wait per skills/shared/bgjob-wait.md and remove allowlisted legacy prose as each site moves.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** dismissed (0 YES)

### FINDING_14: reap can unlink rows before preserving timeout or termination status
- **Reviewer(s)**: cursor-specialist-edge-cases, dyn-dyn-bgjob-lifecycle
- **Severity**: major
- **Concern**: `reap` can remove registry rows before it has preserved a timeout result or proved termination success, which drops tracking too early.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Write timeout result env before registry unlink
  - From dyn-dyn-bgjob-lifecycle: Unlink only when termination returns success, the child/daemon liveness checks are false, or a fresh identity-validated kill was logged; otherwise leave the row and surface a stale-registry diagnostic.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

