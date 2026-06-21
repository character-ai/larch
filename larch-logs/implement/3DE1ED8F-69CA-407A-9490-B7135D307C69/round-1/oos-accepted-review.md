### OOS_1: [OUT_OF_SCOPE] Plan-listed join/rollup/wiring tests largely absent
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-oos-reconciler-output.txt
- **Severity**: important
- **Concern**: Plan-listed cap-rollup, collision, cross-round dedupe, degraded-fetch, and related join/rollup/wiring tests are largely absent from `python/test_analyze_issues.py`. Only a small subset of planned coverage landed; regressions in rollup expansion and cross-repo joins may slip through CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Add the planned focused fixtures when hardening the feature.
  - From cursor-specialist-testing-output.txt: Add fixtures for explicit rollup expansion, exact-count fallback, excess-candidate ambiguity, main-agent aggregate bridging, and single-URL non-fan-out.
  - From dyn-oos-reconciler-output.txt: The plan lists many join/rollup/wiring tests (same-run collisions, cross-round dedupe, cap-rollup ambiguity, offline fetch guard, etc.) that are not present in `python/test_analyze_issues.py`; only a small subset of the planned coverage landed. That is a test-gap risk, not a separate production defect by itself.


### OOS_2: [OUT_OF_SCOPE] Cross-repo filed OOS URLs not filtered against analyzed repo
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Cross-repo filed OOS URLs are not filtered against the analyzed repo. A log URL from another repository could match an unrelated issue number in the local dump.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Skip or warn when parsed URL owner/repo differs from the active `--repo` context.


