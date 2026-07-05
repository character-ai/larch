### FINDING_2: Oversized OOS rollups still split into multiple public issues
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Codex-Requirements
- **Severity**: important
- **Concern**: The shared OOS filer still splits oversized accepted rollups into multiple public GitHub issues, so a single capped batch can produce `(part N/M)` bodies and more than one `[OOS]` issue instead of exactly one unifying issue.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Promote oos_filer.py from MAY_UPDATE to UPDATED: on oversize rollup emit one summarized public body (full text stays in run logs) and file a single create-one call; retire or gate multi-part splitting for capped OOS batches; add/adjust tests in test_oos_filer.py (and test_file_oos.py only if issue-cap output changes)
  - From Codex-Arch: Make oos_filer.py a firm update. Replace splitting with one under-limit summarized body that points to full run-log details, and test exactly one create-one call for oversized OOS
  - From Cursor-Innovation: Promote oos_filer.py from `MAY_UPDATE` to firm `### UPDATED:`: when `OOS_ISSUES_PER_RUN_CAP=1`, replace multi-part splitting with one summarized public body (full detail stays in run logs), and add `test_oos_filer.py` coverage that an oversized post-cap combined payload yields exactly one `create-one` call / one sentinel URL.
  - From Codex-Innovation: Add an explicit plan step for `oos_filer.py` to replace body splitting with one summarized or truncated public body plus run-log details, and cover the oversized path in `test_oos_filer.py`.
  - From Cursor-Pragmatic: Add an UPDATED design_oos.py step: after cap=1 rollup, stamp every source OOS block in oos-accepted-design.md with the single filed URL (or port the implement stable-id mapping); extend test_design_oos.py to assert all rollup sources carry Filed URL and skip re-file on rerun
  - From Codex-Requirements: Promote oos_filer.py from MAY_UPDATE to UPDATED. Replace body splitting with one summarized or truncated public body plus run-log details, and cover the oversized path in test_oos_filer.py.


### FINDING_4: Security-tagged OOS can leak into public artifacts
- **Reviewer(s)**: Codex-Arch, Codex-Innovation
- **Severity**: blocking
- **Concern**: Security-tagged OOS that are rejected or neutral can still be appended to public oos.md / oos_chunks, so security prose can leak into committed or projected public artifacts instead of staying in a private sidecar path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Route every security OOS outcome in plan_review_tally.py to a private sidecar and exclude it from oos.md, oos-accepted-design.md, and the aggregate pool. Add the matching design tally test
  - From Codex-Innovation: Add an explicit plan step for plan_review_tally to keep every security-tagged OOS out of oos_chunks, oos_accepted_chunks, and oos_pool_chunks, preserving it only in a local security sidecar or private disposition path, and cover rejected/neutral design security OOS.


### FINDING_5: Security sidecar blocks non-security OOS filing
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: When a security sidecar is present, oos_filer returns early before reading accepted files, so a separate accepted non-security OOS never gets filed into the unifying public issue.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Make oos_filer.py a firm UPDATED file. File accepted non-security blocks while keeping security blocks private and keeping the checkpoint blocked until private disposition, or explicitly rerun oos file after the sidecar is cleared. Add a mixed security plus non-security test.


