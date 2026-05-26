### FINDING_1: code-quality: scripts/launch-review.sh:560-581 Triplicated KV-parse and record-vendor block also at launch-codex-implement.sh:358-372 and launch-codex-ci.sh:230-245
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Three launchers duplicate the same helper-output consumption loop; a field-mapping bug fix must be edited in three places. Adding a fourth Codex launcher or renaming CACHED_INPUT handling risks inconsistent ledger rows across review/implement/CI lanes. Extract a thin apply-codex-usage-kvs.sh (or lib function) called by all three launchers after parse-codex-usage.sh.
- **Suggested revision**: Address the concern above.

### FINDING_2: code-quality: scripts/parse-codex-usage.md:34-48 vs scripts/parse-codex-usage.sh:35-42
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Sibling doc omits top-level and .msg top-level token field probes that the jq program implements. Contributors extending schema support may update jq only and miss doc/fixture expectations; Codex 0.125 smoke shape is undocumented. Document the third usage-detection branch and top-level field coalesce paths in parse-codex-usage.md.
- **Suggested revision**: Address the concern above.

### FINDING_3: code-quality: scripts/launch-review.sh:561-565 vs scripts/launch-codex-implement.sh:358
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Only launch-review tees parse-codex-usage.sh stderr into the sidecar on parse failure; implement/ci discard diagnostics. An implement or CI run with non-empty events.jsonl but parse failure leaves no parse hint in sidecar logs, slowing ops debugging. Align stderr handling across launchers or document review-only teeing in all launcher .md siblings.
- **Suggested revision**: Address the concern above.

### FINDING_4: correctness: scripts/parse-codex-usage.sh:31-49
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] jq stderr is suppressed and failures surface as generic no usage events. A jq regression or malformed filter on a valid events file silently drops Codex cost rows with a misleading diagnostic. Stop swallowing jq stderr; distinguish jq failure from empty usage.
- **Suggested revision**: Address the concern above.

### FINDING_5: code-quality: scripts/parse-codex-usage.sh:31-46
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Dense inline jq reduce is hard to extend for new Codex schema buckets. Future schema additions require editing a monolithic string and increase risk of subtle double-count or coalesce bugs. Move filter to a .jq file or structured def blocks for readability.
- **Suggested revision**: Address the concern above.

### FINDING_6: correctness: scripts/parse-codex-usage.sh:33-44
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Parser sums every usage-shaped JSON object; cumulative plus per-turn events would double-count. A Codex run emitting per-response usage objects and a final token_usage rollup with session totals records roughly 2x actual tokens and overstates cost despite per-bucket rates. Restrict counted event types or dedupe by event id once production JSONL shapes are documented; extend the checked-in CLI fixture with multi-event captures.
- **Suggested revision**: Address the concern above.

### FINDING_7: correctness: scripts/launch-codex-implement.sh:358, scripts/launch-codex-ci.sh:230
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Implement and CI launchers discard parse-codex-usage stderr while review appends it to the sidecar. JSONL present but parse fail-closed: operator sees missing Codex cost with no parse-codex-usage diagnostic in implement/CI sidecars. Mirror launch-review.sh temp stderr capture and append to SIDECAR_LOG when events file is non-empty.
- **Suggested revision**: Address the concern above.

### FINDING_8: correctness: scripts/parse-codex-usage.sh:70-85
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] jq stderr is fully suppressed; all jq failures surface as no usage events. A jq version or syntax failure is misread as zero usage, hiding the root cause during CLI upgrades. Preserve jq stderr for non-empty parse failures; reserve no usage events for empty sums only.
- **Suggested revision**: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] risk-integration: scripts/run-external-agent.sh:246-277
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] run-external-agent progress lines share stdout with Codex JSONL events sidecar. Future JSON-shaped progress lines could be mistaken for usage and skew totals (today non-JSON lines are skipped). Out of scope for #2813; consider stderr routing or --capture-stdout-only if this appears in production.
- **Suggested revision**: Address the concern above.

### FINDING_10: risk-integration: scripts/launch-review.sh:560-565
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Sidecar parse-failure append path is untested. Non-empty events file plus parse failure (schema drift) may stop appending diagnostics to the review sidecar without CI failure. Add a launch-review stub case with bad JSONL in events file; assert sidecar contains parse-codex-usage diagnostic and ledger has no codex row.
- **Suggested revision**: Address the concern above.

### FINDING_11: risk-integration: scripts/test-launch-review.sh:867
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Events sidecar assertion greps for literal "usage". Stubs aligned to native Codex 0.125 JSONL without a "usage" key could fail the count assertion despite correct per-bucket ledger rows. Assert ledger buckets or invoke parse-codex-usage.sh on the events file instead of grep -c '"usage"'.
- **Suggested revision**: Address the concern above.

