### FINDING_20: risk-integration: docs/linting.md:95-117
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] New harness shards need matching required status checks on main If branch protection still requires only test-harnesses (1)-(13), jobs (14)-(16) may be non-blocking so failures in those shards would not prevent merge while maintainers assume full matrix is gating Update GitHub branch protection or org rulesets to require test-harnesses (14), (15), and (16) before relying on this PR as the enforcement baseline; verify with a draft PR that intentionally fails one new shard
- **Suggested revision**: Address the concern above.



