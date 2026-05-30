### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/SKILL.md:1413-1414
- **Concern**: Plan adds six new sibling `.md` files but only extends the wraps list with `test-trailer-awk.sh`; it does not wire `agent-lint` S030 or SKILL.md sibling citations the way peer optional-trailer docs already do. Scenario: `make lint` / `agent-lint --pedantic` can flag new `skills/design/scripts/*.md` as orphaned skill files while Testing strategy requires a clean lint run
- **Proposed resolution**: Add `Sibling: lib-plan-optional-trailers.md` on the shared-lib bullet and `Sibling: test-trailer-helpers.md` plus harness contract `test-trailer-awk.md` on the unit-harness bullet (mirror `test-gate-b-dedup-plan.md` at 1414); append `test-trailer-dedup.md`, `test-trailer-has-any.md`, and `test-trailer-validate.md` to the `agent-lint.toml` harness-sibling exclusion block (~1371+) if they stay stub-only