### FINDING_12: risk-integration: scripts/test-launch-review.sh:537-671
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Jq-gated codex integration tests skip entirely when jq is absent. Developer or minimal CI without jq sees green harnesses but no per-bucket or fail-closed coverage. Require jq at harness entry or fail with explicit message instead of unconditional pass.
- **Suggested revision**: Address the concern above.

### FINDING_13: risk-integration: scripts/launch-review.sh:476-527
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] /dev/null sidecar branch has no harness coverage. Refactor could parse or write ledger rows when sidecar is disabled, breaking review-codex token semantics. Add test forcing SIDECAR=/dev/null path and assert no vendor row and no events file consumption.
- **Suggested revision**: Address the concern above.

### FINDING_14: risk-integration: scripts/test-launch-codex-ci.sh:106-194
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Runtime tests do not assert --json in codex argv. Removing --json from launch-codex-ci.sh while stubs still emit JSONL would pass CI but break real Codex runs (fail-closed, no cost). Record stub argv and assert --json is present, matching test-codex-implementer.sh.
- **Suggested revision**: Address the concern above.

### FINDING_15: [OUT_OF_SCOPE] risk-integration: Makefile
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Mixed branch bundles unrelated breadcrumb harness expansion. Unrelated shard failures or timeouts can block merge of the Codex token fix. Split PRs or isolate #2813 commits from #2790 rollout when possible.
- **Suggested revision**: Address the concern above.

### FINDING_16: [OUT_OF_SCOPE] risk-integration: docs/linting.md
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Manual real-CLI smoke is acceptance-only. Future Codex CLI shape drift may only surface post-merge in operator runs. Optional follow-up: periodic CI job against installed Codex CLI (plan out-of-scope).
- **Suggested revision**: Address the concern above.

### FINDING_17: security: scripts/parse-codex-usage.sh:36-44
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] jq sums token-like fields on any JSON object without a Codex usage type gate A malformed or diagnostic JSONL line with incidental input_tokens fields inflates BUCKETS_codex and cost lines in committed run logs Filter to documented usage event types (e.g. type==token_usage) and add a negative harness fixture
- **Suggested revision**: Address the concern above.

### FINDING_18: security: scripts/launch-review.sh:507-510
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Codex --json stdout is stored whole in .events.jsonl in session tmpdir Events file may hold prompts/tool output; implement lane grants Codex write access to that tmpdir; mishandled copies could leak secrets Document tmpdir-only residual; delete events file after successful parse when forensics not needed
- **Suggested revision**: Address the concern above.

### FINDING_19: security: scripts/launch-review.sh:574-577
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Unquoted INPUT=$v style KV parsing from helper stdout If parse-codex-usage.sh ever emitted shell metacharacters, assignment could execute before token-ledger validation Quote assignments and/or validate digits in launchers before record-vendor
- **Suggested revision**: Address the concern above.

### FINDING_20: security: scripts/lib-quiet.sh:151-155
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] 1KiB cut applies to full breadcrumb line including text= A long API key in breadcrumb text= can leave a recoverable prefix in committed larch-logs breadcrumbs Truncate/drop only the text payload; add regression test
- **Suggested revision**: Address the concern above.

### FINDING_21: correctness: scripts/launch-review.sh:560-581
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Failure-path transcript tail is copied into .events.jsonl and parsed as usage on failed Codex reviews. Failed/timed-out review with non-empty transcript whose last lines contain JSON usage-shaped text gets token-ledger rows and non-zero cost despite EXIT_CODE!=0. Gate parse/record on success; move run-external failure tail to stderr for JSON-mode tools; and/or restrict parser to Codex token_usage event types.
- **Suggested revision**: Address the concern above.

### FINDING_22: architecture: scripts/launch-codex-implement.sh:358
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Implement/CI discard parse-codex-usage stderr unlike launch-review. Shape drift or parse failures on implement/CI leave zero Codex cost with no sidecar diagnostic while review surfaces parse errors. Reuse launch-review sidecar merge for parse failures.
- **Suggested revision**: Address the concern above.

### FINDING_23: correctness: scripts/parse-codex-usage.sh:46-48
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] jq failures are reported as no usage events. Broken jq leads operators to misdiagnose API/schema issues as missing usage. Emit a distinct jq-failed diagnostic separate from no-usage.
- **Suggested revision**: Address the concern above.

### FINDING_24: risk-integration: scripts/launch-review.sh:487-549
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Only the last retry attempt events file is billed. Multi-attempt transient failures can under-report tokens versus actual API usage. Document retry billing semantics or accumulate usage across attempts if required.
- **Suggested revision**: Address the concern above.

