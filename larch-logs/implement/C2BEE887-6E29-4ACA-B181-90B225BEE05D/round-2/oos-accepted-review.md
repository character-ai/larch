### OOS_9: [OUT_OF_SCOPE] Missing plan-mandated `python/test_agents.py` diagnostic and stderr-tail coverage
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-diagnostics-parity-output.txt
- **Severity**: important
- **Concern**: Plan-required pytest coverage for canonical stderr-tail helpers, vendor append redaction boundaries, CI resolver delegation, Claude timeout branches, Codex tmpdir/repo-root symlink rejection, compose-unredacted vs append-redacted boundaries, `LARCH_FAILED_AGENT_STDERR_TAIL_LINES=0`, multibyte UTF-8 byte-cap truncation, and explicit 50/8000 stall-tail regression is largely absent from `python/test_agents.py`. Without these fixtures, regressions (wrong defaults, character slicing instead of byte caps, shrunk stall tails, redaction inside compose, accepted symlinked design tmpdirs) can land while CI stays green.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-diagnostics-parity-output.txt: Address the concern above.


### OOS_10: [OUT_OF_SCOPE] Missing design drafter integration tests for new `sys.executable` + `agent launch-*-drafter` argv
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The plan called for Step 2b tests in `python/test_design_lifecycle.py` and `python/test_design_cli_ports.py` pinning `sys.executable` + `agent launch-*-drafter` argv and a drafter CLI registry test. Those files were not updated on this branch; `design_lifecycle.py` dispatch changed without integration tests locking the new command shape.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### OOS_11: [OUT_OF_SCOPE] `plan_review_panel.py` writes unredacted vendor stderr on waterfall failure
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: On waterfall failure, `dispatch_panel` writes raw `proc.stderr` to `plan-review-panel-failure.log` without `redact tmpdir-paths` / `redact secrets`. Vendor stderr can contain sensitive tokens.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


