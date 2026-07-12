### OOS_1: Salvage provenance is spoofable [OUT_OF_SCOPE]
- **Reviewer(s)**: codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases
- **Severity**: major
- **Concern**: Salvage reship is authorized by a predictable commit subject rather than lane-bound provenance, so an unrelated commit can be mistaken for fixer salvage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Write and validate identity-bound salvage provenance such as a trailer or sidecar.
  - From cursor-specialist-edge-cases: If tightening is desired later, bind salvage to lane-owned pathspec or commit metadata beyond subject matching.
  - From codex-specialist-edge-cases: Write and verify deterministic lane-identity provenance on the salvage commit or in a durable sidecar before reshipping.
