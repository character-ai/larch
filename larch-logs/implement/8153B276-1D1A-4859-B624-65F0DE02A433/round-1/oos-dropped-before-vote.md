### OOS_2: [OUT_OF_SCOPE] STEP4_MODE is dead config
- **Reviewer(s)**: dyn-dyn-bgjob-design
- **Severity**: nit
- **Concern**: `STEP4_MODE=foreground|background` no longer changes transport; the mode sidecar is mostly dead configuration surface and may confuse operators or resume logic that still branches on it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-bgjob-design: Address the concern above.

