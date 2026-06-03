### FINDING_1: risk-integration: scripts/launch-review.sh:1047-1055
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Exit-0 empty-.result retry omits external_is_quota_failure guards present on the exit-code transient branch. Quota/rate-limit text on stderr with exit 0 and empty .result triggers up to three cursor calls and ends as CURSOR_EMPTY_RESPONSE instead of quota classification. Add the same ! external_is_quota_failure checks on SIDECAR and ${OUTPUT}.diag to the empty-result retry condition; optionally skip when envelope error/type matches quota.
- **Suggested revision**: Address the concern above.

### FINDING_2: risk-integration: scripts/collect-agent-results.sh:869-871
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Collector hardcodes generic FAILURE_REASON for CURSOR_EMPTY_RESPONSE and does not read the new launcher .diag KV. Operators relying only on collector stdout or round-summary rows miss envelope type/is_error/error until #3392 reads .diag. Prefer FAILURE_REASON from ${OUTPUT}.diag when present, or document the limitation until #3392.
- **Suggested revision**: Address the concern above.

### FINDING_3: code-quality: scripts/launch-review.sh:1168-1175
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Eight separate jq calls extract diagnostic fields from the same JSON file. Field list drift or performance overhead if envelope shape grows. Collapse to one jq program emitting all diagnostic fields.
- **Suggested revision**: Address the concern above.

### FINDING_4: code-quality: scripts/launch-review.sh:1005-1013
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Cursor uses _cursor_transient_backoff; codex still inlines duplicate backoff logic. Future edits may change backoff in one path only. Share helper or add a cross-reference comment in the codex block.
- **Suggested revision**: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] architecture: scripts/launch-review.sh:985-986
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] TRANSIENT_ATTEMPT persists across auth retries without reset. Earlier transient exhaustion can block later empty-result retries within the same auth loop. Reset or document transient counter semantics on auth continue (pre-existing).
- **Suggested revision**: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] correctness: scripts/launch-review.sh:1051
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Whitespace-only .result is not treated as empty for retry or CURSOR_EMPTY_RESPONSE promotion. A space-padded .result could pass as non-empty and bypass both retry and empty marker. Normalize .result with trim in jq probe if Cursor ever emits whitespace-only results (pre-existing boundary).
- **Suggested revision**: Address the concern above.

### FINDING_7: correctness: scripts/launch-review.sh:1047-1055
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Exit-0 empty-.result retry omits auth/quota guards used by the exit-code transient branch. Cursor returns exit 0, empty .result, and quota/auth stderr; launcher retries twice (~12s+ backoff) then still emits CURSOR_EMPTY_RESPONSE instead of failing fast as quota/auth. Mirror external_is_auth_failure / external_is_quota_failure checks before empty-.result continue.
- **Suggested revision**: Address the concern above.

### FINDING_8: correctness: scripts/launch-review.sh:1051
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Whitespace-only .result is not treated as empty for retry or CURSOR_EMPTY_RESPONSE promotion. Backend returns {"result":" "}; no retry, no CURSOR_EMPTY_RESPONSE; downstream may classify ambiguously vs explicit empty-backend marker. Extend jq probe to treat whitespace-only .result as empty, or document as out of scope.
- **Suggested revision**: Address the concern above.

### FINDING_9: risk-integration: scripts/test-launch-review.sh:1758-1760
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Case B2 does not disable retry delay/jitter; default empty-result retry triples invocations and adds exponential backoff. Harness case B2 wall time grows by ~12s+ per run; CI slowdown without assertion failure. Set LARCH_TRANSIENT_RETRY_DELAY=0 and LARCH_CURSOR_LAUNCH_JITTER_MS=0 (or disable empty retry) for B2.
- **Suggested revision**: Address the concern above.

### FINDING_10: correctness: scripts/launch-review.sh:1176-1179
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Dead else sets _diag_retries=0; TRANSIENT_ATTEMPT is always >= 1 at diagnostic time. Dead code may confuse future edits about retry-count semantics. Remove else branch or rebase counter semantics on completed retries only.
- **Suggested revision**: Address the concern above.

