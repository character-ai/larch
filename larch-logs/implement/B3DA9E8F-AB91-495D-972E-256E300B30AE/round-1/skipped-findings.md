### FINDING_3: risk-integration: scripts/test-launch-claude-review.sh:230-242
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Plan edge case for repeated identical explicit --context-files is untested. Dedup logic for explicit-only duplicates could regress while implicit+explicit dedup still passes. Add --context-files PATH --context-files PATH and assert single rendered occurrence.
- **Suggested revision**: Address the concern above.



