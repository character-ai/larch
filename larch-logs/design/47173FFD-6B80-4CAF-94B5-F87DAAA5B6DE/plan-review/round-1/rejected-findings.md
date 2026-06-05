### [Plan Review] FINDING_3

### FINDING_3: /implement presence defaults can mask empty durable presence values
- **Reviewer(s)**: Codex-Edge
- **Severity**: latent
- **Concern**: Presence-key reads default to false before calling degraded-tools-gate.sh, so missing or empty durable values can be converted into ordinary false values and suppress PRESENCE_INPUT_EMPTY diagnostics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: For presence keys only, read raw values without --default or separately test the raw value before defaulting, then pass empty through to degraded-tools-gate.sh; keep binary-found defaults if legacy compatibility requires them.


