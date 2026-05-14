## Goal
Rationalize larch-log file formats: structured where queried, raw where not

## Implementation Plan

Implement all per-file decisions from issue #2105. Changes grouped by dependency order.

### A. Bug fix: redact-tmpdir-paths.sh line 9
- Replace `[^[:space:]]*` with `[^/"\\[:space:]]*` in the third sed expression (the `/larch/sessions/` pattern). This bounds the parent-path class so it cannot cross JSON string delimiters (`"`, `\`) or path boundaries (`/`), preventing the multi-occurrence collapsing bug.
- Add regression case to `scripts/test-redact-tmpdir-paths.sh`: feed a JSONL line with two `/larch/sessions/claude-implement-...` occurrences, assert (a) both replaced with `<TMPDIR>` and (b) output passes `python3 -c "import json,sys; json.loads(sys.stdin.read())"`.
- Wire `test-redact-tmpdir-paths` target to `make lint` (already wired; verify no change needed).

### B. model_roster population in larch-log.sh
- At the manifest init site (around line 106), read `CLAUDE_CODE_MODEL` env var (fallback `CLAUDE_MODEL`, fallback `"unknown"`).
- Populate `"model_roster": {"main": "<value>"}` instead of `{}`.
- Update `scripts/test-larch-logs-manifest.sh`: add assertion that `.model_roster.main` is a non-empty string after init.

### C. lib-larch-log.sh: add json-object sanitizer
- Add a `json-object` case in `larch_log_validate_batch_payload`: validate that `jq . < file` exits 0 and the file parses as a JSON object (not array, not primitive). Use `jq -e 'type == "object"'`.
- Update `test-larch-logs-batches.sh` sanitizer case to allow `json-object`.

### D. larch-log-batches.sh: update registry
Changes:
- `plan-review-tally`: `.ndjson → .json`, `append → replace`, `json-lines → json-object`
- `code-review-tally`: `.ndjson → .json`, `append → replace`, `json-lines → json-object`
- `review-findings-full`: `.ndjson → .md`, `append → replace`, `json-lines → none`
- `timing-report`: `.md → .json`, keep `replace`, keep `none`
- `token-report`: `.md → .json`, keep `replace`, keep `none`
- Update `scripts/test-larch-logs-batches.sh`: update expected batch list (names unchanged), update extension/mode/sanitizer assertions for the five changed batches.

### E. compose-review-findings.sh: switch to markdown output
- Change `emit_record` to write markdown sections instead of JSON lines: `printf '### %s: %s [%s/%s]\n\n%s\n\n' "$id" "$reviewer_redacted" "$phase" "$outcome" "$body_redacted" >> "$TMP_OUT"`.
- Remove the `jq -nc` JSON encoding; use direct printf with redacted field values.
- Change `MODE=ndjson` → `MODE=markdown` in output.
- Update `scripts/test-compose-review-findings.sh`:
  - Change the `line_count` check to use `grep -c '^###'` for finding section count.
  - Replace `jq -e` assertions with `grep` assertions against the markdown structure.
  - Keep the redaction check.

### F. token-report.sh and timing-report.sh: JSON output mode
For `token-report.sh`:
- Add `--format json` flag (default `markdown`).
- When `--format json`: after computing the token data, output a JSON object matching the shape: `{"vendors": [...], "claude": {"per_step": [...], "totals": {...}}, "codex": {...}, ...}` rather than the markdown table. Reuse existing data gathering logic; just switch the output serialization.

For `timing-report.sh`:
- Add `--format json` flag (default `markdown`).
- When `--format json`: output `{"workflow_path": "...", "per_step": [...], "total_seconds": N, "total_hms": "HH:MM:SS", "vendor_task_averages": [...]}`.

### G. refresh-run-logs.sh: call with --format json
- Change `token-report.sh --full --output ... .md` → `token-report.sh --full --format json --output ... .json`
- Change `timing-report.sh --full --output ... .md` → `timing-report.sh --full --format json --output ... .json`
- Update `--input-file` to use `.json` extension in subsequent `larch-log.sh write` calls.

### H. skills/implement/SKILL.md: update pre-bump log flush calls
- Change the two render calls (token-report, timing-report) to use `--format json` and `.json` extensions.
- Update larch-log batch references from `.ndjson` → `.json` for tally batches (mention in Step 5 tally section) and `.md` → (drop) for findings-full.
- Clear the "Known limitation" line at Step 5 / `compose-review-findings.sh` call (the known limitation about accepted code-review findings remains until that upstream wiring is done; note it in the comment instead).

### I. skills/report-tokens/scripts/run-analysis.sh: JSON consumer
- In the scan loop: try `token-report.json` first, fall back to `token-report.md` (backward compat).
- For `plan-review-tally`: try `plan-review-tally.json` first (read `"body"` field), fall back to `plan-review-tally.ndjson`.
- For JSON token report: instead of `cat token_report` as a text blob, `json.load()` the file and extract the structured totals directly (bypassing the markdown parser). Pass the structured data through the existing `cost_vendor` and `total_cost` functions.
- For timing JSON: if `timing-report.json` is present, read `workflow_path` directly.
- Keep all markdown-path code for fallback compatibility.

### J. Doc updates
- `scripts/larch-log-batches.md`: update registry table for the five changed batches.
- `scripts/compose-review-findings.md`: update output mode from NDJSON to markdown, describe section format.
- `skills/report-tokens/SKILL.md`: update input-format reference.


## Test plan
- `make test-redact-tmpdir-paths` — new regression case passes
- `make test-larch-logs-manifest` — model_roster assertion passes
- `make test-larch-logs-batches` — updated extension/sanitizer expectations pass
- `make test-compose-review-findings` — markdown output assertions pass
- `/relevant-checks` on the resulting branch
