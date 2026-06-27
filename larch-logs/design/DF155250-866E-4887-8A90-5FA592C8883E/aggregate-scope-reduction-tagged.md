### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: blocking
- **Focus area**: risk-integration
- **Location**: skills/implement/references/ship-pr-oos-checkpoint-router.md
- **Concern**: [SCOPE-REDUCTION] Router cap-pointer sentence conflicts with structural forbid on `/issue --input-file`. Scenario: Approach items 45 and 70 and structural pin item 70 require adding a router sentence that includes `/issue --input-file` while also forbidding that exact substring in `ship-pr-oos-checkpoint-router.md`. `scripts/test-implement-structure.sh` `forbid()` is substring-based, so the mandated negation cannot coexist with the forbid pin; implementers must weaken the forbid or drop the required sentence, reintroducing either harness failure or ambiguous public-filing guidance on the security-only branch.
- **Proposed resolution**: Rephrase the required cap-authority sentence without the literal `/issue --input-file` token (for example, "does not run cap enforcement or public issue batch filing"). Keep the structural forbid on positive batch-filing instructions only, or scope the harness forbid to exclude clearly negated forms.
