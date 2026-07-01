### [Plan Review] FINDING_3

### FINDING_3: Design Step 0a session-setup dedup lacks plan validation
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: Design Step 0a session-setup dedup stays untested. The plan’s session-setup grep only checks research and review, so `skills/design/SKILL.md` could keep the long inline session-setup prose and still pass every listed validation step, leaving one of the three targeted session-setup consumers duplicated.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add a design-specific grep or before/after check that proves the Step 0a bare session-setup prose was rewritten to the shared-cite form while preserving the single Bash block.

---

**Merge summary**

| Merged ID | Source findings absorbed | Slots |
|-----------|--------------------------|-------|
| FINDING_1 | 1, 5, 7, 10, 11 | 5 slots (review Retain) |
| FINDING_2 | 2, 3, 4, 6, 8, 9, 12, 13 | 6 slots (`--run-id` replace) |
| FINDING_3 | 14 | 1 slot (design test gap) |

All seven inventory slots appear at least once. No `[OUT_OF_SCOPE]` tags in source input; none emitted. Severity merged per **blocking** > **important** rule on FINDING_1 and FINDING_2.

