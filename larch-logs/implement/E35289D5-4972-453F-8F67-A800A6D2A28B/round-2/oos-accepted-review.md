### OOS_1: [OUT_OF_SCOPE] Direct session-env sourcing leaves a trust-boundary gap
- **Reviewer(s)**: dyn-dyn-adapter-races
- **Severity**: minor
- **Concern**: `design-step3-entry.sh` still sources session env directly without the resolver’s expected symlink PID checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-adapter-races: Address the concern above.
