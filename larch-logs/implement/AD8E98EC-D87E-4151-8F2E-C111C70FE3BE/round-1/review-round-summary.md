# Review Round 1

- Mode: `diff`
- 13 accepted, 10 rejected (8 exonerated)

## Accepted Findings

### FINDING_1: risk-integration: scripts/launch-review.sh:1047-1055
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Exit-0 empty-.result retry omits external_is_quota_failure guards present on the exit-code transient branch. Quota/rate-limit text on stderr with exit 0 and empty .result triggers up to three cursor calls and ends as CURSOR_EMPTY_RESPONSE instead of quota classification. Add the same ! external_is_quota_failure checks on SIDECAR and ${OUTPUT}.diag to the empty-result retry condition; optionally skip when envelope error/type matches quota.
- **Suggested revision**: Address the concern above.


### FINDING_12: risk-integration: scripts/test-launch-review.sh:1545-1571
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Default LARCH_CURSOR_LAUNCH_JITTER_MS=250 applies to all cursor harness launches; only the four new empty-result cases disable it. Every legacy cursor case gains 0–250ms random sleep per invocation, stretching test-harnesses-2 (~52s shard) and diverging from the plan’s harness determinism guidance (LARCH_CURSOR_LAUNCH_JITTER_MS=0). Export LARCH_CURSOR_LAUNCH_JITTER_MS=0 at cursor suite entry; opt in to jitter only in targeted cases.
- **Suggested revision**: Address the concern above.


### FINDING_13: risk-integration: scripts/test-launch-review.sh:2899-2929
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] SL-cursor-empty-retry-exhausted does not assert ${OUTPUT}.json persistence. Acceptance requires the full envelope at ${OUTPUT}.json; a regression that stops cp-ing the envelope would still pass .diag greps. Add test -f and jq/grep assertions on ${OUT_CURSOR_EMPTY_EXH}.json envelope fields.
- **Suggested revision**: Address the concern above.


### FINDING_14: risk-integration: scripts/launch-review.sh:1038-1055
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Shared TRANSIENT_ATTEMPT budget for exit-code transients and exit-0 empty .result is untested in combination. Mixed exit-8 then empty-result failures may allow fewer empty retries than the three-call empty-only case documents. Add a counting-stub case covering exit 8 followed by empty .result with explicit invoke-count expectations.
- **Suggested revision**: Address the concern above.


### FINDING_16: security: scripts/launch-review.sh:1168-1193
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] New .diag writer copies Cursor envelope error and metadata without redact-secrets or tmpdir-path scrubbing before persistence. Cursor error JSON may contain tokens or internal URLs; collector embeds raw .diag into FAILURE_REASON (500-char truncate only), risking secret leakage into session logs and operator-visible review output. Pipe assembled diagnostic text through redact-tmpdir-paths.sh and redact-secrets.sh before writing .diag; avoid publishing unredacted ${OUTPUT}.json.
- **Suggested revision**: Address the concern above.


### FINDING_17: risk-integration: scripts/launch-review.sh:1047-1055
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Exit-0 empty-.result retry omits auth/quota sidecar guards used on the exit-code transient branch. Cursor returns exit 0, empty .result, but stderr contains usage-limit or auth signatures; launcher retries up to 3 times per slot instead of fast-failing like exit-8 quota cases. Before empty-result continue, skip retry when external_is_auth_failure or external_is_quota_failure matches $SIDECAR or ${OUTPUT}.diag (mirror lines 1038-1040).
- **Suggested revision**: Address the concern above.


