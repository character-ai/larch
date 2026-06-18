### OOS_4: [OUT_OF_SCOPE] Unrelated design_lifecycle UTF-8 byte-escape decoding bundled in stall-recovery PR
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-cutover-output.txt
- **Severity**: latent
- **Concern**: `_decode_utf8_byte_escapes` in `python/design_lifecycle.py` is unrelated collateral in the same branch. It may affect `/design` plan-command argv parsing but has no direct stall-recovery impact; track separately if design lifecycle decoding needs its own test coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Track separately if design lifecycle decoding needs its own test coverage
  - From dyn-cutover-output.txt: **`design_lifecycle.py` UTF-8 byte-escape decoding** (`_decode_utf8_byte_escapes`) is unrelated collateral in the same branch; it may affect `/design` plan-command argv decoding but is outside the stall-recovery cutover surface reviewed here.


