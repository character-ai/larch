## Decision 1: Scope of change
- **Question**: Is this purely a guideline addition, or does it also include a lint or invariant?
- **Resolution**: Guidelines only. The issue explicitly lists ARCHITECTURAL_GUIDELINES.md and a single G-Gate-1 entry. It notes the work is complementary to but separate from #6873/#6892 which targeted lints and invariants.
- **Source**: codebase (issue body)

## Decision 2: Section placement
- **Question**: New section or append to an existing section?
- **Resolution**: New section. No existing section covers gate/producer release sequencing. Closest candidates (Idempotency, Orchestration) are thematically distinct. The issue suggests a new id `G-Gate-1` implying a new family.
- **Source**: codebase

## Decision 3: Guideline text
- **Question**: Exact text for Why, Guidance, Deviate when?
- **Resolution**: Derived from the three rules in the issue plus the three bug citations (#6880, #6882, #6875). Deviate when: when the gate and producer are the same artifact, or when a separate migration PR covers the wire-up in the same release.
- **Source**: codebase (issue body + bugs)
