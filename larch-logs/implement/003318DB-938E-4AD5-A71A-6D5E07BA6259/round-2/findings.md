### FINDING_1: **Important** (`risk-integration`) [scripts/dispatch-code-voters.sh:236-246](scripts/dispatch-code-voters.sh): `check_and_retry_voter_parse_rate` unconditionally runs `rm -f "$first_pass_sidecar"` before the `NOT_SUBSTANTIVE` gate, so every call removes the derived `*-vote-output-first-pass.txt` (or `*-first-pass`) path even when parse-rate status is `OK` or `SKIPPED` and no retry runs. **Scenario:** A prior run (or operator) left a first-pass sidecar under the same canonical voter basename in a reused or long-lived `REVIEW_TMPDIR`; a later successful parse-rate check deletes that file before returning, destroying preserved first-pass evidence though the new run never overwrote the canonical voter file. **Fix:** Drop the entry `rm -f`, or restrict removal to the retry-success branch immediately before `cp` (or only when you are about to replace stale content), so non-retry paths never unlink the sidecar.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 1. **Important** (`risk-integration`) [scripts/dispatch-code-voters.sh:236-246](scripts/dispatch-code-voters.sh): `check_and_retry_voter_parse_rate` unconditionally runs `rm -f "$first_pass_sidecar"` before the `NOT_SUBSTANTIVE` gate, so every call removes the derived `*-vote-output-first-pass.txt` (or `*-first-pass`) path even when parse-rate status is `OK` or `SKIPPED` and no retry runs. **Scenario:** A prior run (or operator) left a first-pass sidecar under the same canonical voter basename in a reused or long-lived `REVIEW_TMPDIR`; a later successful parse-rate check deletes that file before returning, destroying preserved first-pass evidence though the new run never overwrote the canonical voter file. **Fix:** Drop the entry `rm -f`, or restrict removal to the retry-success branch immediately before `cp` (or only when you are about to replace stale content), so non-retry paths never unlink the sidecar.
- **Suggested revision**: Address the concern above.

### FINDING_2: **Nit** (`risk-integration`) [scripts/dispatch-code-voters.sh:263-265](scripts/dispatch-code-voters.sh): The breadcrumb runs only when `cp` succeeds; on full-disk or permission failure the retry path still promotes via `mv`, but operators get no stderr breadcrumb. If parity with the stated “fail-open + observability” intent matters, emit a distinct diagnostic when `cp` fails (without failing the retry).
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 2. **Nit** (`risk-integration`) [scripts/dispatch-code-voters.sh:263-265](scripts/dispatch-code-voters.sh): The breadcrumb runs only when `cp` succeeds; on full-disk or permission failure the retry path still promotes via `mv`, but operators get no stderr breadcrumb. If parity with the stated “fail-open + observability” intent matters, emit a distinct diagnostic when `cp` fails (without failing the retry). **Security lens summary:** `cp`/`mv` operands stay quoted; `emit_breadcrumb` logs only `basename` of the sidecar, which limits path exfiltration in logs. New artifacts go through `stage_round_artifact`’s default branch and `larch_log_redact_file` in [scripts/larch-log.sh:101-121](scripts/larch-log.sh), so first-pass text is not less redacted than other plain `*.txt` round artifacts. No new hard-coded secrets, eval/injection sinks, or auth changes appear in the diff. The main regression is **artifact integrity** (unconditional unlink), not a classic injection bug.
- **Suggested revision**: Address the concern above.

