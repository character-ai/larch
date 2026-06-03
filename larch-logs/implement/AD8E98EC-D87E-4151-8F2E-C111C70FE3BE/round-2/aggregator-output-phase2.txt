Normalized aggregator output from the supplied reviewer slots. Merged items that describe the same behavioral risk; kept separate items that need different fixes or hit different code paths.

### FINDING_1: Separate empty-result vs exit-code retry budgets (docs, plan, burst load)
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Documentation (`docs/configuration-and-permissions.md`, `scripts/launch-review.md`) states empty-result retries share the exit-code transient budget (`MAX_TRANSIENT_RETRIES` / `TRANSIENT_ATTEMPT`), but `scripts/launch-review.sh` uses a separate `EMPTY_RESULT_ATTEMPT` counter. Per slot, mixed failures (e.g. exit-8 transients then empty envelopes) can exceed the binding plan’s cap of three total backend calls (harness `SL-cursor-transient8-then-empty` expects four; worst-case independent budgets can reach ~6 per auth pass). Operators and reviewers may underestimate parallel burst load, wall time, and rate-limit pressure during backend degradation (e.g. multi-slot plan-review bursts).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_2: Empty-result retry does not check quota on JSON envelope
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: Before empty-result `continue`, quota/rate-limit detection runs on stderr sidecar and pre-existing `.diag`, not on the raw `OUTPUT` JSON being jq-probed. Cursor can return exit 0 with empty `.result` and rate-limit signals only in envelope error fields (empty stderr), so the launcher may still run up to three empty-result retries and amplify quota exhaustion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add envelope-based quota detection before the empty-result continue (jq on error/type/subtype or classify extracted error text).
  - From cursor-specialist-security-output.txt: Also gate on external_is_quota_failure cursor OUTPUT during the loop and/or mirror JSON quota into SIDECAR like Codex events; add JSON-only quota harness case