### FINDING_11: correctness: scripts/launch-review.sh:1168-1175
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Plan mentioned explicit rate-limit fields; implementation relies on generic type/subtype/error only. If Cursor puts quota detail only in undocumented keys, .diag may miss it despite plan wording. Add explicit jq extractions when schema is known, or document reliance on type/error.
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

### FINDING_15: risk-integration: scripts/test-launch-review.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] No harness for jq-missing degradation of empty-result retry/diagnostics. Hosts without jq silently lose retry and .diag enrichment; behavior change would go unnoticed. Optional PATH-without-jq case asserting single stub call and no retry.
- **Suggested revision**: Address the concern above.

### FINDING_16: security: scripts/launch-review.sh:1168-1193
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] New .diag writer copies Cursor envelope error and metadata without redact-secrets or tmpdir-path scrubbing before persistence. Cursor error JSON may contain tokens or internal URLs; collector embeds raw .diag into FAILURE_REASON (500-char truncate only), risking secret leakage into session logs and operator-visible review output. Pipe assembled diagnostic text through redact-tmpdir-paths.sh and redact-secrets.sh before writing .diag; avoid publishing unredacted ${OUTPUT}.json.
- **Suggested revision**: Address the concern above.

### FINDING_17: risk-integration: scripts/launch-review.sh:1047-1055
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Exit-0 empty-.result retry omits auth/quota sidecar guards used on the exit-code transient branch. Cursor returns exit 0, empty .result, but stderr contains usage-limit or auth signatures; launcher retries up to 3 times per slot instead of fast-failing like exit-8 quota cases. Before empty-result continue, skip retry when external_is_auth_failure or external_is_quota_failure matches $SIDECAR or ${OUTPUT}.diag (mirror lines 1038-1040).
- **Suggested revision**: Address the concern above.

### FINDING_18: architecture: scripts/launch-review.sh:986,1042,1052
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] TRANSIENT_ATTEMPT is shared across exit-code and empty-result retries. A slot uses a transient exit retry first, then gets exit-0 empty .result; it may get fewer than two empty-specific retries with no per-class visibility in .diag. Document combined budget in launch-review.md or use separate counters if empty retries must be independent.
- **Suggested revision**: Address the concern above.

### FINDING_19: risk-integration: scripts/collect-agent-results.sh:869-871
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Collector still replaces FAILURE_REASON with a generic string for CURSOR_EMPTY_RESPONSE. New .diag records envelope fields on disk but panel/collector rows stay generic until #3392. Call build_failure_reason or parse FAILURE_REASON from .diag before the hardcoded overwrite, or land #3392 in the same release.
- **Suggested revision**: Address the concern above.

### FINDING_20: correctness: scripts/launch-review.sh:1051,1166
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Whitespace-only .result is not treated as empty. Cursor returns .result with only spaces; no retry, no CURSOR_EMPTY_RESPONSE, downstream format gates see whitespace. Extend jq probe to treat trim-empty .result like absent/empty if that shape is possible.
- **Suggested revision**: Address the concern above.

### FINDING_21: [OUT_OF_SCOPE] architecture: scripts/collect-agent-results.sh:869-872
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Pre-existing collector FAILURE_REASON overwrite for cursor sentinels. Same as in-scope #3; noted as coordination surface for #3392. Address in #3392 or collector follow-up.
- **Suggested revision**: Address the concern above.

### FINDING_22: [OUT_OF_SCOPE] code-quality: scripts/launch-review.sh:535-605
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Codex transient backoff not factored like cursor helper. Future backoff changes may diverge between tools. Factor shared helper when touching codex path (optional).
- **Suggested revision**: Address the concern above.

### FINDING_23: `170d8b6b5` — Handle exit-0 empty Cursor `.result` with retry, diagnostics, and launch jitter
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - `170d8b6b5` — Handle exit-0 empty Cursor `.result` with retry, diagnostics, and launch jitter
- **Suggested revision**: Address the concern above.