### FINDING_3: **[correctness]** [`scripts/dispatch-code-voters.sh:263-272`](scripts/dispatch-code-voters.sh): On the parse-retry success path, `cp "$voter_path" "$first_pass_sidecar" 2>/dev/null` is wrapped in `if cp …; then … fi`, so a failed copy produces **no** sidecar and **no** breadcrumb, while `mv "$retry_output" "$voter_path"` and the rest of the success path still run (`scripts/dispatch-code-voters.sh:267-275`). That matches fail-open promotion, but it means a “successful retry” from the caller’s perspective can still **silently** lose the intended first-pass preservation (for example disk full), with errors suppressed by `2>/dev/null`. Suggested fix: keep control flow identical, but on `cp` failure emit a stderr-only warning (for example via `larch_err` / a dedicated warn helper) that does not pollute stdout used for `PARSE_RATE_STATUS`, optionally still omitting the success breadcrumb.
- **Reviewer**: dyn-sidecar-lifecycle-output.txt
- **Concern**: - **[correctness]** [`scripts/dispatch-code-voters.sh:263-272`](scripts/dispatch-code-voters.sh): On the parse-retry success path, `cp "$voter_path" "$first_pass_sidecar" 2>/dev/null` is wrapped in `if cp …; then … fi`, so a failed copy produces **no** sidecar and **no** breadcrumb, while `mv "$retry_output" "$voter_path"` and the rest of the success path still run (`scripts/dispatch-code-voters.sh:267-275`). That matches fail-open promotion, but it means a “successful retry” from the caller’s perspective can still **silently** lose the intended first-pass preservation (for example disk full), with errors suppressed by `2>/dev/null`. Suggested fix: keep control flow identical, but on `cp` failure emit a stderr-only warning (for example via `larch_err` / a dedicated warn helper) that does not pollute stdout used for `PARSE_RATE_STATUS`, optionally still omitting the success breadcrumb.
- **Suggested revision**: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] **[correctness]** (behavior clarification, not a defect): [`scripts/dispatch-code-voters.sh:240-246`](scripts/dispatch-code-voters.sh) runs `rm -f "$first_pass_sidecar"` before `check_voter_parse_rate` and the early return on non-`NOT_SUBSTANTIVE` statuses, so any pre-existing colliding first-pass sidecar beside that `voter_path` is cleared even when no retry runs; combined with [`scripts/dispatch-code-voters.sh:279-280`](scripts/dispatch-code-voters.sh) (retry-fail path never `cp`s), this matches the harness expectations in [`scripts/test-dispatch-code-voters.sh:381-382`](scripts/test-dispatch-code-voters.sh), [`scripts/test-dispatch-code-voters.sh:478-481`](scripts/test-dispatch-code-voters.sh), and [`scripts/test-dispatch-code-voters.sh:544-566`](scripts/test-dispatch-code-voters.sh) (stale seed removed; no sidecar on fail).
- **Reviewer**: dyn-sidecar-lifecycle-output.txt
- **Concern**: - **[correctness]** (behavior clarification, not a defect): [`scripts/dispatch-code-voters.sh:240-246`](scripts/dispatch-code-voters.sh) runs `rm -f "$first_pass_sidecar"` before `check_voter_parse_rate` and the early return on non-`NOT_SUBSTANTIVE` statuses, so any pre-existing colliding first-pass sidecar beside that `voter_path` is cleared even when no retry runs; combined with [`scripts/dispatch-code-voters.sh:279-280`](scripts/dispatch-code-voters.sh) (retry-fail path never `cp`s), this matches the harness expectations in [`scripts/test-dispatch-code-voters.sh:381-382`](scripts/test-dispatch-code-voters.sh), [`scripts/test-dispatch-code-voters.sh:478-481`](scripts/test-dispatch-code-voters.sh), and [`scripts/test-dispatch-code-voters.sh:544-566`](scripts/test-dispatch-code-voters.sh) (stale seed removed; no sidecar on fail).
- **Suggested revision**: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] **[risk-integration]** [`larch-logs/implement/003318DB-938E-4AD5-A71A-6D5E07BA6259/manifest.json:1-20`](larch-logs/implement/003318DB-938E-4AD5-A71A-6D5E07BA6259/manifest.json) and sibling new files under the same directory in the branch diff: committed implement run metadata (including `status: "in-progress"`) is orthogonal to `check_and_retry_voter_parse_rate` lifecycle; worth reconciling with your repo’s run-log commit policy (`docs/run-logs.md`) outside this sidecar-correctness pass.
- **Reviewer**: dyn-sidecar-lifecycle-output.txt
- **Concern**: - **[risk-integration]** [`larch-logs/implement/003318DB-938E-4AD5-A71A-6D5E07BA6259/manifest.json:1-20`](larch-logs/implement/003318DB-938E-4AD5-A71A-6D5E07BA6259/manifest.json) and sibling new files under the same directory in the branch diff: committed implement run metadata (including `status: "in-progress"`) is orthogonal to `check_and_retry_voter_parse_rate` lifecycle; worth reconciling with your repo’s run-log commit policy (`docs/run-logs.md`) outside this sidecar-correctness pass.
- **Suggested revision**: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] code-quality: larch-logs/implement/003318DB-938E-4AD5-A71A-6D5E07BA6259/plan-goals-test.md
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Flushed run log repeats the full implementation plan in committed metadata. PR noise for consumers skimming code changes. Out of scope per review instructions on larch-logs flush commits; no product change requested.
- **Suggested revision**: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] risk-integration: scripts/dispatch-code-voters.sh (pre-existing mv/rm patterns)
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Same set -e semantics on rm/mv existed around retry cleanup and promotion. Not introduced solely by this diff; observation that new leading rm increases how often this class of failure can fire. No change required for this PR scope; optional hardening elsewhere if desired.
- **Suggested revision**: Address the concern above.

