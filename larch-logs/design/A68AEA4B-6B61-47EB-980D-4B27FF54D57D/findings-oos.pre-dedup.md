### OOS_1: [OUT_OF_SCOPE] Shared implementer-base changes are unnecessary for Gate C plan revision
- **Description**: [OUT_OF_SCOPE] Shared implementer-base changes are unnecessary for Gate C plan revision. Scenario: Only `larch:claude-implementer` would run plan revision under the proposed plan. Editing `agents/_implementer-base.md` still affects generated Cursor/Codex implementer prompts and unrelated generated-artifact churn without serving the Gate C ladder.
- **Reviewer**: Cursor-Arch
- **Severity**: minor
- **Focus area**: architecture
- **Location**: agents/_implementer-base.md
- **Phase**: design



### OOS_2: [OUT_OF_SCOPE] Design exception validation may drift from implement ship gate
- **Description**: [OUT_OF_SCOPE] Design exception validation may drift from implement ship gate. Scenario: `python/larch/implement/ship_guidelines.py::guideline_deviation_exception_present` already validates `Exception:` grammar for ship. The plan adds a separate fence-aware helper only in `architectural_guidelines.py`, so publish and ship can disagree on duplicates, fences, or author/date rules.
- **Reviewer**: Cursor-Arch
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/core/architectural_guidelines.py
- **Phase**: design



### OOS_3: [OUT_OF_SCOPE] New Gate C wire literals are not centralized per G-Cfg-1
- **Description**: [OUT_OF_SCOPE] New Gate C wire literals are not centralized per G-Cfg-1. Scenario: The plan introduces cross-module tokens (`gate-c-return`, `gate-c-validator-fail`, `PUBLISH_REFUSE_REASON=invariant-violation|invalid-guideline-deviation`, per-kind counter basenames) across Python, Bash wrappers, and reference docs without naming `config.py` as the single `Final` source (G-Cfg-1).
- **Reviewer**: Cursor-Arch
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/core/config.py
- **Phase**: design



### OOS_4: [OUT_OF_SCOPE] Design exception validation may drift from implement ship gate
- **Description**: [OUT_OF_SCOPE] Design exception validation may drift from implement ship gate. Scenario: The plan adds a fence-aware Exception helper in architectural_guidelines.py only. ship_guidelines.guideline_deviation_exception_present already enforces rationale, author main-agent, and calendar date without fence-awareness. Two parsers can disagree on the same note and let /design publish accept what /implement would refuse.
- **Reviewer**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/implement/ship_guidelines.py:54-79
- **Phase**: design



### OOS_5: [OUT_OF_SCOPE] Gate C ladder postplan failures lack validator-failure routing
- **Description**: [OUT_OF_SCOPE] Gate C ladder postplan failures lack validator-failure routing. Scenario: The shared validator-failure reference documents Fix-and-retry and Override for Step 2b, Gate B, Gate A, and discussion-round2, but not Gate C ladder revisions after design-step35-settle.sh --site gate-c. A POSTPLAN_RC=10 from a Gate C fix can fall through to ad-hoc handling instead of the documented operator branch.
- **Reviewer**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: skills/design/references/validator-failure.md:19-28
- **Phase**: design



