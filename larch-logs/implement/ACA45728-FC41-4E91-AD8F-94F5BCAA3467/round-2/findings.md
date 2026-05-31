Normalized aggregator output from the supplied reviewer slots (first-seen order, merges applied per your rules).

### FINDING_1: lint-fix-loop: unconditional codex stderr-tail rewrite
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `run_codex` unconditionally rewrites stderr-tail after `run-external-agent` already wrote it via `--stderr-sink`. A failed codex lint-fix run can double-invoke `write_failed_agent_stderr_tail` from the same wrapper log; usually harmless but can mask divergent source selection if `run-external-agent` and the explicit write ever disagree.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Only backfill when `${run_dir}/codex.log.stderr-tail` is missing, or drop the explicit write and rely on `--stderr-sink`.

### FINDING_2: ship-pr vs Step 5: duplicated stderr-tail stem parsing
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `_surface_lint_fix_stderr_tail` duplicates `step5_surface_lint_stderr_tail` stem parsing. Future edits to fallback order could update ship-pr but not Step 5 (or vice versa), surfacing tails in one lane only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extract a shared parse-and-surface helper used by both callers.

### FINDING_3: ship-pr recovery waterfall: split failure continue blocks
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Recovery waterfall uses two separate failure `continue` blocks after one surfacing call. Readers must reason about `tier_rc` vs `launcher_exit` separately even though both paths surface then revert.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Combine failure conditions into one block that surfaces, reverts, and continues.

### FINDING_4: recovery waterfall: launcher stdout capture files accumulate
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Per-tier `recovery-*-launcher-$$.out` (and related launcher stdout capture files) are never removed. Long `/implement` runs accumulate launcher captures under `IMPLEMENT_TMPDIR` until session cleanup.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: `rm -f` after parsing or reuse one capture path per waterfall.
  - From cursor-specialist-edge-cases-output.txt: `rm -f` after awk parse or reuse one `mktemp` per waterfall invocation.

### FINDING_5: Step 5: stderr-tail surfacing on lint-fix attempt-cap after applied
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `step5_surface_lint_stderr_tail` on lint-fix-attempt-cap after `applied` status may attempt emit using `CODER_LOG_FILE` from a successful applied capture when no failure tail exists.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Skip surfacing on attempt-cap or gate on terminal failure statuses only.

### FINDING_6: plan-review-loop: `collect` subshell `|| true` swallows collector failure
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Collector invocation uses `|| true`, so non-zero collect exit no longer aborts the loop under `set -e`. When `collect-agent-results.sh` exits non-zero (including exit 1 with empty stdout for bad args/paths), the loop continues, parses no or partial records, and may take a degraded/zero-findings path instead of failing closed—exceeding Decision 7’s authorized minimal tee-only change and altering panel-failed handling beyond stderr surfacing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Restrict `|| true` to cases that need stderr teed without abort; fail closed when collect rc != 0 and `_collect_out` is empty/unparseable.
  - From cursor-specialist-plan-fidelity-output.txt: Remove `|| true` if the FD-2 harness passes without it; if `set -e` must be satisfied, capture collector rc without swallowing failure semantics, and add a harness assertion for the expected loop status on collector failure.

### FINDING_7: implement Step 3/6: orchestrator does not surface lint-fix stderr tails
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Step 3/6 orchestrator lint-fix invocations do not parse `STDERR_TAIL_PATH` or emit tails to chat. Codex lint-fix can fail at Step 3 with tail file and KV emitted, but orchestrator never surfaces it—only ship-pr RCC and Step 5 loop consumers do.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Extend Step 3/6 SKILL/bash surfacing, or narrow acceptance to implemented consumers (step2, ship-pr, step5).

### FINDING_8: test gap: first-fixer-non-health early return without stderr-tail assertion
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: No test for stderr-tail surfacing on first-fixer-non-health early return despite plan choke-point requirement. `run_ci_fix_vendor` can return 1 with `BAIL_REASON=first-fixer-non-health` while a tier stderr-tail exists; without a test, a refactor could move or drop `_surface_ci_stderr_tail` before that return and regress Step 8+ chat diagnostics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add or extend a #3134-style case: stub first tier non-health failure, seed `${tier_out}.stderr-tail`, assert probe on caller stderr before first-fixer bail.

### FINDING_9: test gap: codex implementer agent-failure lacks redacted bounded tail assertions
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Agent-failure test does not assert redacted bounded tail per plan testing strategy. A multi-kilobyte or secret-bearing stderr sidecar could slip through without line/byte/redaction checks; only content presence is verified (harness could pass with unbounded or unredacted `${TRANSCRIPT}.stderr-tail`).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Reuse test-lib-failed-agent-stderr-tail patterns: cap lines via `LARCH_FAILED_AGENT_STDERR_TAIL_LINES` and assert fence plus size bounds on `${TRANSCRIPT}.stderr-tail`.
  - From cursor-specialist-plan-fidelity-output.txt: Assert tail line/byte caps (and optionally redaction) using existing lib harness patterns or seeded sensitive content in `$SIDECAR_LOG`.