### FINDING_8: architecture: scripts/dispatch-code-voters.sh:240-244
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Unplanned rm -f of first_pass_sidecar before status check. Deletes any existing first-pass sidecar even when returning immediately with OK parse rate. Document as intentional hygiene or restrict rm to the retry-success branch per plan scope.
- **Suggested revision**: Address the concern above.

### FINDING_9: code-quality: scripts/dispatch-code-voters.md:126-127 vs scripts/dispatch-code-voters.sh:189-192
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Doc implies generic best-effort copy/breadcrumb; code emits breadcrumb only after successful cp. Operators may expect a breadcrumb whenever retry promotion succeeds even if copy failed; minor mismatch only. Note in doc that breadcrumb is tied to successful sidecar write, or emit a different stderr line when cp fails but promotion proceeds.
- **Suggested revision**: Address the concern above.

### FINDING_10: code-quality: scripts/dispatch-code-voters.sh:240-246
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Unconditional rm -f of the first-pass sidecar path runs before parse-rate classification, including on OK/SKIPPED early return; not described in the feature plan or dispatch-code-voters.md. Extra no-retry filesystem side effect and potential confusion when operators expect only retry-success paths to touch sidecars. Document the cleanup contract in dispatch-code-voters.md or move rm to immediately before cp on the retry-success branch if stale cleanup is not required on OK paths.
- **Suggested revision**: Address the concern above.

### FINDING_11: code-quality: scripts/dispatch-code-voters.sh:240-252
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Duplicate case "$voter_path" blocks compute sidecar and retry temp paths separately. Future edits could update one case and forget the other, reintroducing inconsistent suffix handling. Consolidate into one case arm that assigns both locals.
- **Suggested revision**: Address the concern above.

### FINDING_12: code-quality: scripts/dispatch-code-voters.sh:263-266
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Breadcrumb is emitted only when cp succeeds; plan text described fail-open cp with breadcrumb around the promotion. When cp fails but mv still succeeds, retry succeeds without the observability breadcrumb the plan promised. Use cp ... || true (or emit a separate warning) and emit the breadcrumb whenever promotion proceeds, without tying it solely to cp success.
- **Suggested revision**: Address the concern above.

### FINDING_13: correctness: scripts/dispatch-code-voters.sh:240-246;scripts/test-dispatch-code-voters.sh (retry_fail_claude/codex blocks)
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Entry rm -f of the sidecar plus tests that seed then assert ! -e conflate cleanup with no-copy-on-failure. A future change could remove entry rm while wrongly adding a cp on the fail branch; tests might still pass or fail for the wrong reason relative to plan intent. Remove unconditional sidecar rm or adjust tests to prove no copy on failure without relying on prior deletion.
- **Suggested revision**: Address the concern above.

### FINDING_14: correctness: scripts/dispatch-code-voters.sh:263-266
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Breadcrumb is emitted only when cp succeeds; plan shows cp with || true then unconditional emit_breadcrumb. When cp fails but mv still promotes retry output, no breadcrumb is emitted, reducing observability vs the plan and hiding preservation failure. Emit breadcrumb after the cp attempt (still on stderr for KV capture), or split success vs best-effort-failed messaging.
- **Suggested revision**: Address the concern above.

### FINDING_15: risk-integration: scripts/dispatch-code-voters.sh:240-246
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Unconditional rm -f of first_pass_sidecar before parse-rate outcome is known A pre-existing *-vote-output-first-pass.txt beside the canonical voter file is deleted when check_and_retry_voter_parse_rate runs even if status is OK and no retry occurs (e.g. reused REVIEW_TMPDIR or tooling-seeded sidecar). Move rm to the retry-success path before cp and/or only after NOT_SUBSTANTIVE; adjust harness to assert no sidecar without depending on entry-time deletion.
- **Suggested revision**: Address the concern above.

### FINDING_16: risk-integration: scripts/dispatch-code-voters.sh:244
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Unconditional rm -f first_pass_sidecar under set -e without fail-open guard. If unlink fails (e.g. path is a directory, permission denied) or rm is non-zero, dispatch-code-voters.sh exits before retry/parse handling for that run. Use rm -f "$first_pass_sidecar" || true (or equivalent) so cleanup matches the best-effort contract used for cp.
- **Suggested revision**: Address the concern above.

### FINDING_17: risk-integration: scripts/dispatch-code-voters.sh:263-265
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] emit_breadcrumb is forced through >&2 to avoid polluting command-substitution stdout for parse-rate status. Quiet-log FD layout or capture idioms could change, risking breadcrumb text leaking into VOTER_*_PARSE_RATE_STATUS or mis-routing diagnostics. Re-validate whenever lib-quiet init or the $(check_and_retry_voter_parse_rate ...) call pattern changes; consider a dedicated helper that logs without touching FD1 of the capture subshell.
- **Suggested revision**: Address the concern above.