### FINDING_3: Case B2 does not pin stub invocation count
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-launch-review.sh` case B2 still passes marker assertions after empty-result retry default-on but does not assert stub invocation count. Regressions that change retry behavior (extra retries, disabled retry, single attempt) can pass while altering runtime cost and burst behavior, weakening regression signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Set LARCH_CURSOR_RETRY_EMPTY_RESULT=0 on B2 or assert invocation count like SL-cursor-empty-retry-exhausted.
  - From cursor-specialist-testing-output.txt: Assert exactly 3 stub calls with retry on, or set LARCH_CURSOR_RETRY_EMPTY_RESULT=0 for a single-shot marker test.
  - From cursor-specialist-edge-cases-output.txt: Assert invocation count (3 with retry on, 1 with LARCH_CURSOR_RETRY_EMPTY_RESULT=0).

### FINDING_4: Large inline empty-result diagnostic block in `_launch_cursor`
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: A large inline diagnostic block in `_launch_cursor` (approx. lines 1170–1217) hurts readability; future envelope fields risk copy-paste drift from collector KV grammar.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extract _cursor_write_empty_result_diag helper beside _cursor_transient_backoff.

### FINDING_5: Whitespace-only `.result` not treated as empty
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: The empty `.result` jq probe does not treat whitespace-only `.result` as empty. Backend may return `result:" "` with exit 0: no retry, no `CURSOR_EMPTY_RESPONSE`, possible silent collector drop.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Tighten jq probe or document whitespace-only as out of scope if never seen.

### FINDING_6: Non-string `.result` not treated as empty
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: The jq empty probe does not treat non-string `.result` (e.g. `{}`) as empty. Cursor may return `{"result":{}}`: no retry, no `CURSOR_EMPTY_RESPONSE`; `OUTPUT` may become `"{}"` and pass collectors incorrectly. Applies to in-loop probe and post-loop promotion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Treat non-string .result as empty in both the in-loop probe and post-loop promotion; add a harness fixture.

### FINDING_7: Harness sibling `scripts/test-launch-review.md` not updated
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Harness sibling markdown was not updated for new cursor empty-result retry, diag, jitter, and SL test cases. Future harness edits via script-md-siblings onboarding may miss required assertions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add Coverage bullets for SL-cursor-empty-* cases, .diag/json sidecars, and env knobs.

### FINDING_8: No harness for malformed JSON or missing `jq`
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: No harness covers plan edge cases where malformed JSON or absent `jq` skips empty-result retry; production falls back to legacy no-retry behavior and a jq-guard regression would not be caught by current SL cases.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add one stub case each for invalid JSON and jq-absent PATH with invocation-count assertions.

### FINDING_9: CI shard 2 load from new multi-invocation cases
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Many new multi-invocation cases were added to an already heavy `test-launch-review` shard (`Makefile:test-harnesses-2`). CI may slow or flake under load without functional failures in the new logic.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Monitor harness duration; split or gate the slowest SL cases if the shard regresses.

### FINDING_10: `.diag` writer lacks newline/delimiter sanitization; untrusted envelope text reaches failure logs
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-diag-format-safety-output.txt
- **Severity**: important
- **Concern**: `${OUTPUT}.diag` interpolates jq-extracted envelope fields via bare `printf '%s'` without newline or delimiter sanitization; `jq -r` can preserve embedded newlines and break the intended two-line `TOOL=` / `FAILURE_REASON=` sidecar shape. Rich vendor error content (tokens, PII, prompt echoes beyond `redact-secrets` coverage) can flow into committed round artifacts and execution-issues via `compose-collector-failure-log.sh` (`.diag` cat without the stderr redaction path) and `append-tool-failure.sh --redact`, diverging from patterns that use `head -1 … | tr '\n' ' '`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Whitelist error.message/code only cap length skip object fallback consider redacting OUTPUT.json at launcher before retention
  - From dyn-diag-format-safety-output.txt: Before interpolation, normalize every extracted field the same way as model-args failures (`tr '\n\r|'` to spaces, collapse runs, cap length), or emit envelope diagnostics as a single JSON line / base64 blob instead of inline `printf` fragments; add a harness case with a stub envelope whose `.error` contains embedded newlines and `usage limit` / `TOOL=fake` substrings and assert `.diag` stays two lines and `compose-collector-failure-log` output survives `--redact`.

### FINDING_11: Full `${OUTPUT}.json` envelope retained without redaction; `.diag` points at raw file
- **Reviewer(s)**: dyn-diag-format-safety-output.txt
- **Severity**: important
- **Concern**: The branch retains the full Cursor JSON envelope at `${OUTPUT}.json` while only `${OUTPUT}.diag` passes through `redact-tmpdir-paths.sh` and `redact-secrets.sh`. Envelope `.error` fields are not fully covered by redactor pattern families; operator-visible `.diag` text references `(full envelope: ${OUTPUT}.json)`, increasing exposure of backend error text in tmpdirs and failure logs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-diag-format-safety-output.txt: Run the same redaction pipeline on `${OUTPUT}.json` (or a redacted copy used for diagnostics), omit the pointer to the raw envelope from operator-visible `.diag` text, or restrict full-envelope retention to a test-only / opt-in env flag.

### FINDING_12: `LARCH_CURSOR_RETRY_EMPTY_RESULT` only disables on literal `0`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `LARCH_CURSOR_RETRY_EMPTY_RESULT` only treats literal `0` as disable; values like `false` still enable empty-envelope retries, contrary to typical operator intent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Document literal-0 semantics or normalize falsy values to disabled.

### FINDING_13: `LARCH_CURSOR_RETRY_EMPTY_RESULT` re-read each auth-loop iteration
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: The retry-disable env gate is re-read on each auth-loop iteration though the plan specified env gates are read once—minor contract drift unless env changes mid-loop.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Hoist the retry-disable flag to a variable set once before the while loop.

### OOS_1: [OUT_OF_SCOPE] Collector ignores rich `.diag` for `CURSOR_EMPTY_RESPONSE`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-diag-format-safety-output.txt
- **Severity**: latent
- **Concern**: `scripts/collect-agent-results.sh` overwrites or hardcodes generic `FAILURE_REASON` for `CURSOR_EMPTY_RESPONSE` and does not consume the new launcher `.diag`; panel summaries and execution-issues show degraded-backend text until collector work (e.g. #3392). Primary consumer of enriched diagnostics today is failure-log composition, not the collector RESULTS row.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Have build_failure_reason prefer .diag for CURSOR_EMPTY_RESPONSE (likely in #3392).
  - From cursor-specialist-edge-cases-output.txt: Call build_failure_reason when .diag exists or document sidecar-only visibility until collector work lands.

### OOS_2: [OUT_OF_SCOPE] `compose-collector-failure-log.sh` cats `.diag` without secret redaction
- **Reviewer(s)**: dyn-diag-format-safety-output.txt
- **Severity**: latent
- **Concern**: Pre-existing: `.diag` sections are `cat` without `render_failed_agent_stderr_tail` / secret redaction; this branch amplifies how much untrusted content can land there, but the missing redaction path predates #3393.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_3: [OUT_OF_SCOPE] `${OUTPUT}.diag.$$` temp naming — no practical collision
- **Reviewer(s)**: dyn-diag-format-safety-output.txt
- **Severity**: nit
- **Concern**: Distinct `OUTPUT` paths per slot and per-process `$$` make `${OUTPUT}.diag.$$` temp naming a non-issue in parallel burst; cleanup removes temp files. No change required for safety on that basis alone.
- **Suggested revisions (informational for voters; coder decides)**:
