Normalizing the supplied reviewer inputs into one structured finding list: merging duplicate risks, dropping commit-title noise and positive “no defect” notes, and keeping OOS items tagged.
# Orchestrator Aggregator — normalized findings

Commit-subject entries (`170d8b6b5`, `cd318f2d7`, `cbc96741e`, `d69fddbc7`) are omitted: they are history titles, not behavioral risks. The positive “no defect in backoff wiring” note (`dyn-retry-budget-integrity` FINDING_33) is omitted (nothing to vote on).

---

### FINDING_1: Separate empty-result retry budget allows up to six cursor calls per auth pass
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, cursor-specialist-structure-output.txt, dyn-retry-budget-integrity-output.txt
- **Severity**: important
- **Concern**: Empty-result retries use `EMPTY_RESULT_ATTEMPT` bounded independently of `TRANSIENT_ATTEMPT` (both gated by `MAX_TRANSIENT_RETRIES=2`), diverging from the binding plan to reuse `TRANSIENT_ATTEMPT` and cap total cursor backend calls at three per slot per auth pass. Under mixed exit-code transients and exit-0 empty `.result`, a slot can issue up to six sequential `cursor agent` invocations (three exit-code + three empty-result), amplifying backend and rate-limit pressure during outages—especially across parallel panels (~8 slots).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Reuse TRANSIENT_ATTEMPT for empty-result retries, or update plan/acceptance to document separate budgets explicitly.
  - From cursor-specialist-testing-output.txt: Align counters with the plan (single shared budget) or document and accept the six-call ceiling explicitly in acceptance/docs.
  - From cursor-specialist-edge-cases-output.txt: Unify retry counting under one MAX_CURSOR_BACKEND_ATTEMPTS or cap total backend calls at three across both branches.
  - From cursor-specialist-plan-fidelity-output.txt: Reuse TRANSIENT_ATTEMPT for empty-result retries per the binding plan, or update the plan/acceptance criteria and keep docs aligned if separate budgets are intentional.
  - From cursor-specialist-structure-output.txt: No code change required if intentional; ensure issue/PR description calls out the deliberate plan deviation so future readers do not “simplify” back to a shared counter and break the mixed-retry tests.
  - From dyn-retry-budget-integrity-output.txt: Drop `EMPTY_RESULT_ATTEMPT` and drive empty-result retries through the existing `TRANSIENT_ATTEMPT` counter (increment before `continue` in either branch, single `_cursor_transient_backoff` using that counter), so the combined transient budget stays at `MAX_TRANSIENT_RETRIES + 1 = 3` total calls; update `SL-cursor-transient8-then-empty` and the docs in `scripts/launch-review.md` / `docs/configuration-and-permissions.md` to match the shared-budget semantics.

---

### FINDING_2: Operator docs understate separate-counter worst-case load
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Env-var documentation describes retry limits as sharing `MAX_TRANSIENT_RETRIES=2` with exit-code transients but does not clearly state that empty-result retries use a separate `EMPTY_RESULT_ATTEMPT` counter, so operators tuning parallel panels may not expect up to six backend calls per auth pass under mixed failure modes (as spelled out in `scripts/launch-review.md`).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add one sentence under `LARCH_CURSOR_RETRY_EMPTY_RESULT` mirroring `launch-review.md` (separate counter, worst-case 3+3 calls per auth pass) so operators tuning parallel panels are not surprised by load.

---

### FINDING_3: Codex and Cursor transient backoff logic can drift
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `_cursor_transient_backoff` was extracted for the cursor path, but `_launch_codex` still inlines equivalent delay logic, so retry timing can diverge on future edits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Hoist a single file-level helper (e.g. `_review_transient_backoff`) used by both `_launch_codex` and `_launch_cursor`, or document in `launch-review.md` that codex must be updated in lockstep.

---

### FINDING_4: No JSON-envelope quota classification before empty-result retry
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Empty-result retry guards rely on grep substrings in sidecar/diag/stdout; exit 0 with empty `.result` and rate-limit metadata only in JSON envelope fields that do not match patterns can still consume empty-result retries (up to three per slot), re-sending full reviewer prompts and worsening outage load. Codex mirrors quota from JSON events; cursor has no equivalent before empty-result retry.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Mirror quota from envelope to sidecar or classify rate-limit type/subtype as non-retryable before empty-result retry.
  - From cursor-specialist-security-output.txt: Classify JSON envelope quota/rate-limit fields as non-retryable; cap total cursor invocations per slot across retry types.
  - From cursor-specialist-edge-cases-output.txt: Extend guard with jq-based envelope quota classification or mirror quota markers into the sidecar before retry.

---

### FINDING_5: Terminal `.diag` omits planned pointer to full envelope file
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `${OUTPUT}.diag` `FAILURE_REASON` does not include the planned in-diag reference to `${OUTPUT}.json`; operators must discover the full envelope artifact separately.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add a redacted `(full envelope: ${OUTPUT}.json)` suffix to FAILURE_REASON.
  - From cursor-specialist-plan-fidelity-output.txt: Append a redacted envelope path or stable artifact reference to FAILURE_REASON while keeping field sanitization.

---

### FINDING_6: Whitespace-only `.result` not treated as empty for retry
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Backend returning whitespace-only `.result` (e.g. `" "`) does not trigger empty-result retry; the slot may still fail later at the first-line content gate as empty-looking output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Trim or treat whitespace-only `.result` like empty for retry/diagnostic if observed in the wild.

