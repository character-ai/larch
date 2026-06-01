### FINDING_10: risk-integration: no test for has_bump=False and defer_push=True together
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: No test covers `has_bump=False` and `defer_push=True` together (`python/test_rebase.py:975-1020`). A future `ship.py` driver passing both flags could regress push/rebump gating without CI signal; only single-flag paths are covered. Combined-flag regression (rebase-only, no rebump, no push) could break silently. Add a test asserting `new_version` is `None`, `pushed` is `False`, no force-push in `runner.calls`, and no classify/apply/push calls with both flags set.
- **Suggested revisions (informational for voters; coder decides)**:


### FINDING_12: security: apply_bump base_remote/base_ref not validated at API boundary
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `apply_bump` accepts `base_remote`/`base_ref` without the bash `^[A-Za-z0-9._/-]+$` guard before `git fetch`/`show` (`python/version_bump.py:472-583`). A future driver forwarding unvalidated base strings: argv lists avoid shell RCE but git may mis-parse flags or revspecs and the publish race guard may check the wrong ref. Validate `base_remote` and `base_ref` at the Python API boundary (shared helper) before any fetch/show, matching `rebase-push.sh`.
- **Suggested revisions (informational for voters; coder decides)**:


### FINDING_5: code-quality: rebase_and_rebump docstring omits flag semantics
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `rebase_and_rebump` docstring (`python/rebase.py:494`) omits `has_bump` and `defer_push` semantics. Driver authors may assume force-push always runs or rebump always classifies. Document flags and that `RebaseResult.pushed` reflects `defer_push`.
- **Suggested revisions (informational for voters; coder decides)**:


