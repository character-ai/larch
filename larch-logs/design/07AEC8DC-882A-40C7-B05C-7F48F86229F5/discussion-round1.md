## Decision 1: Fix approach for `set -e` violation
- **Question**: Per-site `|| true` (issue's proposal) vs change `step5_parse_kv_tokens` to return 0?
- **Resolution**: Change `step5_parse_kv_tokens` to return 0 unconditionally (drop `return 1` at line 15). Callers already discriminate via `[[ -n "$v" ]]`. ADDITIONALLY: emit a very clear error message to stderr when a wrapper function (e.g., `step5_parse_checks_capture_file`, `step5_parse_lint_capture_file`) finishes without finding its required field(s), so the failure shows up clearly in run logs.
- **Source**: user

## Decision 2: Regression test
- **Question**: Add a regression test exercising both functions under `set -e`?
- **Resolution**: Yes — add to `skills/review-and-fix/scripts/test-review-and-fix.sh`. Cover (a) single-line passing form `RELEVANT_CHECKS_OK=true SITE=... COVERAGE=full`, (b) multi-line failing form with `STATUS=fail` + `FAILURE_REASON=...`, and (c) the wrapper-level "required field missing" stderr emission.
- **Source**: user

## Decision 3: Out-of-scope
- **Question**: Should we audit other scripts for similar `var=$(cmd_returning_1)` patterns under `set -e`?
- **Resolution**: No. Surgical fix limited to `step5_parse_kv_tokens` and its two wrappers. Any similar pattern elsewhere is its own bug.
- **Source**: orchestrator (KARPATHY surgical-changes principle)
