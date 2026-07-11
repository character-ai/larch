# Review Round 1

- Mode: `diff`
- 3 accepted, 1 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Author guidance must land with ship-blocking contracts
- **Reviewer(s)**: cursor-specialist-correctness, dyn-dyn-gate-sequencing
- **Severity**: major
- **Concern**: G-Gate-1 requires producer updates in the same change or release as a fail-closed gate, but only says to update author guidance with every new ship-blocking contract. It does not require same-change or same-release timing, allowing stale author guidance to ship separately from the exact-string contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From dyn-dyn-gate-sequencing: Give author guidance the same sequencing language as producers, e.g. “update author guidance in the same change or release as every new ship-blocking contract, or later, never earlier,” and keep that requirement outside the migration carve-out unless the carve-out explicitly covers guidance too.


### FINDING_2: Keep author-guidance and persisted-state requirements in parser-retained text
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: G-Gate-1 stores the ship-blocking author-guidance and persisted-state integration-test rules only in Guidance, which `parse_guideline_entries` drops before automated guideline assessments consume the entry. As a result, `/design` and `/implement` assessments retain only the title, Why, and Deviate text and cannot see the core contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


### FINDING_3: Tighten the same-release migration carve-out
- **Reviewer(s)**: dyn-dyn-gate-sequencing
- **Severity**: major
- **Concern**: The `Deviate when` carve-out permits a separate migration to complete the producer and gate wire-up in the same release without requiring the migration to land before or with the gate. A gate could therefore become consumer-visible before its producer is live, recreating the fail-closed stall pattern.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-gate-sequencing: Tighten the carve-out so the completing migration must land in the same change as the gate or in an earlier same-release change that is already released before the gate is consumer-visible; alternatively require feature-flag or version gating so no gate reads persisted state until every producer path is live.
