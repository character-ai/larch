### OOS_1: Add structural test pinning the canonical YES↔EXONERATE anchor phrase across all prose locations
- **Description**: The new framing prose lives in four locations: the two voter-prompt strings in `skills/design/references/plan-review.md` (Voter 1 and shared Voter 2/3), the `make_prompt_file()` body in `scripts/dispatch-plan-voters.sh`, and the acceptance-guidance line in `skills/design/references/plan-review-quick.md`. This PR adds a harness assertion against the rendered dispatch-script prompt only. A structural test (e.g., a check in `scripts/test-design-structure.sh` or a small new harness) that greps for the canonical phrase `When in doubt between YES and EXONERATE, prefer EXONERATE` across all four locations would catch prose drift early. Deferred per the user's "verbatim" scope decision for this PR.
- **Reviewer**: Claude (quick mode)
- **Vote tally**: N/A — quick-mode self-review
- **Phase**: design