### FINDING_24: `cd318f2d7` — chore(larch-logs) flush (run log; excluded from plan review per policy)
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - `cd318f2d7` — chore(larch-logs) flush (run log; excluded from plan review per policy)
- **Suggested revision**: Address the concern above.

### FINDING_25: [OUT_OF_SCOPE] **nit** `scripts/launch-review.sh:1048` — The binding design decision says both env vars are “read once,” but `LARCH_CURSOR_RETRY_EMPTY_RESULT` is evaluated on every auth-loop iteration rather than cached before the loop like `LARCH_CURSOR_LAUNCH_JITTER_MS`. **Why OOS:** behavioral equivalence holds for a stable env; this is a stylistic deviation from a binding comment, not a functional gap against acceptance criteria.
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: 1. **nit** `scripts/launch-review.sh:1048` — The binding design decision says both env vars are “read once,” but `LARCH_CURSOR_RETRY_EMPTY_RESULT` is evaluated on every auth-loop iteration rather than cached before the loop like `LARCH_CURSOR_LAUNCH_JITTER_MS`. **Why OOS:** behavioral equivalence holds for a stable env; this is a stylistic deviation from a binding comment, not a functional gap against acceptance criteria.
- **Suggested revision**: Address the concern above.

### FINDING_26: [OUT_OF_SCOPE] **latent** `scripts/collect-agent-results.sh:345-357` — `build_failure_reason` truncates `.diag` content to 500 characters via `sanitize_failure_reason`, so rich envelope fields written by this PR may be shortened in collector-emitted `FAILURE_REASON` even though `${OUTPUT}.diag` and `${OUTPUT}.json` retain full detail. **Why OOS:** `collect-agent-results.sh` is outside the plan’s file list; the plan explicitly preserves the full envelope at `${OUTPUT}.json` and only requires `.diag` to record fields on disk.
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: 2. **latent** `scripts/collect-agent-results.sh:345-357` — `build_failure_reason` truncates `.diag` content to 500 characters via `sanitize_failure_reason`, so rich envelope fields written by this PR may be shortened in collector-emitted `FAILURE_REASON` even though `${OUTPUT}.diag` and `${OUTPUT}.json` retain full detail. **Why OOS:** `collect-agent-results.sh` is outside the plan’s file list; the plan explicitly preserves the full envelope at `${OUTPUT}.json` and only requires `.diag` to record fields on disk.
- **Suggested revision**: Address the concern above.

