---LARCH-REJECTED-BEGIN---
## Considered Plan Review Suggestions (Not Adopted)

These reviewer suggestions were considered but not adopted. Some may already be addressed by the current plan; they are not automatically unimplemented gaps.

### [Plan Review] FINDING_2

### FINDING_2: Explicitly scope both plan-review panel doc_fallback strings
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Concern**: The plan does not explicitly scope the `design.plan_review_panel` `doc_fallback` string. An implementer could update the reviewer and fixer fallbacks while leaving the per-slot auto wording at line 442, violating the requirement to remove Cursor auto prose. The final acceptance grep also may miss isolated per-slot auto wording without an adjacent cursor token.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Name both panel `doc_fallback` strings explicitly in the `config.py` section (include `design.plan_review_panel` at line 442). Replace per-slot auto with Composer 2.5 default-resolution wording. Add `python/larch/core/config.py` to the manual inspection list in the testing strategy.


---LARCH-REJECTED-END---
