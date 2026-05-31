### FINDING_33: `_insert_md_at_anchor` blank-line order vs bash
- **Reviewer(s)**: dyn-bash-parity-output.txt
- **Severity**: important
- **Concern**: In `_insert_md_at_anchor`, when closing an `## [Unreleased]` block at the next `## [` heading, Python appends the new entry block and then a blank line before the following heading (`out.extend(block)` then `out.append("")`). `scripts/lib-changelog.sh` `write_changelog_entry` does the opposite on that path: it prints a blank line first, then the entry lines (`print ""` then `for … print e[i]`), then the next heading. That changes blank-line spacing between Unreleased content and the inserted version section relative to bash; `test_parity_write_changelog_entry` is the right guard, but the control-flow order is visibly inverted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-parity-output.txt: In the `in_unreleased and line.startswith("## [")` branch, match bash by emitting `out.append("")` before `out.extend(block)` (keep the trailing `out.append(line)` for the next heading unchanged). The `END` path at `389-392` already uses blank-then-block and should stay as-is.



