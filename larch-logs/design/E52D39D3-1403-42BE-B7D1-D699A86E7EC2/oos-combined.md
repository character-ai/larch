### OOS_1: Aggregated rollup of 2 capped OOS items
- **Description**: Cap 1 (OOS_ISSUES_PER_RUN_CAP) exceeded; the following 2 items were rolled up by skills/implement/scripts/oos-issue-cap.sh:
  - **OOS_2:**: - **Description**: Tier 3 reads `DESIGN_TMPDIR` / `SESSION_TMPDIR` but not `IMPLEMENT_TMPDIR`. Scenario: `/implement` Step 5 also launches Codex via `_review_launch_codex`; implement sessions write `.… [Files: plan.txt:49-52]
  - **OOS_3:**: - **Description**: Codex reviewer probe still uses `str(Path.cwd())` for `-C` and `_trust_config_arg`. Scenario: Health-check / probe launches from plugin-cache cwd can hit the same trust-check failur… [Files: python/agents.py:815]
- **Reviewer**: Combined: capped per-run rollup
- **Vote tally**: N/A — capped rollup of 2 entries
- **Phase**: implement

