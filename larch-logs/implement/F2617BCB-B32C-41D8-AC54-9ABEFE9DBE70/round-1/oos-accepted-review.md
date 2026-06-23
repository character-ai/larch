### OOS_1: [OUT_OF_SCOPE] Tests cover character length only, not UTF-8 byte limit
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Tests in `python/test_oos_filer.py` (roughly lines 762–812) assert character-length bounds for the new guard but not UTF-8 byte overflow. A regression where multibyte content passes the char cap but exceeds the byte cap would not be caught by CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt: Address the concern above.


### OOS_2: [OUT_OF_SCOPE] Design OOS path lacks body-size guard
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `python/design_oos.py` has no body-size guard. Large design OOS bodies can still fail at GitHub create time. A shared byte-based fit helper should be reused when the design path is in scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