---

### FINDING_7: Case B2 does not guard empty-result retry or diagnostic regressions
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `scripts/test-launch-review.sh` case B2 does not assert `.diag` content or stub invocation count. Removing `LARCH_CURSOR_RETRY_EMPTY_RESULT=0` from B2 could still pass marker assertions while invoking the stub three times and missing `.diag` regressions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add .diag grep and stub count==1 assertions to case B2, matching SL-cursor-empty-retry-disabled.
  - From cursor-specialist-edge-cases-output.txt: Set LARCH_CURSOR_RETRY_EMPTY_RESULT=0 for B2 or assert exactly one stub invocation.

---

### FINDING_8: No harness for jq-missing or malformed JSON on empty-result path
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: No CI case covers jq absent or corrupt envelope on the empty-result branch; production could regress to undocumented behavior without signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add minimal stubs or PATH/jq-off cases asserting no empty-result retry and expected output promotion.

---

### FINDING_9: Launch jitter env var not behaviorally tested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `LARCH_CURSOR_LAUNCH_JITTER_MS` is documented but harness runs use `JITTER_MS=0`; sleep/ms parsing regressions could ship unnoticed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add a small timing/counting case or state in test-launch-review.md that jitter is intentionally production-only.

---

### FINDING_10: Default launch jitter adds happy-path latency without CI coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Default 250ms pre-loop jitter adds up to 250ms wall-clock per cursor slot on the happy path; large parallel panels pay cumulative delay with no harness coverage of the delay path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Document CI/autonomous opt-out (JITTER_MS=0) or add a harness timing assertion if jitter must stay default-on.

---

### FINDING_11: New SL-cursor-* cases not listed in harness sibling doc
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-launch-review.md` Coverage section does not name new mixed/quota cursor cases; contributors may miss them when extending the launcher.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: List all new SL-cursor-* case IDs explicitly in the Coverage section.

---

### FINDING_12: Committed larch-logs may retain sensitive envelope fields
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: New empty-result diagnostics and `*-output.txt.json` sidecars copy full Cursor JSON envelopes minus top-level `.result`; sensitive text in `.error` or other keys may ship in merged PRs after best-effort `redact-secrets` only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Redact or allowlist envelope fields before cp to .json; avoid (.error | tostring) dumps in .diag without nested redaction.

---

### FINDING_13: Diagnostic write fail-opens to unredacted copy when redaction fails
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: When `redact-secrets.sh` fails, the launcher may still `cp` raw `_diag_tmp` into `.diag`, leaving API/error prose in artifacts consumed by failure logs and execution-issue composers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Omit .diag or write a fixed placeholder when redaction fails; do not cp raw _diag_tmp.

---

### FINDING_14: Retry backoff does not stagger empty-result or exit-code retries
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: One-time pre-loop jitter does not desynchronize retries; after aligned initial failures, parallel slots can re-hit Cursor on similar `1<<attempt` backoff and re-synchronize bursts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Add per-retry random delay (or slot-derived offset) inside each continue path, not only before the loop.

---

### FINDING_15: Empty-result diagnostic block inline in `_launch_cursor`
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: ~50 lines of sanitize/jq/redact logic inline in `_launch_cursor` reduce readability of the auth loop.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Optional local helper `_cursor_write_empty_result_diag` to keep the auth loop readable; only worth doing if this file grows again.

---

### OOS_1: [OUT_OF_SCOPE] Exit-code transient branch lacks stdout quota grep present on empty-result path
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Exit-code transient guard does not grep `$OUTPUT` for quota; empty-result guard does. Quota-only-on-stdout with exit 8 may burn exit-code retries (pre-existing asymmetry).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add external_is_quota_failure on $OUTPUT to the exit-code transient branch.

---

### OOS_2: [OUT_OF_SCOPE] Collector overwrites rich `.diag` for `CURSOR_EMPTY_RESPONSE`
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `scripts/collect-agent-results.sh` overwrites rich `.diag` with generic `FAILURE_REASON` for `CURSOR_EMPTY_RESPONSE` (pre-existing); operators may not see new envelope diagnostics in pipe-delimited `RESULTS` even when `.diag` is populated.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Align collector with .diag KV grammar when #3392 lands (not introduced by this diff).

---

### OOS_3: [OUT_OF_SCOPE] No panel-level cursor launch concurrency cap
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Parallel dispatch can still launch eight cursor slots with no global in-flight limit; jitter/retry logic is per-process only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Consider a future global cursor concurrency cap in the dispatcher (separate change).

---

### OOS_4: [OUT_OF_SCOPE] Doc “six total” worst-case call count slightly overstated
- **Reviewer(s)**: dyn-retry-budget-integrity-output.txt
- **Severity**: latent
- **Concern**: `scripts/launch-review.md` and related docs claim worst case “six total” backend calls (3 exit-code + 3 empty-result); in one auth-loop pass the achievable maximum is five (two exit-code retries then three empty-result attempts) because a third consecutive exit-8 breaks out without entering the empty-result branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-retry-budget-integrity-output.txt: (Concern documents arithmetic only; no explicit fix bullet in source.)

---

### OOS_5: [OUT_OF_SCOPE] chore(larch-logs) flush
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Commit `cd318f2d7` — chore(larch-logs) flush is out of scope per review instructions.
- **Suggested revisions (informational for voters; coder decides)**:
  - (No fix direction in source beyond out-of-scope note.)
