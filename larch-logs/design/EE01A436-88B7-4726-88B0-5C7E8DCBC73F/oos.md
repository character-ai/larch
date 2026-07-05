### FINDING_2: Cap-1 design rollup annotation can mis-stamp filed URLs
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The cap-1 design rollup branch needs to be explicit about when to bypass the per-slot stdout loop and how to detect the single combined block, or reruns can rewrite the sentinel map incorrectly and leave some originals unfiled.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Branch before `map_lines: list[str] = []`: on cap-1 rollup, stamp every non-failed order id, append one `OOS_FILE_MAP` row per original, write sentinel, and skip the per-slot loop; keep the current loop for all other cases
  - From Cursor-Pragmatic: In file_oos_annotate_main, branch on len(_parse_post_cap_combined_blocks(combined))==1, len(_parse_order(order_file))>1, and exactly one non-failed URL from _parse_issue_stdout_slots(stdout); add a regression where two stdout URL slots with one combined block leaves conservative per-index behavior


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

