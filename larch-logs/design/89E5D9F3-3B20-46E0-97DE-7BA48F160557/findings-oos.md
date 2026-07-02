### OOS_1: [OUT_OF_SCOPE] Cursor launches measure the pre-preamble resolved prompt, not the strict preamble bytes actually sent on the wire.
- **Description**: [OUT_OF_SCOPE] Cursor launches measure the pre-preamble resolved prompt, not the strict preamble bytes actually sent on the wire.. Scenario: Logging after _review_resolve_prompt but before _review_launch_cursor omits _CURSOR_REVIEW_STRICT_PREAMBLE from prompt_bytes, so Cursor panel-tier totals undercount a large share of lifetime tokens; rankings by agent_file stay directionally useful but are not fully realized.
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: correctness
- **Location**: python/larch/agents/_review_launcher.py:1195-1200
- **Phase**: design



