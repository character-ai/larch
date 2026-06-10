# Review Round 1

- Mode: `diff`
- 4 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_10: combine-issues says to scan issue bodies but gh issue list default output omits bodies
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The prescribed `gh issue list` workflow can miss implementing issues whose body mentions the missing file because default list output does not include issue bodies.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Use gh issue list with --json number,title,body or add gh issue view for candidate issues before deciding no implementing issue matches.
  - From codex-specialist-edge-cases-output.txt: Use gh issue list with --json number,title,body or fetch candidate bodies with gh issue view before deciding no implementing issue exists.


### FINDING_18: combine-issues can lose blocked-by semantics when blocked items enter OOS combination
- **Reviewer(s)**: dyn-oos-blocked-by-logic-output.txt
- **Severity**: important
- **Concern**: Blocked OOS items are collected into the same flat actual list as normal kept items, so later deduplication/combination can close or merge the source issue after blocked-by wiring was attached to the original issue number.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-oos-blocked-by-logic-output.txt: **Suggested fix:** Exclude blocked items from the oos-3/oos-4 pipeline (keep them on their source issues without closing those issues), or explicitly carry blocked status into the combined issue and re-run `add-blocked-by.sh` against the new issue before any source close.


### FINDING_3: combine-issues interpolates untrusted issue Location text into gh search command prose
- **Reviewer(s)**: cursor-specialist-security-output.txt, codex-specialist-security-output.txt
- **Severity**: important
- **Concern**: The combine-issues OOS actuality search uses untrusted filenames from issue bodies in a `gh --search` command, allowing malformed search operators, broken quoting, or shell-command execution when prose is followed literally.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Sanitize to a strict basename charset; pass --search as a quoted argv element; validate issue numbers before add-blocked-by.sh
  - From codex-specialist-security-output.txt: Route through a helper script or validated shell variable; pass the search term as argv, not interpolated command text.


### FINDING_7: combine-issues can wire blocked-by to unrelated issues from loose filename matches
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-oos-blocked-by-logic-output.txt
- **Severity**: latent
- **Concern**: Missing-file actuality checks rely on bare-filename search and loose title/body matching, so generic filenames can match unrelated open issues and incorrectly classify stale OOS items as blocked.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Require full path or implementing-state match before calling `add-blocked-by.sh`, or add operator confirmation on non-exact matches.
  - From dyn-oos-blocked-by-logic-output.txt: **Suggested fix:** Narrow the search (full repo-relative path or quoted path), require a lifecycle/busy title prefix on `#<M>`, and treat ambiguous matches as **stale** or **actual** (not blocked) rather than picking the first search hit.


