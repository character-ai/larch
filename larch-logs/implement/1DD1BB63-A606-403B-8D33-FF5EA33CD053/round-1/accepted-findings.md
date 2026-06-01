### FINDING_31: correctness: scripts/test-implement-timing-rehydration.sh:1-20
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Plan required updating the harness header comment plus PASS line; only PASS was updated. Contributors reading the .sh header will not see the helper-aware tmpdir coupling documented in the .md sibling; drift risk if counts change again. Extend the top-of-file or cardinality comment block to document step_telemetry_mark_count and tmpdir == token_read + step_telemetry_mark_count.
- **Suggested revision**: Address the concern above.