### FINDING_27: **correctness** `scripts/launch-review.sh:992-997` — `LARCH_CURSOR_LAUNCH_JITTER_MS` parsing uses `case "${LARCH_CURSOR_LAUNCH_JITTER_MS:-250}"` for matching but assigns `_CURSOR_JITTER_MS=$LARCH_CURSOR_LAUNCH_JITTER_MS` in the `*)` branch. When the variable is **unset**, the case word is `250` (from `:-250`), so `*)` runs and assigns from the still-unset variable, clearing the initial `_CURSOR_JITTER_MS=250` to an empty string. `(( _CURSOR_JITTER_MS > 0 ))` then treats that as 0 and **skips jitter entirely**, contradicting the documented default of 250 ms in `docs/configuration-and-permissions.md:212-214`. Empty string, non-numeric, explicit `0`, and explicit positive integers behave as documented (empty/non-numeric keep the initializer `250`; `0` and positive values use the dedicated branches). This diverges from the established idiom in the same function (`MAX_AUTH_RETRIES=${LARCH_EXTERNAL_AUTH_RETRIES:-5}` then `case "$MAX_AUTH_RETRIES" in …`) and from `scripts/check-reviewers.sh:43-46`, which default-assign first and only mutate the target variable inside `case`. **Suggested fix:** adopt the probe-style two-step parse, e.g. `_CURSOR_JITTER_MS="${LARCH_CURSOR_LAUNCH_JITTER_MS:-250}"` followed by `case "$_CURSOR_JITTER_MS" in ''|*[!0-9]*) _CURSOR_JITTER_MS=250 ;; esac` (no `*)` assignment from the raw env var), or assign `_CURSOR_JITTER_MS=$REPLY` / the case match word in `*)` instead of `$LARCH_CURSOR_LAUNCH_JITTER_MS`.
- **Reviewer**: dyn-shell-var-parsing-output.txt
- **Concern**: - **correctness** `scripts/launch-review.sh:992-997` — `LARCH_CURSOR_LAUNCH_JITTER_MS` parsing uses `case "${LARCH_CURSOR_LAUNCH_JITTER_MS:-250}"` for matching but assigns `_CURSOR_JITTER_MS=$LARCH_CURSOR_LAUNCH_JITTER_MS` in the `*)` branch. When the variable is **unset**, the case word is `250` (from `:-250`), so `*)` runs and assigns from the still-unset variable, clearing the initial `_CURSOR_JITTER_MS=250` to an empty string. `(( _CURSOR_JITTER_MS > 0 ))` then treats that as 0 and **skips jitter entirely**, contradicting the documented default of 250 ms in `docs/configuration-and-permissions.md:212-214`. Empty string, non-numeric, explicit `0`, and explicit positive integers behave as documented (empty/non-numeric keep the initializer `250`; `0` and positive values use the dedicated branches). This diverges from the established idiom in the same function (`MAX_AUTH_RETRIES=${LARCH_EXTERNAL_AUTH_RETRIES:-5}` then `case "$MAX_AUTH_RETRIES" in …`) and from `scripts/check-reviewers.sh:43-46`, which default-assign first and only mutate the target variable inside `case`. **Suggested fix:** adopt the probe-style two-step parse, e.g. `_CURSOR_JITTER_MS="${LARCH_CURSOR_LAUNCH_JITTER_MS:-250}"` followed by `case "$_CURSOR_JITTER_MS" in ''|*[!0-9]*) _CURSOR_JITTER_MS=250 ;; esac` (no `*)` assignment from the raw env var), or assign `_CURSOR_JITTER_MS=$REPLY` / the case match word in `*)` instead of `$LARCH_CURSOR_LAUNCH_JITTER_MS`.
- **Suggested revision**: Address the concern above.

### FINDING_28: [OUT_OF_SCOPE] correctness
- **Reviewer**: dyn-shell-var-parsing-output.txt
- **Concern**: - **correctness** `scripts/launch-review.sh:1047-1051` — `LARCH_CURSOR_RETRY_EMPTY_RESULT` uses `[[ "${LARCH_CURSOR_RETRY_EMPTY_RESULT:-1}" != "0" ]]`, which matches the plan/docs for unset, empty, non-`0`, and literal `0`; only exact `0` disables retry. No defect found in the traced cases.
- **Suggested revision**: Address the concern above.

### FINDING_29: [OUT_OF_SCOPE] code-quality
- **Reviewer**: dyn-shell-var-parsing-output.txt
- **Concern**: - **code-quality** `scripts/test-launch-review.sh:2886-2980` — new harness cases always set `LARCH_CURSOR_LAUNCH_JITTER_MS=0`, so they would not catch the unset-default jitter regression above; a small case with the variable unset and a mocked `sleep` counter would lock the default.
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

### FINDING_34: [OUT_OF_SCOPE] correctness
- **Reviewer**: dyn-retry-state-output.txt
- **Concern**: - **correctness** `scripts/launch-review.sh:1015-1064` — The outer loop is bounded by `AUTH_ATTEMPT <= MAX_AUTH_RETRIES` while transient/empty `continue`s do not advance `AUTH_ATTEMPT`; after `TRANSIENT_ATTEMPT` reaches 3, further auth-classified failures can still invoke cursor up to `MAX_AUTH_RETRIES` times without transient/empty retries (pre-existing auth-loop shape, amplified but not introduced by this branch).
- **Suggested revision**: Address the concern above.

