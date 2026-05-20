### FINDING_1: **risk-integration** `scripts/session-setup.sh:207-214` — The failure path uses `if ! _stale_out=$("$SCRIPT_DIR/check-stale-plugin.sh" 2>&1); then` followed by `_stale_rc=$?`. In Bash, a successful `if ! …` test leaves `$?` as `0` (the negated condition succeeded), not the helper’s exit status, so `larch_errf` logs `rc=0` even when `check-stale-plugin.sh` exited non-zero (for example invalid CLI usage or future `set -e` failures), which misreports diagnostics and weakens integration triage. **Suggested fix:** Initialize `_stale_rc=0`, assign with `_stale_out=$("$SCRIPT_DIR/check-stale-plugin.sh" 2>&1) || _stale_rc=$?`, then run the `larch_errf` / clear branch when `[[ $_stale_rc -ne 0 ]]` instead of relying on `$?` after `if !`.
- **Reviewer**: dyn-wiring-output.txt
- **Concern**: - **risk-integration** `scripts/session-setup.sh:207-214` — The failure path uses `if ! _stale_out=$("$SCRIPT_DIR/check-stale-plugin.sh" 2>&1); then` followed by `_stale_rc=$?`. In Bash, a successful `if ! …` test leaves `$?` as `0` (the negated condition succeeded), not the helper’s exit status, so `larch_errf` logs `rc=0` even when `check-stale-plugin.sh` exited non-zero (for example invalid CLI usage or future `set -e` failures), which misreports diagnostics and weakens integration triage. **Suggested fix:** Initialize `_stale_rc=0`, assign with `_stale_out=$("$SCRIPT_DIR/check-stale-plugin.sh" 2>&1) || _stale_rc=$?`, then run the `larch_errf` / clear branch when `[[ $_stale_rc -ne 0 ]]` instead of relying on `$?` after `if !`.
- **Suggested revision**: Address the concern above.


### FINDING_13: correctness: docs/installation-and-setup.md:75
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Doc claims the stale-plugin warning runs for /review alongside /implement and /fix-issue. /review calls session-setup with --skip-preflight, so the new check at scripts/session-setup.sh:207-221 is skipped; readers expect a warning that never appears on that path. Remove /review from the entrypoint list or document that only non-skip-preflight session-setup runs trigger the warning.
- **Suggested revision**: Address the concern above.


### FINDING_23: risk-integration: docs/installation-and-setup.md:75
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Doc claims /review is a typical entrypoint for the warning; /review passes --skip-preflight so the stale-plugin block never runs. Operators read that /review will surface the warning but it will not in the default skill flow. List only entrypoints that omit --skip-preflight or note the /review exception explicitly.
- **Suggested revision**: Address the concern above.


