### OOS_1: Aggregated rollup of 3 capped OOS items
- **Description**: Cap 1 (OOS_ISSUES_PER_RUN_CAP) exceeded; the following 3 items were rolled up by skills/implement/scripts/oos-issue-cap.sh:
  - **OOS_1:**: - **Description**: Helper jq/inc.bash assets absorbed into Python are not named in the Retired paths list.. Scenario: If deleted during port without migrated-scripts.tsv rows, later callers of test-fe… [Files: SKILL.md migrated-scripts.tsv test-fetch-combinable-issues-filter.sh]
  - **OOS_1:**: - **Description**: `gh-body-file.md` frontmatter drops retiring bash callers but does not add Python replacements. Scenario: After cutover, `python/release_finish.py` (and `combine-issues apply`) will… [Files: .claude/rules/gh-body-file.md:1-10 gh-body-file.md plan.txt:559-562 python/release_finish.py]
  - **OOS_1:**: - **Description**: [OUT_OF_SCOPE] Step 15 verify-main logic already exists inline in python/finalize.py postmerge while the plan also adds python/verify_main.py for scripts/implement-finalize.sh.. Sce… [Files: python/finalize.py python/finalize.py:386-400 python/verify_main.py scripts/implement-finalize.sh.]
- **Reviewer**: Combined: capped per-run rollup
- **Vote tally**: N/A — capped rollup of 3 entries
- **Phase**: implement

