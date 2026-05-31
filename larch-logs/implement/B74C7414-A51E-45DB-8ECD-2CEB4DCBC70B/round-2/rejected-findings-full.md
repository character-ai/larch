### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: MAV test hardcodes relocated snapshot path
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The MAV assertion hardcodes `.pre-coder-snapshots/round-1` instead of deriving the path through `pre_coder_snapshot_dir`, so a legitimate helper layout change could break the test while production remains valid.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: Repeated pre-coder head path construction
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Several functions manually reconstruct the relocated `pre-coder-head.txt` path, increasing the chance that future edits update only some call sites.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: Snapshot placement tests do not cover full trust boundary
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-snapshot-tamper-output.txt
- **Severity**: latent
- **Concern**: The new location/invariant tests mainly assert snapshots are outside `round_dir`, but they do not fully assert canonical placement outside `PWD` / Codex grants or that orchestrator integration writes snapshots only under `.pre-coder-snapshots`. A regression could pass tests while snapshots remain coder-writable or are written back into `round_dir`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-snapshot-tamper-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: Structural LOC relocation test relies on indirect cap-hit behavior
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The relocated structural LOC test checks an indirect cap-hit envelope rather than directly asserting the structural LOC input/path behavior, so a stale `round_dir` read or unrelated envelope change could obscure the intended regression signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

