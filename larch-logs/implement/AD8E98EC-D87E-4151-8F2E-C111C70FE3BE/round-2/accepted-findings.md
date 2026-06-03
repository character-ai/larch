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


### FINDING_7: Harness sibling `scripts/test-launch-review.md` not updated
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Harness sibling markdown was not updated for new cursor empty-result retry, diag, jitter, and SL test cases. Future harness edits via script-md-siblings onboarding may miss required assertions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add Coverage bullets for SL-cursor-empty-* cases, .diag/json sidecars, and env knobs.


