### FINDING_1: Extract §3.8 collector stderr logic into shared lib
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: Section 3.8 adds nested helpers and KV parsing inside a 1500+ line collector instead of the shared stderr lib. Harder to unit-test dedup/resolve logic and increases merge/conflict risk on the hottest collector script.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extract batch emit/dedup into lib-failed-agent-stderr-tail.sh; leave one call site after section 3.7.

### FINDING_2: Aggressive stderr signature normalization collapses distinct failures
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Global/heuristic digit normalization in `failed_agent_stderr_signature` can equate distinct failures (e.g., different exit codes, HTTP 401 vs 403, or identical error templates across slots). Collector dedup then suppresses subsequent tails, hiding root-cause diversity on FD 2.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Tighten normalization rules or document and test acceptable collision rate.
  - From cursor-specialist-correctness-output.txt: Narrow digit normalization or add stable error-class tokens to signature input.
  - From cursor-specialist-edge-cases-output.txt: Tighten normalization or skip dedup when failures differ after minimal normalization; keep first full tail always.

### FINDING_3: Waterfall overwrites single launch-stderr path per output slot
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Single launch-stderr path per output is overwritten each waterfall phase. Phase-1 launcher validation stderr is lost if phase-3 runs on the same slot path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Use per-phase launch-stderr filenames or append with phase labels; extend collector resolution.

### FINDING_4: Inconsistent stderr-tail fence formats across call sites
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Two different stderr tail fence formats for the same feature (`run-external-agent.sh` vs collector). Transcript consumers cannot rely on one delimiter pattern.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Unify formatting via one lib helper used by run-external-agent and the collector.

### FINDING_5: Full stderr replay duplicates bounded stderr-tail on failure
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Full stderr replay plus bounded stderr-tail duplicates content on failure. Chat noise and token burn on validation failures already captured in the sidecar.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Make full replay opt-in or skip when write_failed_agent_stderr_tail succeeds.

### FINDING_6: Collector resolution ignores earlier waterfall-phase stderr sidecars
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Collector tail resolution only inspects paths derived from the final `REVIEWER_FILE`. Waterfall writes phase-specific outputs and sidecars (e.g., phase-2 codex stderr on `slot-phase2.txt.stderr-tail` while phase-3 Claude fails on `slot-phase3.txt`); final collect emits the phase-3 tail only and hides earlier root causes. Plan-review panels with mass codex phase-1 failures can leave tails on base paths while collect uses phase-3 paths only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Walk phase suffixes (phase2/phase1/base) for first non-empty .stderr-tail or .launch-stderr, or copy last phase tail to final output before collect.
  - From cursor-specialist-edge-cases-output.txt: Add phase fallback in `_resolve_collector_stderr_tail_file` (or ledger-driven lookup) for base / -phase2 / -phase3 paths and matching .stderr-tail and .launch-stderr files.

### FINDING_7: Empty signature skips stderr-tail chat emission
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: When signature computation returns empty, §3.8 skips all tail emission. Operators get `FAILURE_REASON` only with no fenced stderr block despite a valid `.stderr-tail` artifact (e.g., rare sed/cksum failure).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Emit tail when signature empty; treat as unique occurrence.
  - From cursor-specialist-edge-cases-output.txt: Emit tail without dedup when signature computation fails.

### FINDING_8: compose-collector-failure-log omits launch-stderr sidecars
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: `compose-collector-failure-log` omits launch-stderr sidecars. Launcher validation failure surfaced via launch-stderr on-demand render is absent from committed failure logs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add launch-stderr section or persist launcher failures to .stderr-tail at write time.

### FINDING_9: Missing E2E test for collect-findings.sh stderr tee on failing externals
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Plan acceptance for FINDING_3 / wrapper FD-2 visibility is not E2E-tested: harness exercises `collect-agent-results.sh` directly, not `collect-findings.sh` with tee. A tee/FD-4 regression or broken quiet FD routing could ship; `/review` operators would see no stderr tails despite green collect.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Run collect-findings.sh with stub external files and assert fenced tails on wrapper stderr.
  - From cursor-specialist-plan-fidelity-output.txt: Run collect-findings.sh with failed external stubs; assert tail fences on wrapper stderr when collector_rc=0.

### FINDING_10: Collector stdout RESULTS byte-unchanged contract not enforced in tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-fd-stdout-isolation-output.txt
- **Severity**: important
- **Concern**: Dedup/distinct cases labeled “stdout unchanged contract” only check that `STATUS=FAILED` appears on stdout (or remain vacuous). §3.8 could inject/garble `KEY=value` lines or route tail body text to stdout via `emit`/`printf`; CI would still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Golden stdout diff for fixture batch; assert stderr tails only on FD 2.
  - From cursor-specialist-plan-fidelity-output.txt: Capture and diff collector stdout with vs without pre-seeded .stderr-tail files, or compare to a golden KV blob.
  - From dyn-fd-stdout-isolation-output.txt: Add explicit negative greps on the captured stdout file (e.g. `! grep -Fq 'fatal tool error' <<< "$DEDUP_STDOUT"` and `! grep -Fq 'agent stderr tail' <<< "$DEDUP_STDOUT"`) for dedup/distinct/launch-stderr cases, matching the plan acceptance line that stdout `KEY=value` bytes stay unchanged when `.stderr-tail` sidecars exist.

