# Review Round 3

- Mode: `diff`
- 1 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Review failure paths skip stderr_sink merge when base .failure-diag exists
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-generic-output.txt
- **Severity**: important
- **Concern**: Review failure paths call `_ensure_failure_diag_composed`, which returns early when a non-empty base `.failure-diag` already exists (`python/agents.py:1505-1508`), while implement paths call `_compose_failure_diag` unconditionally. After `run_external_agent()` leaves a generic base `.failure-diag`, `stderr_sink` may hold the real launcher/auth detail. On brainstorm failures (`codex-brainstorm` / `cursor-brainstorm`), `_review_write_failure_sink()` can write the sink after the base carrier exists (`python/agents.py:4682-4683`), so recomposition is skipped and sink content is never merged. `_review_emit_launcher_result` and `_review_append_launch_failure` (`python/agents.py:4126`, `4334-4337`) then resolve via `_review_failure_source` / `resolve_failure_diagnostic_source`, which prefer the stale base carrier over the sink. Downstream `LAUNCHER_FAILURE_*` and append-failure output miss sink content.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Call _compose_failure_diag(output, sink=stderr_sink) unconditionally on review failure paths (or append-only merge when populated), matching implement and add a regression test.
  - From cursor-specialist-edge-cases-output.txt: Call _compose_failure_diag (not _ensure_failure_diag_composed) on review failure emit/append paths to match implement parity.
  - From codex-generic-output.txt: Call `_compose_failure_diag(output, sink=stderr_sink)` for non-zero launcher exits before resolving the source, or force recomposition after `_review_write_failure_sink()` writes the sink.