### FINDING_27: **correctness** `scripts/launch-review.sh:992-997` — `LARCH_CURSOR_LAUNCH_JITTER_MS` parsing uses `case "${LARCH_CURSOR_LAUNCH_JITTER_MS:-250}"` for matching but assigns `_CURSOR_JITTER_MS=$LARCH_CURSOR_LAUNCH_JITTER_MS` in the `*)` branch. When the variable is **unset**, the case word is `250` (from `:-250`), so `*)` runs and assigns from the still-unset variable, clearing the initial `_CURSOR_JITTER_MS=250` to an empty string. `(( _CURSOR_JITTER_MS > 0 ))` then treats that as 0 and **skips jitter entirely**, contradicting the documented default of 250 ms in `docs/configuration-and-permissions.md:212-214`. Empty string, non-numeric, explicit `0`, and explicit positive integers behave as documented (empty/non-numeric keep the initializer `250`; `0` and positive values use the dedicated branches). This diverges from the established idiom in the same function (`MAX_AUTH_RETRIES=${LARCH_EXTERNAL_AUTH_RETRIES:-5}` then `case "$MAX_AUTH_RETRIES" in …`) and from `scripts/check-reviewers.sh:43-46`, which default-assign first and only mutate the target variable inside `case`. **Suggested fix:** adopt the probe-style two-step parse, e.g. `_CURSOR_JITTER_MS="${LARCH_CURSOR_LAUNCH_JITTER_MS:-250}"` followed by `case "$_CURSOR_JITTER_MS" in ''|*[!0-9]*) _CURSOR_JITTER_MS=250 ;; esac` (no `*)` assignment from the raw env var), or assign `_CURSOR_JITTER_MS=$REPLY` / the case match word in `*)` instead of `$LARCH_CURSOR_LAUNCH_JITTER_MS`.
- **Reviewer**: dyn-shell-var-parsing-output.txt
- **Concern**: - **correctness** `scripts/launch-review.sh:992-997` — `LARCH_CURSOR_LAUNCH_JITTER_MS` parsing uses `case "${LARCH_CURSOR_LAUNCH_JITTER_MS:-250}"` for matching but assigns `_CURSOR_JITTER_MS=$LARCH_CURSOR_LAUNCH_JITTER_MS` in the `*)` branch. When the variable is **unset**, the case word is `250` (from `:-250`), so `*)` runs and assigns from the still-unset variable, clearing the initial `_CURSOR_JITTER_MS=250` to an empty string. `(( _CURSOR_JITTER_MS > 0 ))` then treats that as 0 and **skips jitter entirely**, contradicting the documented default of 250 ms in `docs/configuration-and-permissions.md:212-214`. Empty string, non-numeric, explicit `0`, and explicit positive integers behave as documented (empty/non-numeric keep the initializer `250`; `0` and positive values use the dedicated branches). This diverges from the established idiom in the same function (`MAX_AUTH_RETRIES=${LARCH_EXTERNAL_AUTH_RETRIES:-5}` then `case "$MAX_AUTH_RETRIES" in …`) and from `scripts/check-reviewers.sh:43-46`, which default-assign first and only mutate the target variable inside `case`. **Suggested fix:** adopt the probe-style two-step parse, e.g. `_CURSOR_JITTER_MS="${LARCH_CURSOR_LAUNCH_JITTER_MS:-250}"` followed by `case "$_CURSOR_JITTER_MS" in ''|*[!0-9]*) _CURSOR_JITTER_MS=250 ;; esac` (no `*)` assignment from the raw env var), or assign `_CURSOR_JITTER_MS=$REPLY` / the case match word in `*)` instead of `$LARCH_CURSOR_LAUNCH_JITTER_MS`.
- **Suggested revision**: Address the concern above.


