### OOS_1: [OUT_OF_SCOPE] C1b cutover uses bash relocation shims instead of Python port
- **Reviewer(s)**: dyn-review-cli-parity-output.txt, dyn-retired-reference-sweep-output.txt
- **Severity**: important
- **Concern**: The branch relocates bash into `python/legacy_review_shell/` and wraps it with thin Python CLI verbs rather than porting logic into `review_pipeline.py` / `review_aggregate.py` / `review_tally.py` / `compose_review.py` as the plan specified. Runtime parity may hold when `CLAUDE_PLUGIN_ROOT` is set correctly, but this is a structural deviation from the stated C1b design; “Python port” docs overstate how much behavior moved and stale-reference risk remains tied to the legacy tree until a later phase deletes or inlines it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-review-cli-parity-output.txt: - **architecture** The branch relocates bash into `python/legacy_review_shell/` and wraps it with thin Python CLI verbs, rather than porting logic into `review_pipeline.py` / `review_aggregate.py` / `review_tally.py` / `compose_review.py` as the plan specified. Runtime parity may hold when `CLAUDE_PLUGIN_ROOT` is set correctly, but this is a structural deviation from the stated C1b design.
  - From dyn-retired-reference-sweep-output.txt: - **architecture** The C1b modules (`python/review_pipeline.py`, `python/review_aggregate.py`, `python/review_tally.py`, `python/compose_review.py`) delegate to `python/legacy_review_shell/*.sh` via `run_legacy()` rather than inlining the bash logic. That is a valid cutover strategy, but it means “Python port” docs overstate how much behavior moved; stale-reference risk remains tied to the legacy tree until a later phase deletes or inlines it.


### OOS_2: [OUT_OF_SCOPE] Quiet-mode stderr relay bypasses lib-quiet diagnostic stream
- **Reviewer(s)**: dyn-review-cli-parity-output.txt
- **Severity**: important
- **Concern**: `python/review_pipeline.py:33-35` relays captured bash stderr to `sys.stderr` instead of the quiet diagnostic stream (fd 4). With quiet mode enabled, operator diagnostics from legacy scripts may bypass the lib-quiet routing that direct bash invocation used.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-review-cli-parity-output.txt: - **risk-integration** `python/review_pipeline.py:33-35` relays captured bash stderr to `sys.stderr` instead of the quiet diagnostic stream (fd 4). With quiet mode enabled, operator diagnostics from legacy scripts may bypass the lib-quiet routing that direct bash invocation used.