### FINDING_25: code-quality: scripts/test-launch-review.sh:867
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Transient-retry test greps for literal "usage" not native token_usage shape. Regression in real Codex JSONL shape might not fail this assertion. Assert via parse-codex-usage.sh or token_usage type / ledger buckets.
- **Suggested revision**: Address the concern above.

### FINDING_26: [OUT_OF_SCOPE] risk-integration: skills/review-and-fix/scripts/review-and-fix.sh:257
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] review-and-fix Codex path still aggregate-only. BLENDED_WARN can still appear for coder-loop Codex usage. Follow-up: wire --json + parse-codex-usage.sh there.
- **Suggested revision**: Address the concern above.

### FINDING_27: **New helper** [`scripts/parse-codex-usage.sh`](scripts/parse-codex-usage.sh): line-streaming `jq -nR`, per-field coalesce, `uncached_input = max(input - cached, 0)`, fail-closed exits, four KV lines, defensive `cached_tokens > input_tokens`.
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - **New helper** [`scripts/parse-codex-usage.sh`](scripts/parse-codex-usage.sh): line-streaming `jq -nR`, per-field coalesce, `uncached_input = max(input - cached, 0)`, fail-closed exits, four KV lines, defensive `cached_tokens > input_tokens`.
- **Suggested revision**: Address the concern above.

### FINDING_28: **All three launchers** add `--json`, split stdout→`*.events.jsonl` / stderr→sidecar, `rm -f` stale events before launch, call the helper, record per-bucket `record-vendor` / token-record on success only (no aggregate fallback).
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - **All three launchers** add `--json`, split stdout→`*.events.jsonl` / stderr→sidecar, `rm -f` stale events before launch, call the helper, record per-bucket `record-vendor` / token-record on success only (no aggregate fallback).
- **Suggested revision**: Address the concern above.

### FINDING_29: **Tests/docs/Makefile**: `test-parse-codex-usage.sh` (+ fixtures), updated launcher/scraper/implementer harnesses, sibling `.md` files, `test-harnesses-17` registration, `docs/linting.md` row.
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - **Tests/docs/Makefile**: `test-parse-codex-usage.sh` (+ fixtures), updated launcher/scraper/implementer harnesses, sibling `.md` files, `test-harnesses-17` registration, `docs/linting.md` row.
- **Suggested revision**: Address the concern above.

### FINDING_30: **Round-1 fixes** correctly add `.msg.input_tokens` / top-level `token_usage` support and checked-in Codex 0.125 fixtures.
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - **Round-1 fixes** correctly add `.msg.input_tokens` / top-level `token_usage` support and checked-in Codex 0.125 fixtures.
- **Suggested revision**: Address the concern above.

### FINDING_31: [OUT_OF_SCOPE] **`scripts/launch-review.sh:560-565`** — Plan text specified `parse-codex-usage.sh … 2>/dev/null`; implementation captures stderr and appends diagnostics to `$SIDECAR` when events exist but parsing fails. Ledger behavior remains fail-closed; this is a deliberate observability improvement beyond the plan wording.
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - **`scripts/launch-review.sh:560-565`** — Plan text specified `parse-codex-usage.sh … 2>/dev/null`; implementation captures stderr and appends diagnostics to `$SIDECAR` when events exist but parsing fails. Ledger behavior remains fail-closed; this is a deliberate observability improvement beyond the plan wording.
- **Suggested revision**: Address the concern above.

### FINDING_32: [OUT_OF_SCOPE] **Other `codex exec` call sites** (`skills/review-and-fix/scripts/review-and-fix.sh`, `scripts/lint-fix-loop.sh`, etc.) still use combined `2>&1` without JSONL capture. The plan scoped only the three launchers; this is expected residual aggregate-only telemetry outside #2813.
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - **Other `codex exec` call sites** (`skills/review-and-fix/scripts/review-and-fix.sh`, `scripts/lint-fix-loop.sh`, etc.) still use combined `2>&1` without JSONL capture. The plan scoped only the three launchers; this is expected residual aggregate-only telemetry outside #2813.
- **Suggested revision**: Address the concern above.

### FINDING_33: [OUT_OF_SCOPE] **Branch noise** — `fa1546e4` (breadcrumb #2849) and `c47fb38a` (larch-logs flush) are unrelated to the #2813 plan; excluded from fidelity findings per review rules.
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - **Branch noise** — `fa1546e4` (breadcrumb #2849) and `c47fb38a` (larch-logs flush) are unrelated to the #2813 plan; excluded from fidelity findings per review rules.
- **Suggested revision**: Address the concern above.

