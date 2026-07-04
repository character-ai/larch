### OOS_1: [OUT_OF_SCOPE] detailed ledger parity across gaps
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: `_build_revisions` still clears absent targets from `last_values`, so the detailed ledger can emit `previous=None` on reappear while the summary path freezes through gaps and resets via `reappearing_targets`. This is a parity gap between the detailed and summary histories.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: `only if product wants parity—emit explicit removal rows in _build_revisions or document that detailed and summary intentionally diverge on gap histories.`

### OOS_2: [OUT_OF_SCOPE] spy coverage for multi-target advances
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: nit
- **Concern**: The spy assertion only checks that `("c3", 0)` was not advanced and does not record which target each `advance` call touched, so a multi-target regression could slip through if another target were advanced to `0` at `c3`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: `extend the spy to capture target (e.g., subclass accumulator keyed by target) if multi-target _summarize scenarios are added later.`