### FINDING_11: Missing launch-claude-review failure tests for .stderr-tail and stderr re-emit
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Plan testing strategy omits non-zero-rc `.stderr-tail` assertion and preserved full stderr re-emit for the launch-claude-review adapter. Parent fallback `write_failed_agent_stderr_tail` from `SUBPROCESS_STDERR` or the re-emit loop could break silently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add failing-stub cases asserting .stderr-tail and re-emitted lines on stderr.
  - From cursor-specialist-plan-fidelity-output.txt: Add stub failure case asserting ${OUTPUT}.stderr-tail exists alongside existing clamp tests.

### FINDING_12: Non-numeric LARCH_FAILED_AGENT_STDERR_TAIL_LINES fallback untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Non-numeric `LARCH_FAILED_AGENT_STDERR_TAIL_LINES` fallback to 30 is untested. Typo env could cause surprising behavior if fallback regresses.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Set env to abc; assert 30-line tail from 40-line fixture.

### FINDING_13: Default review sidecar-first failure path not integration-tested in run-external-agent
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Default review sidecar-first failure path not integration-tested. `run-external-agent` could prefer `.diag` over `.sidecar`; review lanes lose real agent stderr.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Failed run with populated .sidecar; assert .stderr-tail matches sidecar not diag.

### FINDING_14: NS-retry success stale .stderr-tail removal untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: NS-retry success stale `.stderr-tail` removal not tested (transient only). NS OK path might leave failure tail beside `STATUS=OK`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Seed .stderr-tail on NS-retry-success fixture; assert file removed and STATUS=OK.

### FINDING_15: No ordering assertion for stderr-tail before .done
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: No ordering assertion stderr-tail before .done. Race could theoretically surface .done before tail to collector.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Assert mtime ordering or document-only if deemed sufficient.

### FINDING_16: Unredacted full subprocess stderr re-emitted on launch-claude-review failure
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: Full subprocess stderr is re-emitted via `larch_err` without redaction whenever `SUBPROCESS_STDERR` is non-empty, before the new redacted `.stderr-tail` path. On Claude fallback/validation failure, chat and committed transcripts can contain raw API keys or paths from the full stderr file, defeating #3202's redaction goal despite a redacted sidecar.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Gate or remove the blanket re-emit; use redacted tail/sidecar emission for agent failures; redact SUBPROCESS_STDERR before any line-by-line larch_err if a full message is still required.

### FINDING_17: Unredacted tail -5 of OUTPUT_FILE on run-external-agent failure path
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: Failed-path diagnostics still print `tail -5` of `OUTPUT_FILE` to FD 2 without redaction in the same block that adds redacted `.stderr-tail`. With merged stdout capture, agent output lines containing secrets appear unredacted in the orchestrator transcript alongside the new redacted stderr tail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Remove unredacted tail -5 or run it through render_failed_agent_stderr_tail / the same redactor stack with a byte cap.

### FINDING_18: Collector emits .stderr-tail contents without read-time re-redaction
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Collector §3.8 emits `.stderr-tail` contents directly without re-redaction at read time. A stale or forged `.stderr-tail` in the session tmpdir would be surfaced verbatim to FD 2 and tee'd collector logs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Re-render or re-redact sidecar contents in `_emit_collector_stderr_tail_from_file` before larch_err.

### FINDING_19: Redactor failures swallowed; partial coverage on publish path
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Redactor failures are swallowed; partial redact-secrets coverage; stderr-tail may be published under gitleaks-exempt `larch-logs/`. A redaction miss or opaque bearer token in agent stderr can be committed and not caught by gitleaks Layers 1-2.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Fail closed on redactor non-zero exit; tighten publish policy or add post-publish secret assertions for *.stderr-tail.

### FINDING_20: Non-zero exit with empty stderr produces no .stderr-tail
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Non-zero exit with empty stderr still produces no `.stderr-tail`. Codex/cursor exit 1 with 0-byte sidecar: verdict line only, same blind spot as before for empty-stream failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Document limitation or synthesize tail from .diag / exit metadata when stderr is empty but status is failed.

### FINDING_21: Panel timeout 1860 clamped to 1800 without extending subprocess cap
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Panel timeout 1860 is clamped to 1800 without extending the subprocess cap. Claude fallback runs 60s shorter than the panel budget; marginal timeouts on long reviews.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Align launch-claude-subprocess.sh cap with panel timeout or document effective 1800s ceiling.

