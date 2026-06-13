### OOS_1: Aggregated rollup of 4 capped OOS items
- **Description**: Cap 1 (OOS_ISSUES_PER_RUN_CAP) exceeded; the following 4 items were rolled up by skills/implement/scripts/oos-issue-cap.sh:
  - **OOS_1:**: - **Description**: Item 6 describes validation Codex lanes writing token-record sidecars without ledger ingestion; plan only updates research-phase.md. Scenario: Codex validation lane usage at codex-v… [Files: codex-validation-output.txt. research-phase.md. skills/research/references/validation-phase.md:130-187]
  - **OOS_3:**: - **Description**: Research ingestion `env -u` omits `LARCH_TOKEN_SESSION_ID`, which `resolve_session_id` reads before any tmpdir `session-id` file. Scenario: With the planned unsets for `LARCH_TOKEN_… [Files: python/tokens.py:324-330 skills/research/references/research-phase.md:165]
  - **OOS_2:**: - **Description**: Validation-phase Codex lane has no sidecar ingestion step. Scenario: Item 6 cites research Codex lanes beyond the drafter. `codex-validation-output.txt` also gets `${OUTPUT}.token-r… [Files: codex-validation-output.txt research-phase.md skills/research/references/validation-phase.md:129-188]
  - **OOS_1:**: - **Description**: Item 6 text mentions validation Codex lanes but the plan only adds ingestion prose to research-phase.md. Scenario: Validation still collects Codex outputs via `collect-agent-results… [Files: collect-agent-results.sh research-phase.md. skills/research/references/validation-phase.md:180-190]
- **Reviewer**: Combined: capped per-run rollup
- **Vote tally**: N/A — capped rollup of 4 entries
- **Phase**: implement