### FINDING_30: **correctness** `scripts/launch-review.sh:1038-1055` — `TRANSIENT_ATTEMPT` is shared by the exit-code transient branch (`external_is_transient_infra_failure`, which only fires when stdout is **byte-empty** at `scripts/lib-external-launcher-common.sh:343-349`) and the new exit-0 empty-`.result` branch. After two exit 4/8 failures with an empty `$OUTPUT`, `TRANSIENT_ATTEMPT` becomes 3; on the next invocation, exit 0 with a non-empty JSON envelope and `(.result // "") == ""` hits the empty branch but fails `TRANSIENT_ATTEMPT <= MAX_TRANSIENT_RETRIES` (3 > 2), so **no empty-result retry runs** on the failure shape this issue targets. Total invocations: 3 (two exit-code retries + one terminal empty envelope), not the “up to 3 attempts all retrying empty `.result`” path the new tests exercise. **Suggested fix:** Add a harness case (e.g. stub: attempt 1–2 `exit 8` with empty stdout, attempt 3 exit 0 + empty `.result`) and either document this cross-class budget in `scripts/launch-review.md` or adjust policy (separate counters, or reset `TRANSIENT_ATTEMPT` when the failure class changes from exit-code-transient to exit-0-empty).
- **Reviewer**: dyn-retry-state-output.txt
- **Concern**: - **correctness** `scripts/launch-review.sh:1038-1055` — `TRANSIENT_ATTEMPT` is shared by the exit-code transient branch (`external_is_transient_infra_failure`, which only fires when stdout is **byte-empty** at `scripts/lib-external-launcher-common.sh:343-349`) and the new exit-0 empty-`.result` branch. After two exit 4/8 failures with an empty `$OUTPUT`, `TRANSIENT_ATTEMPT` becomes 3; on the next invocation, exit 0 with a non-empty JSON envelope and `(.result // "") == ""` hits the empty branch but fails `TRANSIENT_ATTEMPT <= MAX_TRANSIENT_RETRIES` (3 > 2), so **no empty-result retry runs** on the failure shape this issue targets. Total invocations: 3 (two exit-code retries + one terminal empty envelope), not the “up to 3 attempts all retrying empty `.result`” path the new tests exercise. **Suggested fix:** Add a harness case (e.g. stub: attempt 1–2 `exit 8` with empty stdout, attempt 3 exit 0 + empty `.result`) and either document this cross-class budget in `scripts/launch-review.md` or adjust policy (separate counters, or reset `TRANSIENT_ATTEMPT` when the failure class changes from exit-code-transient to exit-0-empty).
- **Suggested revision**: Address the concern above.


### FINDING_31: **correctness** `scripts/launch-review.sh:1047-1055` — The exit-code transient branch skips retry when `external_is_quota_failure` matches `$SIDECAR` or `${OUTPUT}.diag` (`1039-1040`), but the exit-0 empty-`.result` branch has no analogous guard. A burst that returns **exit 0**, empty `.result`, and quota/rate-limit text only on stderr (or in envelope fields not scanned here) can still burn up to two empty-result retries, unlike `SL-quota-no-retry-cursor-8` at `scripts/test-launch-review.sh:2994-3031` for exit 8. **Suggested fix:** Before the empty-result `continue`, apply the same quota (and optionally auth) exclusions as the exit-code branch; add a stub case with exit 0 + empty `.result` + usage-limit stderr asserting a single invocation.
- **Reviewer**: dyn-retry-state-output.txt
- **Concern**: - **correctness** `scripts/launch-review.sh:1047-1055` — The exit-code transient branch skips retry when `external_is_quota_failure` matches `$SIDECAR` or `${OUTPUT}.diag` (`1039-1040`), but the exit-0 empty-`.result` branch has no analogous guard. A burst that returns **exit 0**, empty `.result`, and quota/rate-limit text only on stderr (or in envelope fields not scanned here) can still burn up to two empty-result retries, unlike `SL-quota-no-retry-cursor-8` at `scripts/test-launch-review.sh:2994-3031` for exit 8. **Suggested fix:** Before the empty-result `continue`, apply the same quota (and optionally auth) exclusions as the exit-code branch; add a stub case with exit 0 + empty `.result` + usage-limit stderr asserting a single invocation.
- **Suggested revision**: Address the concern above.


