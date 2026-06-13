### OOS_4: [OUT_OF_SCOPE] Shim architecture vs planned Python port
- **Reviewer(s)**: dyn-review-cli-parity-output.txt, dyn-review-and-fix-handoff-output.txt
- **Severity**: important
- **Concern**: The C1b plan calls for importable Python implementations in `python/review_pipeline.py`, `python/review_aggregate.py`, `python/review_tally.py`, and `python/compose_review.py`; the branch instead adds thin `run_legacy()` wrappers around scripts moved to `python/legacy_review_shell/`. Runtime parity is mostly preserved on the happy path when `CLAUDE_PLUGIN_ROOT` is set, but this is a shim architecture rather than the planned Python port. `review core` remains a `run_legacy("review-core.sh")` shim rather than a native Python stage graph; nested Step 5 works today via env copy and stdout relay, but adds an extra process hop and leaves no pytest coverage for the default `python3 "$PY_CLI" review core` path with `IMPLEMENT_TMPDIR`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-review-cli-parity-output.txt: Address the concern above.
  - From dyn-review-and-fix-handoff-output.txt: Address the concern above.


