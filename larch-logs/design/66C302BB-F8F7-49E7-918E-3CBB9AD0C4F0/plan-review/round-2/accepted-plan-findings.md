### FINDING_1: Enumeration `find` fail-open must stay documented
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Concern**: Planned SECURITY.md/cleanup.md edits document nested-scan fail-safe but do not require keeping enumeration-pass fail-open semantics. If an implementer rewrites both docs per the plan’s replacement bullets (nested activity, per-entry warn-and-keep) and drops the invariant that cache/tmp top-level enumeration `find` errors are swallowed (`2>/dev/null`, loop `|| true`)—exit 0, zero counts, no warning—operators and auditors may treat any `find` failure as the warned per-entry skip, or assume deletions still ran when the cache enumerator failed silently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Keep two documented behaviors: (1) enumeration `find` failure → exit 0, counts may be 0, no warning; (2) nested activity `find` failure → `larch_err` + skip that entry. Add (1) explicitly to the SECURITY.md replacement paragraph; in the cleanup.md plan, name the line-12 enumeration-error bullet alongside the symlink/bash-3.2 keep list


### FINDING_2: Gap-1 doc sync omits consumer catalog and linting docs
- **Reviewer(s)**: Cursor-Requirements, unknown-slot
- **Severity**: important
- **Concern**: Gap-1 doc sync does not update all consumer-facing docs that still describe retention as top-level mtime only. After planned SKILL.md/cleanup.md fixes, README-adjacent catalog text (`docs/skills.md`, including line 47) and linting harness docs (`docs/linting.md`) can still state top-level-mtime pruning and misstate what `make test-cleanup` exercises, undermining anti-drift goals and leaving operators with the wrong retention model.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Add ### UPDATED blocks for docs/skills.md and docs/linting.md (nested maxdepth-5 model, depth-5 tradeoff, find-fail-safe where relevant) or explicitly fold them into the four-doc list and Edit-in-sync triggers
  - From unknown-slot: Add `### UPDATED: docs/skills.md` (or extend the `skills/cleanup/SKILL.md` block) to replace line 47 with the same bounded nested-activity phrasing as `SKILL.md`


### FINDING_3: Stale edit-in-sync phrase in test-cleanup.md
- **Reviewer(s)**: unknown-slot
- **Severity**: nit
- **Concern**: The edit-in-sync trigger in `test-cleanup.md` still says "top-level mtime age pruning" after the plan’s edits. If the plan updates `cleanup.md`’s trigger from "top-level mtime age checks" to "bounded nested-activity / maxdepth 5 retention" but `test-cleanup.md` only adds the new case without fixing line 26, that file will still use the phrase corrected elsewhere.
- **Suggested revisions (informational for voters; coder decides)**:
  - From unknown-slot: While updating `test-cleanup.md` to add `find-failure-skips-deletion`, also reword line 26: replace "top-level mtime age pruning" with "bounded nested-activity / maxdepth 5 retention (and find-failure fail-safe)" to match the corrected `cleanup.md` trigger

