### OOS_6: [OUT_OF_SCOPE] Design/review panel changes are bundled
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Design/review panel changes are bundled even though the Part 2 plan defers design surfaces. Unrelated harness failures can block merge of the stall-report feature.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### OOS_7: [OUT_OF_SCOPE] Bootstrap coder waterfall order changed
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The branch includes an unrelated `python/bootstrap.py` coder-waterfall reorder that puts Cursor before Codex. This can change implicit implementer selection independently of the stall filing work.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt: Address the concern above.


