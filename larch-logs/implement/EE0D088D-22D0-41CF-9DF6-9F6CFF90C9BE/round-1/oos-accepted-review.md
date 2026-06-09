### OOS_1: [OUT_OF_SCOPE] Token source snapshot accepts arbitrary transcript paths
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `LARCH_CLAUDE_SOURCE_FILE` can accept a snapshot `TRANSCRIPT_PATH` that points outside the intended Claude project directory if the path merely exists.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


### OOS_2: [OUT_OF_SCOPE] Required=false text fallback now blocks optional statuses
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt, dyn-text-fallback-regression-output.txt
- **Severity**: important
- **Concern**: The expanded text fallback regexes in `python/ci_monitor.py` apply to `required=False` callers, changing optional/default ship-pr behavior and making JSON and text fallback disagree on cancelled, skipped, neutral, unknown, waiting, or similar optional states.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt, dyn-text-fallback-regression-output.txt: Address the concern above.


### OOS_3: [OUT_OF_SCOPE] Missing planned design_log_ship unit tests
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-shell-python-bridge-output.txt
- **Severity**: latent
- **Concern**: Planned tests for quiet `main()` contract behavior and settle behavior beyond `CI_MONITOR_MAX_ITERATIONS` are missing, leaving quiet capture and settle-budget regressions unpinned.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-shell-python-bridge-output.txt: Address the concern above.


