# parse-codex-usage.sh

Parses a Codex `exec --json` JSONL events file and emits per-bucket token usage for launcher token accounting.

## Interface

```text
parse-codex-usage.sh EVENTS_JSONL
```

Success stdout is exactly four lines, in order:

```text
INPUT=<uncached_input>
CACHED_INPUT=<cache_read>
OUTPUT=<output>
TOTAL=<input + cached_input + output>
```

Exit codes:

- `0`: at least one usage object parsed and total usage is non-zero.
- `1`: fail-closed parse branch: missing/empty events file, missing `jq`, no usage objects, zero total, or `cached_tokens > input_tokens`.
- `2`: argv/usage error.

Failure stdout is empty. Failure stderr is one short diagnostic.

## Bucket Math

OpenAI usage schemas report `input_tokens` as gross input, with cached tokens as a detail bucket inside that gross count. The parser records fresh input as `max(input_tokens - cached_tokens, 0)`, records `cached_tokens` as `CACHED_INPUT`, records `output_tokens` as `OUTPUT`, and computes `TOTAL` from those emitted buckets. If cached tokens exceed input tokens, the parser exits `1` so launchers skip the token row instead of double-billing or inventing data.

## Schema Probes

Each field is coalesced once per event, in this order:

```text
input_tokens  = .msg.usage.input_tokens // .usage.input_tokens
             // .input_tokens // 0
cached_tokens = .msg.usage.cached_input_tokens
             // .msg.usage.input_tokens_details.cached_tokens
             // .usage.cached_input_tokens
             // .usage.input_tokens_details.cached_tokens
             // .cached_input_tokens
             // .input_tokens_details.cached_tokens
             // 0
output_tokens = .msg.usage.output_tokens // .usage.output_tokens
              // .output_tokens // 0
```

This handles top-level Codex-native `cached_input_tokens`, Responses-style `input_tokens_details.cached_tokens`, and wrappers that nest usage under `.msg.usage`. Non-JSON wrapper noise is skipped by `fromjson?`.

Example JSONL:

```jsonl
{"msg":{"usage":{"input_tokens":1000,"cached_input_tokens":900,"output_tokens":50}}}
{"usage":{"input_tokens":20,"input_tokens_details":{"cached_tokens":5},"output_tokens":7}}
{"input_tokens":3,"cached_input_tokens":1,"output_tokens":2}
```

Current consumers are `scripts/launch-review.sh`, `scripts/launch-codex-implement.sh`, `scripts/launch-codex-ci.sh`, and `scripts/test-parse-codex-usage.sh`.
