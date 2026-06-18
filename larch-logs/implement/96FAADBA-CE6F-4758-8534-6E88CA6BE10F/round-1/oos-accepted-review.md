### OOS_1: [OUT_OF_SCOPE] `_redact_text()` fail-opens on redactor failure
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-public-surface-output.txt
- **Severity**: latent
- **Concern**: Pre-existing: `_redact_text()` returns unredacted input when `python/cli.py redact` is missing or errors. Tier B chat-print filing can post secrets if prior corpus checks miss them.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Pre-existing; fail closed to fallback-print when redaction fails
  - From dyn-public-surface-output.txt: Pre-existing: `_redact_text()` at `python/stall_recovery.py:1775-1780` still fail-opens to the original body when `python/cli.py redact secrets` is missing or exits non-zero; Tier B then relies on prior corpus checks only.


### OOS_2: [OUT_OF_SCOPE] Pre-existing resume-hint routing divergence in `_classify_text()`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Pre-existing resume-hint logic in `_classify_text()` differs from bash `resume_hint_for()` step-based routing (e.g., stall at step 10 may get `RESUME_HINT=step2-impl` in Python vs `step8-shippr` in bash).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Implement resume_hint_for() parity or document intentional divergence


### OOS_3: [OUT_OF_SCOPE] Pre-existing missing merge-loop-iteration-cap terminal-step fast path
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Pre-existing: no merge-loop-iteration-cap terminal-step fast path from bash `classify_from_evidence`. Stall at merge-loop-iteration-cap may classify from noisy evidence instead of terminal unrecoverable.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add explicit step-token handling matching bash


