### FINDING_1: code-quality: scripts/test-launch-review.sh:99-110,1512-1523
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Identical assert_meta_stderr_sink_before_outer_launcher is duplicated in codex and cursor subshells; test-collect-agent-retry.sh has a third near-copy with a generic before_prefix. If ordering rules change (e.g. also assert before CMD_JSON on primary launch), maintainers must update three copies and subshells can drift. Hoist one shared assert_meta_key_before_key helper at file scope or in a sourced test lib; reuse from both lanes and test-collect-agent-retry.sh.
- **Suggested revision**: Address the concern above.

### FINDING_2: code-quality: scripts/test-collect-agent-retry.sh:852-876
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] New codex sink-outer-retry case inlines the same TOOL=codex meta printf block as case Q2 instead of a helper. Future meta field additions for codex outer-retry fixtures require editing multiple inline blocks; risk of Q2 and sink-retry diverging. Extract write_codex_outer_meta (or parameterize write_outer_meta by TOOL) and use it for Q2 and sink-outer-retry.
- **Suggested revision**: Address the concern above.

### FINDING_3: code-quality: scripts/test-launch-review.sh:99-110
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] assert_meta_stderr_sink_before_outer_launcher calls fail "$label" with no meta context on mismatch. A ordering regression shows only the label string, not which line numbers were found, slowing harness debugging. On failure, emit sink_ln, outer_ln, and a short head of the meta file like other asserts in these harnesses.
- **Suggested revision**: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] architecture: (branch)
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Six commits vs main mix #3273 with unrelated fixes/docs/tests. Reviewers must mentally filter a large diff; bisecting a regression to stderr/risk work is harder. Prefer separate PRs or clearly separated commits when landing stacked work (observation only).
- **Suggested revision**: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] code-quality: scripts/launch-review.md:497-510
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Full-branch diff adds large #3283 degraded-response docs in the same file as the #3273 --risk bullet. Doc readers may conflate two features in one changelog-style edit. Keep #3273 doc delta minimal in the feature commit (already true in 33b85f448).
- **Suggested revision**: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] correctness: scripts/lib-external-launcher-common.sh:26-32,scripts/collect-agent-results.sh:531
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Append path can write a second STDERR_SINK= after OUTER_LAUNCHER=; collector keeps the last value. If base and append sinks ever differed, retries could pick the wrong sink silently. Pre-existing; optional hardening is dedupe-on-read or omit 6th arg when run-external-agent already wrote base STDERR_SINK=.
- **Suggested revision**: Address the concern above.

### FINDING_7: `--risk` is forwarded through top-level `ARGS` into `_launch_codex` / `_launch_cursor` (lines 42–48, 1129–1130), then into `external_launcher_append_outer_meta` (lines 605, 1030).
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - `--risk` is forwarded through top-level `ARGS` into `_launch_codex` / `_launch_cursor` (lines 42–48, 1129–1130), then into `external_launcher_append_outer_meta` (lines 605, 1030).
- **Suggested revision**: Address the concern above.

### FINDING_8: `STDERR_SINK` ordering tests align with the real contract: `run-external-agent.sh` writes base meta (`STDERR_SINK` before `CMD_JSON`, lines 199–202), then `external_launcher_append_outer_meta` appends `OUTER_LAUNCHER=…` (lines 27–31 in `lib-external-launcher-common.sh`). Pairing `grep -Fxq` presence with “first `STDERR_SINK=` before first `OUTER_LAUNCHER=`” avoids false greens from a sink line only appended by the launcher block.
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - `STDERR_SINK` ordering tests align with the real contract: `run-external-agent.sh` writes base meta (`STDERR_SINK` before `CMD_JSON`, lines 199–202), then `external_launcher_append_outer_meta` appends `OUTER_LAUNCHER=…` (lines 27–31 in `lib-external-launcher-common.sh`). Pairing `grep -Fxq` presence with “first `STDERR_SINK=` before first `OUTER_LAUNCHER=`” avoids false greens from a sink line only appended by the launcher block.
- **Suggested revision**: Address the concern above.

