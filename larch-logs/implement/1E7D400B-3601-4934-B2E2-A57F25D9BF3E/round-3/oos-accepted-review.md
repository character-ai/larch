### OOS_6: [OUT_OF_SCOPE] resume_hint_for classifies raw unsafe stall steps
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-shell-kv-output.txt
- **Severity**: latent
- **Concern**: `resume_hint_for` uses raw `stall_step` prefix globs while public output uses sanitized step values, so corrupted values can produce mismatched public titles and recovery dispatch hints.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Apply safe_step_value (or the same allowlist) inside resume_hint_for before branch matching.
  - From cursor-specialist-correctness-output.txt: Align resume_hint_for with safe_step_value or sanitize stall_step before resume-hint selection (follow-up).
  - From cursor-specialist-edge-cases-output.txt: Route resume_hint_for through safe_step_value or classify using the sanitized step token
  - From dyn-shell-kv-output.txt: Address the concern above.


