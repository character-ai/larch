### FINDING_1: Route handoff file-first loop drops WARN/ERROR from result env
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Concern**: The Step 0b route-handoff file-first `while` loop over `.design-route-result.env` allowlists ROUTE/RESUME keys but not WARN/ERROR. When pause-load fallthrough writes failures only into the result env (stdout capture empty), file-only paths never surface pause-load WARN/ERROR because the pre-branch re-emit path also skips them.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Mirror Step 3 WARN handling: in the file-first while-loop, add WARN|ERROR) branches that print breadcrumbs (and set vars if re-emit needs them); keep stdout merge filling only missing ROUTE keys


### FINDING_2: Structure Check 20 still pins obsolete Step 0b sub-step 2.5 anchors
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: `scripts/test-design-structure.sh` Check 20 still requires SKILL.md sub-step `2.5. **Title-eligibility filter**` and enforces fetch→2.5→3 line order via awk. After the Step 0b rewrite (title eligibility in `design-route.sh`, renumbered sub-steps), the test can fail even when routing and extraction behavior are correct.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Replace Check 20 with greps on design-route.sh plus orchestrator cancel-title-filter-before-clarify ordering (drop or rewrite the 2.5 / filter_line awk)


