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

- `0`: at least one `type=="token_usage"` event parsed and total usage is non-zero.
- `1`: fail-closed parse branch: missing/empty events file, missing `jq`, `jq` execution failure, no `token_usage` objects, zero total, or `cached_tokens > input_tokens`.
- `2`: argv/usage error.

Failure stdout is empty. Failure stderr is one short diagnostic.

## Bucket Math

OpenAI usage schemas report `input_tokens` as gross input, with cached tokens as a detail bucket inside that gross count. The parser records fresh input as `max(input_tokens - cached_tokens, 0)`, records `cached_tokens` as `CACHED_INPUT`, records `output_tokens` as `OUTPUT`, and computes `TOTAL` from those emitted buckets. If cached tokens exceed input tokens, the parser exits `1` so launchers skip the token row instead of double-billing or inventing data.

## Schema Probes

Only JSON objects with `type=="token_usage"` (or `.msg.type=="token_usage"` for wrapped events) are counted. For each counted event, usage is detected in this order:

```text
usage payload = .msg.usage
             // .usage
             // synthetic top-level branch when any of:
                .msg.input_tokens, .msg.cached_input_tokens, .msg.output_tokens,
                .input_tokens, .cached_input_tokens, .output_tokens
                is present
```

Each token field is then coalesced once per counted event, in this order:

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

This handles top-level Codex-native `cached_input_tokens`, `.msg` top-level token fields, Responses-style `input_tokens_details.cached_tokens`, and wrappers that nest usage under `.msg.usage`. Non-JSON wrapper noise is skipped by `fromjson?`.

Example JSONL:

```jsonl
{"type":"token_usage","msg":{"usage":{"input_tokens":1000,"cached_input_tokens":900,"output_tokens":50}}}
{"type":"token_usage","usage":{"input_tokens":20,"input_tokens_details":{"cached_tokens":5},"output_tokens":7}}
{"type":"token_usage","input_tokens":3,"cached_input_tokens":1,"output_tokens":2}
```

Current consumers are `scripts/launch-review.sh`, `scripts/launch-codex-implement.sh`, `scripts/launch-codex-ci.sh`, and `scripts/test-parse-codex-usage.sh`.
