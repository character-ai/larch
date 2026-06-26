### OOS_1: [OUT_OF_SCOPE] Auth-before-retry for Cursor exit-1 zero-byte auth failures not implemented
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-dyn-cursor-degraded-calibration-output.txt
- **Severity**: important
- **Concern**: Auth-before-retry for Cursor exit-1 zero-byte auth failures is not implemented per work item 3. At `python/agents.py:4563-4571`, the review retry loop is unchanged: first auth failure still gets transient retries before postprocess may catch a canned exit-0 sentinel, wasting retry budget and allowing auth-shaped failures to retry into fake-clean instead of being marked degraded early.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, dyn-dyn-cursor-degraded-calibration-output.txt: Address the concern above.

### OOS_2: [OUT_OF_SCOPE] Cursor plan inlining embeds raw plan text without redaction or escaping
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: At `python/rendering.py:1212-1224`, Cursor plan inlining copies plan body verbatim into prompts and sidecars without the redact+escape pipeline used for other untrusted design anchors. Plans derived from issue bodies can contain secrets or delimiter breakout content that reaches Cursor prompt sidecars unredacted, creating a durable leak path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.
