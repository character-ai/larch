### OOS_1: [OUT_OF_SCOPE] Static Codex generalist drop basename fallback omits special case
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Static drop fallback omits the `codex-generalist-output.txt` special case. A manifest-miss generalist drop resolves to `codex-specialist-generalist-output.txt`, causing false failure or missed dedupe relative to `_is_static_reviewer_basename` and `_static_slug_for_file`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### OOS_2: [OUT_OF_SCOPE] SECURITY.md omits scrub_log_secrets gate for dropped artifacts
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: SECURITY.md documents only the `redact.redact()` staging path for dropped-slot artifacts and omits the earlier `scrub_log_secrets` fail-closed gate. Operators may assume Cursor-key scrubbing does not run on dropped carriers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### OOS_3: [OUT_OF_SCOPE] SECURITY.md understates pre-commit secret scrub coverage for dropped artifacts
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: SECURITY.md documents `redact.redact()` only, but `run_logs` applies `scrub_log_secrets` first. Operators may underestimate pre-commit secret scrub coverage for dropped artifacts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### OOS_4: [OUT_OF_SCOPE] Prior-round unbounded stderr hardening not re-opened
- **Reviewer(s)**: dyn-dyn-retry-warnings-output.txt
- **Severity**: important
- **Concern**: Prior-round FINDING_6 (unbounded stderr in `dropped-*-*.txt`) was rejected on this branch. Diagnostic byte caps remain a hardening item for committed run logs, but are not re-opened here without new evidence on the current diff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-retry-warnings-output.txt: Address the concern above.

