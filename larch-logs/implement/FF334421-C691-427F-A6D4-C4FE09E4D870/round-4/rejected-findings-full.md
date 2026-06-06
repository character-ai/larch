### [rejected] FINDING_15

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_15: Step 18 conditional restore behavior lacks executable coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The stale-finalize versus skip-restore branches in Step 18 are pinned only by prose/substrings, leaving `_restore_finalize` branch behavior without fixture-level tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: Terminal stall/finalize metadata has competing writers
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `python/ship.py` can write terminal stall/finalize disk state from in-run helpers and again from `_persist_stall_metadata_if_needed`, allowing partial or divergent terminal metadata in `ship-pr-state.sh` / `finalize-state.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_28

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_28: Run-log refresh triggers still name bash-only `ship-pr.sh` semantics
- **Reviewer(s)**: dyn-prompt-contracts-output.txt
- **Severity**: latent
- **Concern**: `refresh-run-logs.sh` trigger prose is still framed around `ship-pr.sh` internals and exit parsing, risking missed refreshes or wrong semantics on Python JSON/state-file paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-prompt-contracts-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: Step 8+ Python-vs-bash routing prose is too fragile
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `skills/implement/SKILL.md` describes Python default routing and bash opt-in in a dense mixed paragraph with repeated qualifiers, increasing the chance of orchestrator misrouting and doc drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_35

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_35: Python selector underdocuments pre-push conflict handoff routing
- **Reviewer(s)**: dyn-scope-anchor-output.txt
- **Severity**: important
- **Concern**: The Python selector collapses exit 4 into generic stall handling and does not surface the required `ship_pr_pre_push` conflict-resolution branch before Step 16/18.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-scope-anchor-output.txt: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: Ship state KV parsing and merge logic is duplicated
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Ship state KV files are parsed and merged through multiple code paths, so preserve/merge behavior can diverge between readers and writers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_45

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_45: `py-lint` is not pinned to the configured Python interpreter
- **Reviewer(s)**: dyn-runtime-versioning-output.txt
- **Severity**: latent
- **Concern**: `make py-lint` invokes bare `ruff`, `pylint`, and `pyright` from `PATH`, so local lint can run under/tool against an interpreter/toolchain that diverges from Python 3.12 CI and production.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-runtime-versioning-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: Success path writes `phase=done` twice
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, dyn-scope-anchor-output.txt
- **Severity**: important
- **Concern**: `run_postmerge_phase` already writes terminal success state, but the merge loop writes `phase=done` again without the same terminal context, risking drift between `ship-pr-state.sh` and `finalize-state.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From dyn-scope-anchor-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_9: PrePushConflictHandoff writes handoff keys without stall metadata
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-state-machine-output.txt
- **Severity**: important
- **Concern**: On pre-push conflict handoff, `python/ship.py` writes resume/conflict keys but leaves or rewrites disk state as `STALL_TRACKING=false` and skips finalize metadata, so Step 18/classification can miss a real stalled handoff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-state-machine-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

