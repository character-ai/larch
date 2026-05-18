### FINDING_1: risk-integration: skills/report-tokens/scripts/test-rate-assertions.sh:1-72
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Per-workflow mean output is not covered by the existing rate/cost_vendor harness. A future edit could drop or break the mean fragment in skills/report-tokens/scripts/run-analysis.sh:805-807 while CI still passes test-rate-assertions. Extend test-rate-assertions.sh (or add a sibling harness) with a grep/static guard for the mean/statistics.mean(values) fragment in the per-workflow print line.
- **Suggested revision**: Address the concern above.

