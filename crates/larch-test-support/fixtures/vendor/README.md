# Vendor Contract Fixtures

These replay scripts preserve output shapes from `python/tests/agents/` without
requiring a vendor executable or network access.

- `codex-success.json` combines the structured thread identifier cases from
  `test_parse_codex_session_id_valid_structured_event` with the nested usage
  totals from `test_parse_codex_usage_nested_usage`.
- `cursor-success.json` preserves the JSON result and camel-case token fields
  used by Cursor launcher and usage-recording tests.
- The `claude-*.json` fixtures cover every status asserted by
  `TestClaudeEnvelope`.
- The quota, connectivity, Codex CLI gate, refusal, policy rejection, parse
  error, and truncated fixtures preserve the failure classifier and stream
  cases in `test_agents.py` and `test_launch_review.py`.
- `redaction.json` carries a synthetic secret-shaped token for later diagnostic
  redaction tests. It is not a credential.

Each file uses the `VendorScript` schema. Chunks replay in array order. The
runner flushes each chunk, waits `inter_chunk_delay_ms` before the next chunk,
then exits with `exit_code` unless `never_exit` is true.