### FINDING_9: Collector already replays `--risk "$META_OUTER_LAUNCHER_RISK"` and `--stderr-sink` on outer retry; the bug was launch-review discarding `--risk` before meta emission—now fixed.
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - Collector already replays `--risk "$META_OUTER_LAUNCHER_RISK"` and `--stderr-sink` on outer retry; the bug was launch-review discarding `--risk` before meta emission—now fixed. Tests were not executed in this read-only session; static review only. ---
- **Suggested revision**: Address the concern above.

### FINDING_10: Static source greps (`_RUN_EXTERNAL_SINK_ARGS`, `_outer_sink_args`, `RETRY_ARGS`) are correctly replaced with runtime `.meta` artifact checks at the `run-external-agent.sh` boundary.
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: - Static source greps (`_RUN_EXTERNAL_SINK_ARGS`, `_outer_sink_args`, `RETRY_ARGS`) are correctly replaced with runtime `.meta` artifact checks at the `run-external-agent.sh` boundary.
- **Suggested revision**: Address the concern above.

### FINDING_11: Ordering helpers (`assert_meta_stderr_sink_before*`) implement the FINDING_2 mitigation: first `^STDERR_SINK=` must precede first `^OUTER_LAUNCHER=` (or `^CMD_JSON=`), catching outer-only duplicates that would false-green a source grep.
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: - Ordering helpers (`assert_meta_stderr_sink_before*`) implement the FINDING_2 mitigation: first `^STDERR_SINK=` must precede first `^OUTER_LAUNCHER=` (or `^CMD_JSON=`), catching outer-only duplicates that would false-green a source grep.
- **Suggested revision**: Address the concern above.

### FINDING_12: Outer-retry cases use canonical `$REPO_ROOT/scripts/launch-review.sh` with leaf CLI stubs only — aligned with FINDING_3 constraints.
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: - Outer-retry cases use canonical `$REPO_ROOT/scripts/launch-review.sh` with leaf CLI stubs only — aligned with FINDING_3 constraints.
- **Suggested revision**: Address the concern above.

### FINDING_13: CMD_JSON retry uses valid vendor-shaped `json_array bash "$HELPER" …` — aligned with FINDING_4 constraints; fail-closed `..` and sink-absent cases preserved unchanged.
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: - CMD_JSON retry uses valid vendor-shaped `json_array bash "$HELPER" …` — aligned with FINDING_4 constraints; fail-closed `..` and sink-absent cases preserved unchanged.
- **Suggested revision**: Address the concern above.

### FINDING_14: `--risk` round-trip tests cover both lanes (`low` + default `high`), directly guarding the discarded-flag regression (FINDING_12).
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: - `--risk` round-trip tests cover both lanes (`low` + default `high`), directly guarding the discarded-flag regression (FINDING_12).
- **Suggested revision**: Address the concern above.

### FINDING_15: Both harnesses are wired into CI (`Makefile`: `test-collect-agent-retry` in `test-harnesses-2`, `test-launch-review` in `test-harnesses-9`).
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: - Both harnesses are wired into CI (`Makefile`: `test-collect-agent-retry` in `test-harnesses-2`, `test-launch-review` in `test-harnesses-9`). **Regression risk:** Low. FINDING_12 is the only behavior change (discarded flag → functional). FINDING_6 is documentary. Test changes strengthen coverage without weakening collector allowlists. ---
- **Suggested revision**: Address the concern above.

### FINDING_16: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: 1. **risk-integration** `scripts/test-collect-agent-retry.sh:814-827` — The existing `corrupt-risk` case verifies outer-retry succeeds with invalid input `OUTER_LAUNCHER_RISK=medium` but does not assert the retry `.meta` records normalized `OUTER_LAUNCHER_RISK=high`. Pre-existing; not introduced by this diff. A follow-up assertion would close the collector→launcher→retry-meta loop for risk normalization.
- **Suggested revision**: Address the concern above.

### FINDING_17: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: 2. **risk-integration** `scripts/test-launch-review.sh` — No primary-path test that `--risk medium` (non-`high|low`) normalizes to `OUTER_LAUNCHER_RISK=high` in outer `.meta`. Plan edge case documents this via `external_launcher_append_outer_meta`; only `low` + default are required. Pre-existing gap, not amplified by this change.
- **Suggested revision**: Address the concern above.

