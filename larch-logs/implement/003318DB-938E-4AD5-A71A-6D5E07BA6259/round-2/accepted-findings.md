### FINDING_14: correctness: scripts/dispatch-code-voters.sh:263-266
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Breadcrumb is emitted only when cp succeeds; plan shows cp with || true then unconditional emit_breadcrumb. When cp fails but mv still promotes retry output, no breadcrumb is emitted, reducing observability vs the plan and hiding preservation failure. Emit breadcrumb after the cp attempt (still on stderr for KV capture), or split success vs best-effort-failed messaging.
- **Suggested revision**: Address the concern above.


### FINDING_16: risk-integration: scripts/dispatch-code-voters.sh:244
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Unconditional rm -f first_pass_sidecar under set -e without fail-open guard. If unlink fails (e.g. path is a directory, permission denied) or rm is non-zero, dispatch-code-voters.sh exits before retry/parse handling for that run. Use rm -f "$first_pass_sidecar" || true (or equivalent) so cleanup matches the best-effort contract used for cp.
- **Suggested revision**: Address the concern above.


### FINDING_3: **[correctness]** [`scripts/dispatch-code-voters.sh:263-272`](scripts/dispatch-code-voters.sh): On the parse-retry success path, `cp "$voter_path" "$first_pass_sidecar" 2>/dev/null` is wrapped in `if cp …; then … fi`, so a failed copy produces **no** sidecar and **no** breadcrumb, while `mv "$retry_output" "$voter_path"` and the rest of the success path still run (`scripts/dispatch-code-voters.sh:267-275`). That matches fail-open promotion, but it means a “successful retry” from the caller’s perspective can still **silently** lose the intended first-pass preservation (for example disk full), with errors suppressed by `2>/dev/null`. Suggested fix: keep control flow identical, but on `cp` failure emit a stderr-only warning (for example via `larch_err` / a dedicated warn helper) that does not pollute stdout used for `PARSE_RATE_STATUS`, optionally still omitting the success breadcrumb.
- **Reviewer**: dyn-sidecar-lifecycle-output.txt
- **Concern**: - **[correctness]** [`scripts/dispatch-code-voters.sh:263-272`](scripts/dispatch-code-voters.sh): On the parse-retry success path, `cp "$voter_path" "$first_pass_sidecar" 2>/dev/null` is wrapped in `if cp …; then … fi`, so a failed copy produces **no** sidecar and **no** breadcrumb, while `mv "$retry_output" "$voter_path"` and the rest of the success path still run (`scripts/dispatch-code-voters.sh:267-275`). That matches fail-open promotion, but it means a “successful retry” from the caller’s perspective can still **silently** lose the intended first-pass preservation (for example disk full), with errors suppressed by `2>/dev/null`. Suggested fix: keep control flow identical, but on `cp` failure emit a stderr-only warning (for example via `larch_err` / a dedicated warn helper) that does not pollute stdout used for `PARSE_RATE_STATUS`, optionally still omitting the success breadcrumb.
- **Suggested revision**: Address the concern above.


