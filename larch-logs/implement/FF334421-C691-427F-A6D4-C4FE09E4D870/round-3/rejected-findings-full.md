### [rejected] FINDING_15

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_15: Unvalidated state keys and overlays can poison terminal metadata
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Merged state keys and overlayed repo/PR fields are not sufficiently allowlisted, quoted, or slug/URL-validated before being persisted into state/finalize files.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_16: Corrupt or unreadable ship-pr-state.sh now aborts instead of recovering
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The new fail-closed read path can turn partially corrupt state into an `INTERNAL_ERROR` rather than recovering or retrying with a fresh overlay.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: ship-pr-state.sh parsing/writing is not canonicalized
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `ship-pr-state.sh` is parsed inline while other paths use canonical KV readers, so quoted or shell-escaped values can be interpreted differently and break state preservation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_25

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_25: ShipError outcome handling is split across envelopes
- **Reviewer(s)**: dyn-parity-contract-output.txt
- **Severity**: latent
- **Concern**: Similar `ShipError`/terminal failures can become different exit codes, JSON outcomes, and disk-finalize behavior depending on whether they surface inside `run_ship` or outer `main`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-parity-contract-output.txt: Route all terminal `ShipError`/`Stalled` outcomes through one envelope builder in `main()` so exit code, JSON `outcome`, and optional terminal disk writes stay aligned; keep `INTERNAL_ERROR` strictly for truly unexpected exceptions.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: Terminal finalize/stall metadata is written through divergent paths
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Multiple terminal/finalize writers populate overlapping stall and PR metadata from different contexts, so terminal state can become path-dependent or stale, and tests do not fully cover common stalled paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: Selector/routing structure-test coverage is incomplete
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Dual-path Step 8+ routing is spread across prose and awk pins, with gaps for anti-halt, stall recovery, conflict-resolution, and stale contract docs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

