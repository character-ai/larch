# test-parse-codex-usage.sh

Offline harness for `scripts/parse-codex-usage.sh`.

It covers per-bucket summing, cached-input subtraction, mixed Codex/OpenAI usage shapes, `.msg.usage` precedence over `.usage`, non-JSON wrapper noise, missing/empty/no-usage/zero-total fail-closed branches, defensive `cached_tokens > input_tokens`, argv errors, missing `jq`, and line-streaming multi-event JSONL. The checked-in Codex CLI smoke fixture lives at `scripts/fixtures/parse-codex-usage/codex-events-0.125.jsonl` and is anonymized to token counts plus non-sensitive event metadata.

Run with:

```text
make test-parse-codex-usage
```

The target is registered in `test-harnesses-17`, alongside the token launcher and vendor scraper harnesses.
