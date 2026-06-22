### [Plan Review] FINDING_2

### FINDING_2: Primary redactor exceptions outside handled tuple can escape as tracebacks
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: Removing the broad `contextlib.suppress(Exception)` around `redact(text)` while only mapping `TypeError`, `ValueError`, `RuntimeError`, and `OSError` at CLI and dispatch boundaries leaves other primary redactor exceptions uncaught. Those can surface as raw tracebacks instead of the preserved exit-1/log/Tool-Failures path from the retired shell subprocess.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Wrap redact(text) exceptions inside _sanitize_public_text as RuntimeError before local regex sanitizers, or otherwise normalize primary redactor failures into the existing handled tuple while keeping raw text unwritten.