### FINDING_10: test gap: ship-pr `_surface_lint_fix_stderr_tail` CODER_LOG_FILE fallback
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `CODER_LOG_FILE` fallback in `_surface_lint_fix_stderr_tail` is untested. Older lint-fix-loop output without `STDERR_TAIL_PATH` would not surface tails to chat if fallback parsing regressed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Stub lint-fix stdout with only `CODER_LOG_FILE=` and seeded `${stem}.stderr-tail`; assert caller stderr via `run_lint_fix_loop_capture`.

### FINDING_11: test gap: Step 5 `step5_surface_lint_stderr_tail` CODER_LOG_FILE fallback
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `step5_surface_lint_stderr_tail` `CODER_LOG_FILE` fallback untested. Step 5 terminal arms could lose backward-compatible surfacing when only `CODER_LOG_FILE` is present in capture file.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add parsers case with `CODER_LOG_FILE` only and assert `step5_surface_lint_stderr_tail` emits seeded tail.

### FINDING_12: test gap: `run_lint_fix_loop_capture` empty-with-failure `LINT_FIX_STATUS` trigger
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `run_lint_fix_loop_capture` omits plan empty-with-failure `LINT_FIX_STATUS` trigger. Malformed capture with rc=0 and empty status might skip `_surface_lint_fix_stderr_tail` while a tail file exists.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Align implementation with plan or prove unreachable; add harness if real.

### FINDING_13: test gap: recovery waterfall surfacing when only `${output}.stderr-tail` exists
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Recovery waterfall test does not isolate surfacing when only `${output}.stderr-tail` exists. CI launcher exit 0 with `LAUNCHER_EXIT=0` but non-empty tail could fail to surface if gating regresses to `launcher_exit` only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Stub launcher exit 0 with `LAUNCHER_EXIT=0` and non-empty `${output}.stderr-tail`; assert caller stderr probe.

### FINDING_14: test gap: wrapper_rc=2 CI validation stderr-tail surfacing
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `wrapper_rc=2` CI validation surfacing path has no dedicated test. Validation failures might stop emitting tier stderr-tail to chat after future edits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Stub launcher exit 2 with seeded `${tier_out}.stderr-tail`; assert caller stderr before rollback.

### FINDING_15: [OUT_OF_SCOPE] cleanup harness expansion bundled with #3227
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Branch bundles #3229 cleanup harness expansion unrelated to #3227. Full `make lint` runs more cases; failures may be misattributed to stderr-tail work.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Split commits or document dual test-plan in PR description.

### FINDING_16: [OUT_OF_SCOPE] plan-review-loop collect `|| true` — monitor design panel-failed regressions
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Collect subshell now uses `|| true` beyond new FD-2 tail test scope. Collector non-zero might alter downstream panel-failed handling vs pre-change behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Monitor design panel-failed regressions; extend harness if semantics shift.

