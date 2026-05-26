# test-generate-code-flow-diagram.sh

Offline harness covering Claude-subprocess generation, Mermaid sanitizer
promotion, sanitizer rejection as a skip, production-shape sanitizer reason
lines, exact token-only `SKIP_REASON` output (without trailing sanitizer
metadata such as `fence=` / `line=`), embedded `=` tokens, empty-token
(`REASON_TOKEN=`) contract, missing-token fallback, and required argument
validation.
