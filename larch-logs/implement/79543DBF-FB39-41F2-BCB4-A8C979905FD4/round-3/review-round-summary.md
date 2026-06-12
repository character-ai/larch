# Review Round 3

- Mode: `diff`
- 8 accepted, 6 rejected (6 neutral)

## Accepted Findings

### FINDING_13: Admission resume matrix lacks coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Admission gate resume success, `RUN_ID` mismatch, blocker exits, report-title exits, and managed-prefix skipping on resume are under-tested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_14: gh issue view retry contract lacks coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The one-retry contract for `gh issue view` is untested. A regression could turn transient `gh` flakes into hard admission failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_15: Preflight skip-clean and stalled-run semantics lack coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Dirty-tree preflight exits, skip flags, stalled-run marker preservation, marker clearing, fetch, sync, and rebase-abort behavior are under-tested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_17: Emergency coder selection lacks coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Emergency-requested routing that forces `coder=claude` is not covered by the coder selection matrix.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_18: Invoke stderr redaction failure paths lack coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Exit 2 stderr redaction for copy-plan and `gh issue view` failures is untested. Secrets or tmpdir paths could leak to operator-visible Step 0 output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_21: Bootstrap accepts parent sentinel without explicit issue number
- **Reviewer(s)**: codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Bootstrap can accept `parent-issue.md` without `st.opts.issue_number`. A stale `IMPLEMENT_TMPDIR` can make a fresh `/implement` resume or mutate the wrong issue instead of failing the issue-number-required-for-resume contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing-output.txt: Address the concern above.


### FINDING_22: Implement skill routing contract can lose coder selection on resume
- **Reviewer(s)**: dyn-routing-contract-output.txt
- **Severity**: important
- **Concern**: `skills/implement/SKILL.md` still describes file-first parsing and dirty-tree resume re-parsing after the migration removed the sourced parsing fences. Resume envelopes omit empty `coder` and `coder_fallback`, so an orchestrator that re-derives coder from `bootstrap-routing.env` can lose implementer selection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-routing-contract-output.txt: Address the concern above.


### FINDING_5: Missing-baseline dirty-tree recovery omits tracked-path sidecar
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: The baseline detector can return on missing-baseline plus untracked ambiguity before writing the tracked-path sidecar. Recovery then sees unknown dirtiness but has no tracked path list to clean known tracked edits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.


