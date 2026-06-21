### OOS_1: [OUT_OF_SCOPE] Design live-run discovery still uses pointer mtime
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Design candidate discovery uses pointer mtime while implement discovery was switched to timing-ledger activity. When both skills have live pointers for the same repo, mixed ranking can let a newer design pointer beat a long-running implement session (same class of symptom as #4954). Pre-existing; unify liveness signals across skills or apply activity-based ranking to `_design_candidate` if design reports the same symptom.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


### OOS_2: [OUT_OF_SCOPE] _discover_live_run does not exclude completed or abandoned sessions
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `_discover_live_run` does not filter completed or abandoned sessions. Stale tmpdirs with high mark timestamps can keep winning after the real session moves on.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