### FINDING_18: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: 3. **risk-integration** `scripts/test-launch-cursor-ci.sh` / `scripts/test-launch-cursor-implement.sh` — No dedicated harness asserts FINDING_6 `.meta` byte-stability after adding explicit `"" ""` args. Coverage relies on `scripts/test-lib-external-launcher-common.sh` function-level tests; acceptable given behavior-neutral intent.
- **Suggested revision**: Address the concern above.

### FINDING_19: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 1. **risk-integration** `scripts/lib-external-launcher-common.sh:19` — Empty 5th positional to `external_launcher_append_outer_meta` uses `${5:-${RISK:-high}}`, so an exported `RISK` in the environment can influence `OUTER_LAUNCHER_RISK` without an explicit launcher `--risk`. Pre-existing; FINDING_6’s explicit `""` does not change that. **Suggested fix:** Only if you want to pin behavior: treat empty `$5` as “use default high” without env fallback (e.g. separate unset vs empty handling).
- **Suggested revision**: Address the concern above.

### FINDING_20: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 2. **risk-integration** `scripts/launch-review.sh:478` vs `launch-review.md:20-22` — Docs now state `--risk` drives “risk-gated effort” on collector replay, but Codex still always invokes `agent-model-args.sh --with-effort` and Cursor still wraps with `/max-mode on` regardless of parsed `RISK` (including on retry). Pre-existing execution gap; the PR improves meta fidelity but does not close it. **Impact:** Operational mismatch, not a privilege-escalation path (retries stay high-effort when meta says `low`). Narrow docs or gate effort on normalized `RISK` if you want meta and behavior aligned.
- **Suggested revision**: Address the concern above.

### FINDING_21: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 3. **security** `scripts/collect-agent-results.sh:536-545` — `validate_retry_stderr_sink_or_mark` only rejects `..` in `META_STDERR_SINK`; full `[A-Za-z0-9._/-]` validation happens later when `launch-review.sh` / `run-external-agent.sh` receive `--stderr-sink`. Pre-existing; mitigated on the outer-retry path by launcher re-validation. **Suggested fix:** Optional defense-in-depth: call `validate_meta_scalar_path` in the collector before retry launch. Other branch commits (`cleanup.sh` enumeration warnings, `ship-pr.sh` errexit preservation, `review-and-fix.sh` pathspec-only staging) are reliability or fail-closed hardening, not new trust-boundary regressions.
- **Suggested revision**: Address the concern above.

### FINDING_22: **`launch-review.sh`**: Both lanes initialize `RISK=""`, capture `--risk` in argv parsing, and pass `"$RISK"` as the 5th arg to `*_launcher_append_outer_meta` (empty → `${5:-${RISK:-high}}` → `high`, unchanged default).
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: - **`launch-review.sh`**: Both lanes initialize `RISK=""`, capture `--risk` in argv parsing, and pass `"$RISK"` as the 5th arg to `*_launcher_append_outer_meta` (empty → `${5:-${RISK:-high}}` → `high`, unchanged default).
- **Suggested revision**: Address the concern above.

### FINDING_23: **`launch-cursor-implement.sh` / `launch-cursor-ci.sh`**: Explicit `"" ""` for risk/stderr slots (behavior-neutral today).
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: - **`launch-cursor-implement.sh` / `launch-cursor-ci.sh`**: Explicit `"" ""` for risk/stderr slots (behavior-neutral today).
- **Suggested revision**: Address the concern above.

### FINDING_24: **Tests**: Static source greps removed; runtime checks assert `STDERR_SINK=` on retry `.meta`, ordering vs `OUTER_LAUNCHER` / `CMD_JSON`, and `--risk` round-trip (`low` / default `high`) in both launch-review lanes; collector outer-retry + CMD_JSON cases mirror case Q / case A without weakening canonical launcher or CMD_JSON validation.
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: - **Tests**: Static source greps removed; runtime checks assert `STDERR_SINK=` on retry `.meta`, ordering vs `OUTER_LAUNCHER` / `CMD_JSON`, and `--risk` round-trip (`low` / default `high`) in both launch-review lanes; collector outer-retry + CMD_JSON cases mirror case Q / case A without weakening canonical launcher or CMD_JSON validation.
- **Suggested revision**: Address the concern above.