### FINDING_22: Plan-to-harness traceability drift for sidecar tests
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Mode-aware sidecar/diag/output tests live in `test-lib-failed-agent-stderr-tail.sh`, not `test-run-external-agent.sh` as planned. Plan-to-harness traceability drift only; behavior is tested in the lib harness.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Add a minimal sidecar integration case to test-run-external-agent.sh or update plan/docs to reference the lib harness.

### FINDING_23: pipefail shell option not restored after lib spool pipeline
- **Reviewer(s)**: dyn-bash-compat-pipefail-output.txt
- **Severity**: latent
- **Concern**: The pipefail guard disables pipefail for the spool pipeline but always re-enables it with `set -o pipefail` instead of restoring the caller’s prior option. A caller that sourced the lib with pipefail off (or a future script without `set -o pipefail`) would inherit pipefail after `render_failed_agent_stderr_tail` / `failed_agent_stderr_signature`, which can change unrelated pipeline behavior under `set -e`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-compat-pipefail-output.txt: Save and restore pipefail around the guarded region (e.g. `_pf=0; [[ $(set -o 2>/dev/null) == *pipefail*on* ]] && _pf=1; set +o pipefail; …; [[ "$_pf" -eq 1 ]] && set -o pipefail || set +o pipefail`), or run the spool pipeline in a subshell `( set +o pipefail; tail … >"$spool" )` so the caller’s shell options are untouched.

### FINDING_24: NS-retry failure stderr-tail not in collector resolution precedence
- **Reviewer(s)**: dyn-bash-compat-pipefail-output.txt
- **Severity**: important
- **Concern**: `_resolve_collector_stderr_tail_file` only prefers `*-retry.txt.stderr-tail` before `${reviewer_file}.stderr-tail`, but NS-retry failures write tails on `*-ns-retry.txt` while `REVIEWER_FILE` stays the original `*.txt`. On an NS-retry failure, §3.8 can miss the real stderr tail and fall back to a stale first-pass `.stderr-tail` or `.launch-stderr`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-compat-pipefail-output.txt: Insert a third precedence step after empty-output retry and before the primary sidecar, e.g. `${reviewer_file%.txt}-ns-retry.txt.stderr-tail`, and extend `scripts/test-collect-agent-results.sh` with an NS-retry failure case that asserts the ns-retry tail is emitted.

### FINDING_25: hook-anti-read-poll splits commands without respecting shell quoting
- **Reviewer(s)**: dyn-hook-regex-parser-output.txt
- **Severity**: important
- **Concern**: `bash_line_task_output_poll_token` splits on `;`, `&&`, and `||` without respecting shell quoting, so a single `echo`/`printf` argument that merely mentions `; cat tasks/<id>.output` (or `&&` / `||` with a task path) can be split into a synthetic segment treated as a real poll even though Bash never executed `cat`/`tail` on the task file.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-hook-regex-parser-output.txt: split only on metacharacters outside quotes (small quote-aware scanner), or run token detection on the full line first and require the match to lie outside quoted spans before incrementing task-output state.

### FINDING_26: hook sed -n read-verb detection uses non-portable `\b` on BSD grep
- **Reviewer(s)**: dyn-hook-regex-parser-output.txt
- **Severity**: important
- **Concern**: `bash_has_read_verb` uses `grep -Eq '…(\-n\b|--quiet)'` for `sed -n` / `sed --quiet` reads. `\b` is not POSIX ERE; BSD/macOS `grep` often does not implement word boundaries, so `sed -n … tasks/<id>.output` polling may not be classified as a read verb on Darwin while the harness expects it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-hook-regex-parser-output.txt: replace `\-n\b` with a portable boundary such as `-[[:space:]]n([^[:alnum:]_]|$)` (and keep the existing `--quiet` branch), and add a harness case that asserts the pattern on the platform’s default `grep`.

### OOS_1: [OUT_OF_SCOPE] hook-anti-read-poll.sh bundled unrelated to #3202
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Massive hook expansion bundled unrelated to #3202 stderr-tail wiring. Reviewers must separate polling-hook risk from stderr-tail risk in one diff; no direct breakage of #3202 but separate behavioral/regression surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Split into its own PR or commit series for clearer review.
  - From cursor-specialist-edge-cases-output.txt: Review hook changes independently of this PR.

### OOS_2: [OUT_OF_SCOPE] *.launch-stderr not excluded from design round publish allowlists
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `*.launch-stderr` is not excluded like `*.sidecar` from round/publish allowlists. Raw launcher stderr persists in tmpdir; accidental top-level design publish would rely on publish-time redaction only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Add *.launch-stderr to the same exclusion list as *.sidecar.

### OOS_3: [OUT_OF_SCOPE] implement/lint-fix launchers lack stderr sidecar hook
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Implement/lint-fix launchers lack sidecar hook; plan defers foreground surfacing there. `/implement` codex/cursor failures may still lack stderr tails in chat.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Follow-up stderr-source hook for implement launchers per plan out-of-scope note.
