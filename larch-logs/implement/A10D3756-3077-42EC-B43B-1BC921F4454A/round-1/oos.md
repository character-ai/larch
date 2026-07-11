### FINDING_1: [OUT_OF_SCOPE] Fallback provenance loading discards all valid entries on corruption or overflow
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, dyn-dyn-baseline-provenance
- **Severity**: minor
- **Concern**: A single malformed provenance entry or exceeding the provenance-path cap clears the entire fallback sidecar. Post-commit recomputation can therefore lose previously verified paths and produce stale disposition results. Invalid rows should be discarded individually, or the failure should be surfaced explicitly rather than silently returning an empty provenance map.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From dyn-dyn-baseline-provenance: Address the concern above.


Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_2: [OUT_OF_SCOPE] Relay coverage unnecessarily requires step2-baseline.txt
- **Reviewer(s)**: cursor-specialist-correctness, dyn-dyn-baseline-provenance
- **Severity**: minor
- **Concern**: `_relay_scope_coverage` still requires `step2-baseline.txt` before computing coverage. Live-base-capable runs that skip relay and first compute at ship can under-report touched plan paths or leave intermediate relay KVs stale.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From dyn-dyn-baseline-provenance: Address the concern above.


Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_3: [OUT_OF_SCOPE] Live-base attribution may include unrelated upstream plan-path commits
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: minor
- **Concern**: Live-base touched-path attribution uses all plan-path commits between the merge base and `HEAD`, which can mark paths as covered even when they were not implemented by this run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.


Vote tally: YES=2 NO=1 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_5: [OUT_OF_SCOPE] Partial ship state prevents FORKED_TARGET fallback
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-baseline-provenance
- **Severity**: minor
- **Concern**: `FORKED_TARGET` resolution stops at the first present `ship-pr-state.sh`, even when the file is empty, partial, or lacks a parseable `FORKED_TARGET` value. This can force normal `origin` mode instead of falling back to `session-env.sh` for resumed forked runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From dyn-dyn-baseline-provenance: Treat a present ship-state file as authoritative only when it contains a parseable `FORKED_TARGET=true|false` key; if the key is absent or malformed, fall through to `session-env.sh` (still never reading ambient env).


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_6: [OUT_OF_SCOPE] Repeated fallback provenance writes cause sidecar churn
- **Reviewer(s)**: codex-specialist-edge-cases
- **Severity**: minor
- **Concern**: Fallback provenance is rewritten on every fallback recomputation, including when the provenance remains unchanged and empty. This creates repeated sidecar writes without changing baseline attribution correctness.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Address the concern above.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false

### FINDING_8: [OUT_OF_SCOPE] Tests do not exercise real Git subprocess behavior
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: New baseline and provenance behavior is tested through `FakeRunner` rather than real `git symbolic-ref` and `git merge-base` subprocesses. This leaves ref-validation and shallow-clone argument wiring unverified against a real Git binary, although it follows the module’s pre-existing test pattern.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_9: [OUT_OF_SCOPE] Path signatures omit HEAD tree state
- **Reviewer(s)**: dyn-dyn-baseline-provenance
- **Severity**: minor
- **Concern**: `_path_state_signature` hashes only the worktree file or symlink target and does not compare the `HEAD` tree state. Sparse-checkout or worktree-absent but `HEAD`-present plan paths can therefore be misclassified as absent, affecting retention and pruning.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-baseline-provenance: Address the concern above.
Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false
