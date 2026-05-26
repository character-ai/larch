### FINDING_3: code-quality: skills/review/scripts/test-aggregate-findings.sh:1230-1251
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] pseudo-heading fallback test does not assert --require-result-pattern on the real dispatcher path. Removing --require-result-pattern from dispatch_args could regress #2881 while pseudo-heading and phase-2 fallback tests still pass. Use write_real_dispatch_wrapper plus AGGREGATE_DISPATCH_ARGV_LOG and grep for the dual-gate ERE like the codex_primary and padded-attestation cases.
- **Suggested revision**: Address the concern above.



