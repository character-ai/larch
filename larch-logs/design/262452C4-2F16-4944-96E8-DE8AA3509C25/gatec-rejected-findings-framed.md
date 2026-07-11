---LARCH-REJECTED-BEGIN---
## Considered Plan Review Suggestions (Not Adopted)

These reviewer suggestions were considered but not adopted. Some may already be addressed by the current plan; they are not automatically unimplemented gaps.

### [Plan Review] FINDING_1

### FINDING_1: Anti-halt contract may be weakened by shortened or recap-style wording
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: minor
- **Concern**: The planned Step 5b.5 anti-halt requirement may preserve only a shortened continuation phrase and omit an explicit prohibition on free-form Step 5c checklist recaps. This could weaken the existing mandatory continuation guard or allow pre-Step-5c narration that duplicates Step 5c duties.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Pin the full existing blockquote (or require `contains` of both the anti-halt prefix and `after the skip marker exists or the candidate write/failure-log path is complete`). Reject free-form recaps with separate `not_contains` examples from the issue anchor, not by shortening the normative anti-halt text.
  - From Cursor-Pragmatic: At the Step 5b.5 anti-halt blockquote, add one sentence: after candidate write or generation-failure logging, emit only the required blockquote and continue; do not print Step 5c compose/validate/publish checklists or validity recaps. Pin that sentence in test-design-structure.sh.


### [Plan Review] FINDING_5

### FINDING_5:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: minor
- **Focus area**: correctness
- **Location**: plan.txt:9,19,28,36
- **Concern**: [SCOPE-REDUCTION] The optional pre-check preserves an unnecessary command that can produce one of the exact unwanted harness lines. Scenario: Step 5c already performs authoritative sanitization, so running this optional probe adds no required behavior and may still render a shell-command count that the issue asks to suppress as much as feasible
- **Proposed resolution**: Remove the optional pre-check permission and its related command-specific prompt and test requirements; proceed directly from candidate authoring to the required Step 5c continuation

---LARCH-REJECTED-END---
