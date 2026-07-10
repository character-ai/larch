### FINDING_4: [OUT_OF_SCOPE] PID residuals hardcode the cache root
- **Reviewer(s)**: dyn-dyn-session-cleanup
- **Severity**: nit
- **Concern**: The PID residual paths still hardcode `Path.home()/.cache/larch/sessions` while other session helpers honor `XDG_CACHE_HOME`; that split is intentionally preserved here, but broader cache-root unification remains follow-up work.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-session-cleanup: Address the concern above.

