# Review Round 1

- Mode: `diff`
- 1 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_2: Malformed row WARN `emit_kv` failure drops valid scout rows
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Delegating coder sidecar normalization to the design wrapper can drop valid scout rows when one malformed row makes wrapper warning emission fail. A sidecar with `name:"bad\rname"` plus a valid `api-contract` row reaches `skills/design/scripts/scout-plan-archetypes-wrapper.sh:214-215`, `emit_kv` rejects the carriage return before `SCOUT_STATUS`, and Step 2 overwrites the normalized manifest with `{"archetypes":[]}`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Sanitize wrapper warning values before `emit_kv`, or avoid interpolating raw invalid names, so malformed rows are filtered while valid rows survive.


