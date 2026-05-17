## Goal
Document oos-issues NDJSON schema and mandate jq -nc for compact JSON output

## Implementation Plan

Two documentation edits, no code changes.

### 1. scripts/larch-log-batches.md

Add a new `## oos-issues record schema` section immediately after the existing `## Tally record schema` section. The section must:
- State that each `larch-log.sh append --batch oos-issues` call MUST supply a record file with exactly one compact (single-line) JSON object.
- Warn that `jq -n` without `-c` produces multi-line pretty-printed JSON that the `json-lines` sanitizer rejects.
- Document the record schema: `{"phase":"<pipeline-phase>","step":"9a.1","category":"OOS","body":"<sanitized-markdown-body>"}`.
- Show a correct `jq -nc --arg body "..." '...'` example command.
- Note that the body must be sanitized (secrets → <REDACTED-TOKEN>, internal URLs → <INTERNAL-URL>, PII → <REDACTED-PII>) before inclusion.

### 2. skills/implement/SKILL.md — Carve-outs paragraph (line ~370)

After the sentence: "Non-accepted OOS (voting rejected) land in the `oos-issues` larch-log batch under the 'Rejected / Out-of-Scope Observations (not filed)' sub-block."

Add a sentence that: 
- Mandates `jq -nc` (compact mode) when composing the record file — the `-c` flag produces a single-line JSON object required by the `json-lines` sanitizer.
- Explicitly warns that `jq -n` without `-c` produces multi-line pretty-printed JSON that the sanitizer rejects.
- States the record schema: `{"phase":"<pipeline-phase>","step":"9a.1","category":"OOS","body":"<sanitized-markdown-body>"}`.


## Test plan
- pre-commit (markdownlint MD038 check on changed .md files)
- agent-lint on full repo