### FINDING_25: **`launch-review.md`**: Documents `--risk` → `OUTER_LAUNCHER_RISK`.
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: - **`launch-review.md`**: Documents `--risk` → `OUTER_LAUNCHER_RISK`. Wiring is symmetric across codex/cursor lanes; fail-closed risk normalization remains in `external_launcher_append_outer_meta`; ordering assertions correctly require `run-external-agent.sh` to own the first `STDERR_SINK=` (append-only sink after `OUTER_LAUNCHER=` would fail the test).
- **Suggested revision**: Address the concern above.

### FINDING_26: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: 1. **risk-integration** `scripts/lib-external-launcher-common.sh:19` — Empty 5th arg uses `${5:-${RISK:-high}}`, so a shell `RISK` env var can influence `OUTER_LAUNCHER_RISK` when callers pass `""`; pre-existing contract, not introduced by this branch. **Why OOS:** unchanged semantics; FINDING_6 only makes empty slots explicit.
- **Suggested revision**: Address the concern above.

### FINDING_27: [OUT_OF_SCOPE] architecture
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: 2. **architecture** Branch vs `main` includes five additional commits (ship-pr errexit restore, review-and-fix dirty-tree, validate-research, cleanup, harness sharding) outside the stderr/risk plan. **Why OOS:** not modified by `33b85f448`; separate issues/PR scope.
- **Suggested revision**: Address the concern above.

### FINDING_28: **correctness** `scripts/test-collect-agent-retry.sh:896-898` — The new `assert_meta_stderr_sink_before … CMD_JSON` check on the CMD_JSON retry path is tautological, not a runtime forwarding contract. That retry path invokes real `scripts/run-external-agent.sh` directly (via `collect-agent-results.sh` `RETRY_ARGS` at `scripts/collect-agent-results.sh:687-744`) and never calls `*_launcher_append_outer_meta`, so the retry `.meta` is written only by `run-external-agent.sh` in a fixed block where `STDERR_SINK=` (lines 199–201 of `scripts/run-external-agent.sh`) always precedes `CMD_JSON=` (line 202). Whenever the preceding `grep -Fxq "STDERR_SINK=$SINK_CMD_JSON"` passes, the ordering assertion must also pass regardless of whether `RETRY_ARGS+=(--stderr-sink …)` forwarding regressed. It therefore adds no regression signal beyond the presence check and can read as validating wrapper ownership when no wrapper participates. **Suggested fix:** Drop the CMD_JSON ordering assertion, or replace it with a check that actually distinguishes forwarding paths—for example assert `^STDERR_SINK=` appears before the first `^OUTER_LAUNCHER=` on outer-launcher retry metas only (already done at `scripts/test-collect-agent-retry.sh:848-850` / `877-879`), or add a test-only `run-external-agent.sh` shim that logs argv and assert `--stderr-sink` is present on the CMD_JSON retry invocation.
- **Reviewer**: dyn-meta-ordering-contract-output.txt
- **Concern**: - **correctness** `scripts/test-collect-agent-retry.sh:896-898` — The new `assert_meta_stderr_sink_before … CMD_JSON` check on the CMD_JSON retry path is tautological, not a runtime forwarding contract. That retry path invokes real `scripts/run-external-agent.sh` directly (via `collect-agent-results.sh` `RETRY_ARGS` at `scripts/collect-agent-results.sh:687-744`) and never calls `*_launcher_append_outer_meta`, so the retry `.meta` is written only by `run-external-agent.sh` in a fixed block where `STDERR_SINK=` (lines 199–201 of `scripts/run-external-agent.sh`) always precedes `CMD_JSON=` (line 202). Whenever the preceding `grep -Fxq "STDERR_SINK=$SINK_CMD_JSON"` passes, the ordering assertion must also pass regardless of whether `RETRY_ARGS+=(--stderr-sink …)` forwarding regressed. It therefore adds no regression signal beyond the presence check and can read as validating wrapper ownership when no wrapper participates. **Suggested fix:** Drop the CMD_JSON ordering assertion, or replace it with a check that actually distinguishes forwarding paths—for example assert `^STDERR_SINK=` appears before the first `^OUTER_LAUNCHER=` on outer-launcher retry metas only (already done at `scripts/test-collect-agent-retry.sh:848-850` / `877-879`), or add a test-only `run-external-agent.sh` shim that logs argv and assert `--stderr-sink` is present on the CMD_JSON retry invocation.
- **Suggested revision**: Address the concern above.