### FINDING_32: **correctness** `scripts/launch-review.sh:1176-1183` — `${OUTPUT}.diag` reports `after %s transient retries` using `_diag_retries=$((TRANSIENT_ATTEMPT - 1))`, which counts **both** exit-code and empty-result increments. After two exit 8 empty-file transients and a terminal exit-0 empty envelope, the diag says “after 2 transient retries” even though **zero** empty-`.result` retries occurred—misleading for the instrumentation goal in the plan. **Suggested fix:** Track separate counters (e.g. `_empty_result_retries` vs exit-code transients) or phrase the diag with both counts / failure classes.
- **Reviewer**: dyn-retry-state-output.txt
- **Concern**: - **correctness** `scripts/launch-review.sh:1176-1183` — `${OUTPUT}.diag` reports `after %s transient retries` using `_diag_retries=$((TRANSIENT_ATTEMPT - 1))`, which counts **both** exit-code and empty-result increments. After two exit 8 empty-file transients and a terminal exit-0 empty envelope, the diag says “after 2 transient retries” even though **zero** empty-`.result` retries occurred—misleading for the instrumentation goal in the plan. **Suggested fix:** Track separate counters (e.g. `_empty_result_retries` vs exit-code transients) or phrase the diag with both counts / failure classes.
- **Suggested revision**: Address the concern above.


### FINDING_33: **correctness** `scripts/test-launch-review.sh:2863-2991` — New coverage is homogeneous (pure empty, pure exhausted empty, sentinel, retry disabled) plus existing `SL-transient-retry-cursor-8` (`2832-2861`); there is **no** mixed-order case for (1) exit-code transient then exit-0 empty, (2) exit-0 empty then auth failure, or (3) auth retries after `TRANSIENT_ATTEMPT` is exhausted. Manual trace: (2) empty on attempt 1 increments `TRANSIENT_ATTEMPT` to 2 and `continue`s; attempt 2 auth failure still hits the auth branch at `1057-1062` (`AUTH_ATTEMPT` increments, `TRANSIENT_ATTEMPT` unchanged)—auth retry is **not** blocked. (3) Auth retries never increment `TRANSIENT_ATTEMPT`, so they **cannot** deplete the transient budget—scout concern (3) is not a defect. **Suggested fix:** Add at least `SL-cursor-transient8-then-empty` and `SL-cursor-empty-then-auth` counting-stub cases so mixed behavior is pinned.
- **Reviewer**: dyn-retry-state-output.txt
- **Concern**: - **correctness** `scripts/test-launch-review.sh:2863-2991` — New coverage is homogeneous (pure empty, pure exhausted empty, sentinel, retry disabled) plus existing `SL-transient-retry-cursor-8` (`2832-2861`); there is **no** mixed-order case for (1) exit-code transient then exit-0 empty, (2) exit-0 empty then auth failure, or (3) auth retries after `TRANSIENT_ATTEMPT` is exhausted. Manual trace: (2) empty on attempt 1 increments `TRANSIENT_ATTEMPT` to 2 and `continue`s; attempt 2 auth failure still hits the auth branch at `1057-1062` (`AUTH_ATTEMPT` increments, `TRANSIENT_ATTEMPT` unchanged)—auth retry is **not** blocked. (3) Auth retries never increment `TRANSIENT_ATTEMPT`, so they **cannot** deplete the transient budget—scout concern (3) is not a defect. **Suggested fix:** Add at least `SL-cursor-transient8-then-empty` and `SL-cursor-empty-then-auth` counting-stub cases so mixed behavior is pinned.
- **Suggested revision**: Address the concern above.


### FINDING_7: correctness: scripts/launch-review.sh:1047-1055
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Exit-0 empty-.result retry omits auth/quota guards used by the exit-code transient branch. Cursor returns exit 0, empty .result, and quota/auth stderr; launcher retries twice (~12s+ backoff) then still emits CURSOR_EMPTY_RESPONSE instead of failing fast as quota/auth. Mirror external_is_auth_failure / external_is_quota_failure checks before empty-.result continue.
- **Suggested revision**: Address the concern above.


### FINDING_9: risk-integration: scripts/test-launch-review.sh:1758-1760
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Case B2 does not disable retry delay/jitter; default empty-result retry triples invocations and adds exponential backoff. Harness case B2 wall time grows by ~12s+ per run; CI slowdown without assertion failure. Set LARCH_TRANSIENT_RETRY_DELAY=0 and LARCH_CURSOR_LAUNCH_JITTER_MS=0 (or disable empty retry) for B2.
- **Suggested revision**: Address the concern above.


