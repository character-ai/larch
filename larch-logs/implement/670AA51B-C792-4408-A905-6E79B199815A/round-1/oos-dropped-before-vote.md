### OOS_1: [OUT_OF_SCOPE] Missing regression guard for eager run_logs imports
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: important
- **Concern**: There is no dedicated CI lint or structural test to prevent eager `run_logs` imports from being reintroduced on the `run_log_flush → final_report` load path. That leaves the cycle vulnerable to coming back later without a targeted failure signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.
