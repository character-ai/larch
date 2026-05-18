## Goal
HTML-escape XML-like tags in compose-review-findings.sh finding bodies to prevent agent-lint failures

## Implementation Plan

### Goal
HTML-escape `<`, `>`, and `&` in finding-body text at composition time in
`scripts/compose-review-findings.sh` so that XML-like tags cited by reviewers
land escaped in `review-findings-full.md` instead of raw, preventing
agent-lint/markdownlint failures.

### Files to modify
1. `scripts/compose-review-findings.sh` — add `escape_finding_body()` + apply in `emit_record()`
2. `scripts/test-compose-review-findings.sh` — add regression case for XML-like tags
3. `scripts/compose-review-findings.md` — document the escaping behavior

### Approach

**`compose-review-findings.sh`**:
- Add `escape_finding_body()` after the existing `redact_field()` helper:
  ```bash
  escape_finding_body() {
      sed -e 's/&/\&amp;/g' -e 's/</\&lt;/g' -e 's/>/\&gt;/g'
  }
  ```
  Mirrors `escape_prompt_data` in `scripts/scout-dynamic-archetypes.sh`.
- In `emit_record()`, pipe `body_redacted` through `escape_finding_body` before
  writing the printf output to `$TMP_OUT`:
  ```bash
  body_escaped="$(printf '%s' "$body_redacted" | escape_finding_body)" || fail "HTML escape failed for prose_body in $id"
  ```
  Then use `body_escaped` instead of `body_redacted` in the printf statement.
- Note: `&` escaping is unconditional (not idempotent). Per the issue, this is
  accepted: the output is for lint-tool ingestion; visual rendering is unchanged.

**`scripts/test-compose-review-findings.sh`**:
- Add a new test section after the existing "accepted and rejected findings" test:
  ```
  === HTML-escape XML-like tags in finding body ===
  ```
- Input: a finding body containing `</reviewer_diff>` and `<scout_notes>`
- Assert output contains `&lt;/reviewer_diff&gt;` and `&lt;scout_notes&gt;`
- Verify the raw `<` / `>` forms are absent.

**`scripts/compose-review-findings.md`**:
- Add one sentence noting that finding bodies are HTML-escaped (`<`, `>`, `&`)
  before writing to the output file, so XML-like tags cited in security findings
  are encoded and do not trigger markdownlint/agent-lint XML-element warnings.


## Test plan
- Run `scripts/test-compose-review-findings.sh` — all assertions must pass
- Run `/relevant-checks` (pre-commit + agent-lint) on modified files
