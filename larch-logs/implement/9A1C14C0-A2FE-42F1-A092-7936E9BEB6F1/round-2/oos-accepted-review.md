### OOS_2: [OUT_OF_SCOPE] plan_block_read_main has the same quiet-init-before-parse pattern
- **Reviewer(s)**: dyn-stream-contracts-output.txt
- **Severity**: latent
- **Concern**: `python/issue_wire.py` also calls `quiet_init()` before `parse_args()`, creating the same stderr-routing pattern outside this branch’s main tracking-issue surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-stream-contracts-output.txt: Address the concern above.


