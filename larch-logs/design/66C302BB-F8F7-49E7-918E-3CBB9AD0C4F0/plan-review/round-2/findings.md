### FINDING_1:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: security
- **Location**: SECURITY.md:234;skills/cleanup/scripts/cleanup.md:9-13
- **Concern**: Planned SECURITY.md/cleanup.md edits document nested-scan fail-safe but do not require keeping enumeration-pass fail-open semantics. Scenario: Implementer rewrites both docs per the plan’s replacement bullets (nested activity, per-entry warn-and-keep) and drops the existing invariant that cache/tmp top-level enumeration `find` errors are swallowed (`2>/dev/null`, loop `|| true`): exit 0, zero counts, no warning. Operators/auditors then treat any find failure as the warned per-entry skip, or assume deletions still ran when the cache enumerator failed silently
- **Proposed resolution**: Keep two documented behaviors: (1) enumeration `find` failure → exit 0, counts may be 0, no warning; (2) nested activity `find` failure → `larch_err` + skip that entry. Add (1) explicitly to the SECURITY.md replacement paragraph; in the cleanup.md plan, name the line-12 enumeration-error bullet alongside the symlink/bash-3.2 keep list

### FINDING_2:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: docs/skills.md:47,docs/linting.md:285
- **Concern**: Gap 1 doc sync omits two consumer docs that still say retention is top-level mtime only. Scenario: After the planned SKILL.md/cleanup.md fixes, README-adjacent catalog and linting harness docs still describe top-level-mtime pruning and misstate what make test-cleanup exercises
- **Proposed resolution**: Add ### UPDATED blocks for docs/skills.md and docs/linting.md (nested maxdepth-5 model, depth-5 tradeoff, find-fail-safe where relevant) or explicitly fold them into the four-doc list and Edit-in-sync triggers

### FINDING_3:
- **Reviewer(s)**: unknown-slot
- **Severity**: nit
- **Focus area**: correctness
- **Location**: skills/cleanup/scripts/test-cleanup.md:26
- **Concern**: Edit-in-sync trigger in `test-cleanup.md` still says "top-level mtime age pruning" after the plan's edits. Scenario: The plan updates `cleanup.md`'s edit-in-sync trigger from "top-level mtime age checks" to "bounded nested-activity / maxdepth 5 retention" but the `test-cleanup.md` update only adds the new case (per plan scope) without fixing the same stale phrase on line 26 of that file. After the PR `test-cleanup.md:26` still reads "top-level mtime age pruning" — the exact phrase corrected in the other four docs.
- **Proposed resolution**: While updating `test-cleanup.md` to add `find-failure-skips-deletion`, also reword line 26: replace "top-level mtime age pruning" with "bounded nested-activity / maxdepth 5 retention (and find-failure fail-safe)" to match the corrected `cleanup.md` trigger.

### FINDING_4:
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Focus area**: correctness
- **Location**: docs/skills.md:47
- **Concern**: Committed `/cleanup` catalog text still says age is measured by top-level mtime only; the plan updates `skills/cleanup/SKILL.md` but not this mirror. Scenario: Operators reading `docs/skills.md` keep the wrong retention model after the four-doc sync; undermines the plan’s anti-drift goal in Failure modes
- **Proposed resolution**: Add `### UPDATED: docs/skills.md` (or extend the `skills/cleanup/SKILL.md` block) to replace line 47 with the same bounded nested-activity phrasing as `SKILL.md`