### FINDING_17: [OUT_OF_SCOPE] design collector stderr lacks implement-lane tail redaction pipeline
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Collector stderr is still teed live to FD 2/4 without the file-based tail pipeline; only `collect-agent-results.sh` §3.8 blocks go through `render_failed_agent_stderr_tail` / `larch_err`. The new harness case and the `|| true` on the collect subshell document/preserve that behavior rather than introducing implement-lane redaction here.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: If design chat must match implement-lane guarantees, pipe teed collector stderr through the same redactors or emit only §3.8 tails (out of #3227 scope).

### FINDING_18: [OUT_OF_SCOPE] redact-secrets residual exposure in capped tails
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `redact-secrets.sh` remains a pattern backstop; internal URLs, hostnames, and PII can still reach operator chat within capped tails. This branch widens where tails surface, not the redactor’s limits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Treat as accepted residual; keep `LARCH_FAILED_AGENT_STDERR_TAIL_LINES=0` documented for sensitive runs.

### FINDING_19: [OUT_OF_SCOPE] Cursor failure tails may source from `.diag` (stdout buffer)
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `scripts/run-external-agent.sh` + cursor `--capture-stdout-only` / `--capture-stdout` (pre-existing; amplified by new consumers) — Cursor failure tails may be sourced from `.diag` (stdout buffer), so chat content can be richer than stderr-only semantics despite the “stderr tail” naming.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Already bounded/redacted; no change required unless product wants stderr-only sourcing for cursor lanes globally.

### FINDING_20: lint-fix-loop: `STDERR_TAIL_PATH` last-wins hides earlier agent tail
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `STDERR_TAIL_PATH` keeps only the last failed stem. Codex dispatch fails (`codex.log.stderr-tail` written) then Cursor preflight fails; chat surfaces Cursor preflight via `STDERR_TAIL_PATH` while the Codex agent tail stays on disk only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Prefer first non-empty agent tail for KV/chat, or document and test last-wins if intentional.

### FINDING_21: ship-pr recovery waterfall: surfaces stderr tail on every failed tier
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Recovery waterfall surfaces stderr tail on every failed tier before `continue`. Cursor CI fix fails (tail emitted) then Codex tier runs; operator sees multiple tails for reverted work.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Surface only on terminal waterfall failure or summarize prior-tier tails.

### FINDING_22: ship-pr recovery waterfall: orphan `${output}.stderr-tail` with `launcher_exit=0`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Tier failure treats orphan `${output}.stderr-tail` as failure when `launcher_exit=0`. Stale tail file with `LAUNCHER_EXIT=0` could skip a tier that actually succeeded.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Require `launcher_exit!=0` (or parsed failure class) before honoring `-s ${output}.stderr-tail` alone.

### FINDING_23: Step 5: whitespace word-splitting truncates path-valued KV tails
- **Reviewer(s)**: dyn-kv-parse-robustness-output.txt
- **Severity**: important
- **Concern**: `step5_parse_kv_tokens` splits capture lines with `for tok in $line`, truncating `STDERR_TAIL_PATH` / `CODER_LOG_FILE` values at the first space. Step 5 can miss valid `${stem}.stderr-tail` files that `run_lint_fix_loop_capture` / ship-pr (`substr` after `=`) would surface for the same stdout block. `emit_kv` allows spaces in values (`scripts/lib-quiet.sh:166-178`).
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-kv-parse-robustness-output.txt: Parse path-valued keys from the full line, not whitespace tokens — e.g. `case "$line" in STDERR_TAIL_PATH=*) stem="${line#STDERR_TAIL_PATH=}" ;; esac`, or the same `awk '$1 == key { print substr($0, index($0,"=")+1); exit }'` pattern used by `scripts/ship-pr.sh:570-572` / `scripts/test-lint-fix-loop.sh:25-27`. Add a harness case with a space (and optionally `=`) in `STDERR_TAIL_PATH`.

### FINDING_24: [OUT_OF_SCOPE] `LAUNCHER_EXIT` / `LINT_FIX_STATUS` `$2` extractions safe for numeric/token contract
- **Reviewer(s)**: dyn-kv-parse-robustness-output.txt
- **Severity**: nit
- **Concern**: `LAUNCHER_EXIT` / `LINT_FIX_STATUS` `$2` extractions (`scripts/ship-pr.sh:151,2084,2773`) are safe for this contract — numeric exit codes or fixed tokens with no embedded `=`. Recovery waterfall parses from launcher-only stdout, cleaner than merged `2>&1` CI fix-loop capture.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_25: [OUT_OF_SCOPE] `_surface_lint_fix_stderr_tail` vs `kv_value` duplication (maintainability only)
- **Reviewer(s)**: dyn-kv-parse-robustness-output.txt
- **Severity**: nit
- **Concern**: Path keys use the correct `substr` strategy; duplication between `_surface_lint_fix_stderr_tail` and `kv_value` is maintainability-only, not a parse bug.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_26: [OUT_OF_SCOPE] `step5_parse_kv_tokens` whitespace weakness for `REDACTED_LOG_FILE` pre-dates branch
- **Reviewer(s)**: dyn-kv-parse-robustness-output.txt
- **Severity**: latent
- **Concern**: `step5_parse_kv_tokens` whitespace weakness for `REDACTED_LOG_FILE` pre-dates this branch; the diff amplifies the same pattern onto tail-surfacing keys but did not introduce the helper itself.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_27: [OUT_OF_SCOPE] test gap: Step 5 parser tests use space-free stems only
- **Reviewer(s)**: dyn-kv-parse-robustness-output.txt
- **Severity**: latent
- **Concern**: New parser tests in `skills/review-and-fix/scripts/test-review-and-fix.sh:2355-2376` use space-free stems; they would not catch Step 5 whitespace truncation. `scripts/test-lint-fix-loop.sh` uses `kv_value` (substr) for assertions, so producer/KV tests do not exercise the Step 5 consumer parser.
- **Suggested revisions (informational for voters; coder decides)**:

---

**Merge notes (brief):** FINDING_4+22 (launcher capture cleanup), FINDING_6+24 (plan-review `|| true`), FINDING_9+25 (codex implementer bounded/redacted tail tests). FINDING_16 kept separate from FINDING_6 despite shared line 762 because the source explicitly tags it `[OUT_OF_SCOPE]` with monitor-only framing. FINDING_2 kept separate from FINDING_25 `[OUT_OF_SCOPE]` duplication note. No `LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED` — 27 finding blocks emitted.
