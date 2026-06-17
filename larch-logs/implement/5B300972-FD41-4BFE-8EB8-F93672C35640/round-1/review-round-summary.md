# Review Round 1

- Mode: `diff`
- 2 accepted, 2 rejected (1 neutral)

## Accepted Findings

### FINDING_2: `_strip_plan_provenance_headers` over-strips plan prose above trailer
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `_strip_plan_provenance_headers` removes any contiguous `review_status:` / `rounds_completed:` lines encountered while walking backward through optional size trailers, not only the terminal machine-provenance pair. A plan documenting wire-format fields with `review_status:` prose immediately above the real trailer block loses that prose in materialized `plan.txt`; acceptance requires prose lines to survive.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: After finding `diff_lines:`, skip optional size-trailer lines backward, then remove only the contiguous provenance block directly above them and stop; reuse or mirror `design_publish` trailer-region bounds.


### FINDING_6: `_count_issue_sections` fence-aware walk swallows later section headings
- **Reviewer(s)**: dyn-report-counts-output.txt
- **Severity**: important
- **Concern**: `_count_issue_sections` only switches sections when `not in_fence`, so an unclosed fenced diagnostic block in one category can swallow later `### …` headings and everything after them. A common shape is `### Tool Failures`, an opening ` ``` `, log text, then `### Warnings` and warning bullets before the closing fence; the warning heading is appended into the exec buffer, the section never becomes `_ISSUE_SECTION_WARN`, and bullets after the fence close are still counted as exec issues (or dropped while still “inside” the fence). The pre-change parser switched on `###` lines regardless of fence state, so this is a regression tied to the new fence-aware section walk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-report-counts-output.txt: treat recognized section headings as hard boundaries: switch section (and reset `in_fence` to `false`) even inside a fence, or stop the backward/forward walk at the first post-fence `###` heading; add a regression test with an unclosed or section-spanning fence in `execution-issues.md`.


