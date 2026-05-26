### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/render-run-summary.sh:130-164; skills/implement/scripts/write-final-report.sh:49-51
- **Concern**: Omitting token CLI args does not yield `- **Cost**: N/A`. Scenario: Verified: `render-run-summary.sh` with no `--claude-*`/`--codex-*`/`--cursor-*` args still shells to `token-cost.sh` with default zeros and emits `💰 TOTAL ~$0.00 — Claude $0.00, Codex $0.00, Cursor $0.00`. Stage-1 re-invoke and FINDING_12-style "no token args" paths therefore cannot satisfy the plan's N/A contract or new "token-data-missing" assertions.
- **Proposed resolution**: Add `--cost-unavailable` (or skip `token-cost.sh`) in `render-run-summary.sh`, wire implement/design helpers to set it when token data is absent or FINDING_12 applies, and extend `scripts/test-render-run-summary.sh` for the N/A path.


### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/render-run-summary.sh:38-43, scripts/render-run-summary.sh:110-140, scripts/render-run-summary.sh:222-224
- **Concern**: Plan assumes omitted token args make render-run-summary emit Cost N/A, but the renderer defaults all token counts to 0 and always calls token-cost. Scenario: Stage-1 fallback and token-missing paths will render a misleading 💰 TOTAL ~$0.00 line or make the proposed N/A assertions fail
- **Proposed resolution**: Add an explicit unavailable-cost contract such as --cost-unavailable or track whether any token flag was supplied and skip token-cost when none were supplied; add render-run-summary tests for the no-token-args N/A path before wiring caller fallbacks


### FINDING_4:
- **Reviewer(s)**: Codex-Arch
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: skills/implement/scripts/write-final-report.sh:220-227, skills/design/scripts/render-final-summary.sh:196-213
- **Concern**: Plan appends fallback failures to Warnings after warning counts are already computed, and implement counts committed execution-issues.ndjson while append-tool-failure writes markdown logs. Scenario: The terminal block can say Warnings 0 even though the fallback just logged a renderer failure, or implement fallback telemetry can land in a log surface the summary never counts
- **Proposed resolution**: For both scripts, append fallback telemetry before composing the final body and refresh counts afterward; for implement, specify the exact run-log/markdown surface and keep the count source aligned with where the warning is written


### FINDING_5:
- **Reviewer(s)**: Cursor-Edge, Cursor-Edge, Cursor-Edge, Cursor-dyn-fallback-schema-parity, Cursor-dyn-fallback-schema-parity, Cursor-dyn-fallback-schema-parity
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/render-run-summary.sh:130-164
- **Concern**: skills/implement/scripts/write-final-report.sh (planned Stage 1). Scenario: Plan assumes omitting token CLI flags makes render-run-summary emit `- **Cost**: N/A` via an empty `cost_lines` path
- **Proposed resolution**: Renderer always calls `token-cost.sh` with default zero aggregate flags; `token-cost.sh` returns `TOTAL_COST=0.00`, so Stage 1 can still show a misleading `$0.00` / zero-token breakdown instead of `N/A` when only tokens are missing Stage 1 must not rely on omission alone: add an explicit cost-unavailable signal to `render-run-summary.sh` (and use it from Stage 1 + implement token-missing primary path), or have Stage 1 jump straight to Stage 2 self-composed `N/A` when the failure mode is token-related


### FINDING_6:
- **Reviewer(s)**: Cursor-Edge, Cursor-Edge, Cursor-dyn-fallback-schema-parity, Cursor-dyn-fallback-schema-parity
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/render-final-summary.sh:305-311
- **Concern**: skills/design/scripts/render-final-summary.sh (planned §4). Scenario: Plan says post-phase uses an existing "chat-print loop" reading `final-summary.md`, but post-phase printing is only via `render-run-summary.sh --print-stdout` inside `invoke_render`
- **Proposed resolution**: Renderer-fail fallback writes the file but never prints; `test-render-final-summary.sh:39` (`cmp` stdout vs file) and cancellation/happy-path chat output both break Add an explicit post-fallback print path (mirror `write-final-report.sh:415-422` / quiet FD 3) whenever `invoke_render` used fallback and `print_stdout=true`; keep stdout byte-identical to `final-summary.md`


### FINDING_7:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: nit
- **Focus area**: correctness
- **Location**: skills/implement/scripts/test-write-final-report.md:103
- **Concern**: skills/design/scripts/test-render-final-summary.md:117. Scenario: Plan lists three new harness cases per script but sibling `.md` stubs say "two new test cases"
- **Proposed resolution**: Doc drift causes incomplete test documentation during implementation Update both `.md` siblings to list all three cases (renderer-fail, token-missing, per-agent happy path)


### FINDING_8:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/render-run-summary.sh:38-140; scripts/token-cost.sh:87-236
- **Concern**: FINDING_1: The plan relies on omitting token argv to produce Cost N/A, but the renderer defaults every token counter to 0 and always invokes token-cost.sh, which emits TOTAL_COST=0.00 and TOTAL_TOKENS=0.. Scenario: Missing or deliberately omitted token data will render as a precise-looking $0.00 per-agent breakdown instead of N/A, silently underreporting unknown cost and causing the new token-missing and Stage 1 fallback tests to fail or lock in the wrong behavior.
- **Proposed resolution**: Add an explicit unavailable-cost path in render-run-summary.sh, such as tracking whether any token flag was supplied or adding --cost-unavailable, and skip token-cost.sh so tc=N/A only when token data is truly absent. Then update write-final-report.sh and render-final-summary.sh to use that path.


### FINDING_9:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/render-final-summary.sh:271-311
- **Concern**: FINDING_2: The plan adds a post-phase chat-print loop but does not say to stop passing --print-stdout through to render-run-summary.sh.. Scenario: On normal post-publish success, the renderer can print the structured block once and the new PHASE=post loop can print final-summary.md again; on a future partial renderer failure, users may see a partial stale block followed by the fallback block.
- **Proposed resolution**: Make invoke_render always render to final-summary.md without --print-stdout, validate or replace the file, then have the post phase print that final file exactly once. Keep the existing byte-identity assertion against that single print path.


### FINDING_10:
- **Reviewer(s)**: Codex-Edge
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/design/scripts/render-final-summary.sh:196-213; skills/design/scripts/render-final-summary.sh:271-302; skills/implement/scripts/write-final-report.sh:220-227; skills/implement/scripts/write-final-report.sh:361-367
- **Concern**: FINDING_3: The proposed fallback Warning append happens after the Warnings counts are computed, so the degraded final summary can report a stale warning count.. Scenario: When renderer fallback fires, append-tool-failure.sh records a Warnings entry, but the already-computed WARNINGS or WARN_N value is reused in the fallback body, making the chat summary say fewer warnings than the log actually contains.
- **Proposed resolution**: After a fallback warning is appended, either increment the in-memory warning count before composing the degraded body or recompute counts from the execution-issues log before the final render or self-composed fallback is written.


### FINDING_11:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/render-run-summary.sh:130-153
- **Concern**: Stage 1 assumes omitted token flags yield Cost N/A. Scenario: Re-invoke still runs token-cost on zeros and emits ~$0.00; token-missing test fails
- **Proposed resolution**: Add explicit cost-unavailable contract on render-run-summary or gate argv in write-final-report; use in Stage 1


### FINDING_12:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/render-run-summary.sh:38-43
- **Concern**: No-token fallback premise is false. Scenario: Omitted token flags are indistinguishable from explicit zero tokens because the renderer initializes all token counts to 0 and still calls token-cost.sh, so the proposed Stage 1 fallback and design COST_ARGS=empty path can emit TOTAL ~$0.00 instead of Cost N/A
- **Proposed resolution**: Add an explicit cost-unavailable mode or track whether any token flags were supplied before calling token-cost.sh; make callers use it and add a direct render-run-summary no-token regression


### FINDING_13:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/write-final-report.sh:162-185
- **Concern**: Implement primary no-token path is not changed. Scenario: The plan adds a token-missing regression expecting Cost N/A, but write-final-report.sh currently leaves counts at 0 and always passes token flags, so ordinary missing token data remains a priced zero line rather than N/A
- **Proposed resolution**: Track TOKEN_JSON availability and build COST_ARGS like render-final-summary.sh; omit token flags or pass the new cost-unavailable mode when no valid token report exists


### FINDING_14:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/render-final-summary.sh:196-213
- **Concern**: Fallback warning counts will be stale. Scenario: The plan appends render fallback failures under Warnings after WARNINGS is already counted, so the fallback summary can print Warnings: 0 even though it just logged a warning
- **Proposed resolution**: Append the fallback warning before composing the fallback body or increment WARNINGS locally before writing final-summary.md; apply the same ordering check to write-final-report.sh


### FINDING_15:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: skills/design/scripts/render-final-summary.sh:75-82
- **Concern**: Proposed design token fixture will be deleted. Scenario: The plan says to set up token-report-final.json for the design happy-path per-agent test, but render-final-summary.sh deletes that file before invoking token-report.sh, making the test flaky or ineffective unless token-report.sh is stubbed
- **Proposed resolution**: Have the test stub scripts/token-report.sh under a temp CLAUDE_PLUGIN_ROOT to emit the desired BUCKETS payload instead of pre-seeding token-report-final.json


### FINDING_16:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/render-run-summary.sh:130-223
- **Concern**: Stage 1 "omit all token flags → `- **Cost**: N/A`" is incorrect for current renderer. Scenario: Re-invoking `render-run-summary.sh` with no `--claude-*`/`--codex-*`/`--cursor-*` args still defaults counts to 0 and `token-cost.sh` emits `TOTAL_COST=0.00`, so Stage 1 yields `💰 TOTAL ~$0.00 — Claude $0.00, …` not `N/A`; planned token-missing assertions and Stage 1 success criteria fail
- **Proposed resolution**: Either (a) add a small renderer guard (all aggregate+bucket counts zero and no token argv → `tc=N/A`), scoped to this fix, or (b) drop Stage 1 for N/A goals and rely on Stage 2 self-compose; if keeping Stage 1, assert `$0.00` breakdown not `N/A` unless renderer changes


### FINDING_17:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/render-run-summary.sh:38-43,110-140; scripts/token-cost.sh:225-236
- **Concern**: The plan assumes omitting token flags makes render-run-summary emit Cost N/A, but the renderer initializes all token values to 0 and token-cost always emits TOTAL_COST=0.00.. Scenario: Stage 1 fallback and the proposed token-data-missing tests will produce a misleading dollar line such as TOTAL ~$0.00 instead of the required unavailable cost line, so the fix does not preserve the stated N/A contract.
- **Proposed resolution**: Add an explicit unavailable path, such as a render-run-summary --cost-unavailable flag or a parsed-token-args-present sentinel that skips token-cost and emits - **Cost**: N/A when no cost data exists; update write-final-report and render-final-summary callers/tests to use that path.


### FINDING_18:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:188-200,275-284; skills/design/scripts/render-final-summary.sh:37
- **Concern**: The proposed design fallback lives inside invoke_render, but several cancellation paths can call render-final-summary with an empty --mode before run-params.json exists, and the script exits during argument validation before invoke_render runs.. Scenario: Title-filter, already-planned cancel, and tier-gate cancel can still produce no structured summary and no cost line despite the new renderer-failure fallback.
- **Proposed resolution**: Default SUMMARY_MODE_STRING to N/A in the Final summary block before invoking render-final-summary, and/or relax render-final-summary so empty mode normalizes to N/A; add a regression for an early cancellation path with no run-params.json.


### FINDING_19:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/render-final-summary.sh:196-213,271-303; skills/implement/scripts/write-final-report.sh:220-227,361-367
- **Concern**: The plan appends fallback-render failures to Warnings after warning counts have already been computed for the summary body.. Scenario: The printed fallback summary can say Warnings: 0 while the fallback itself just logged a warning, making the final block internally stale and weakening the terminal-summary contract.
- **Proposed resolution**: When appending a fallback warning, increment the local warning count before composing the fallback body, or append first and recompute counts before writing/printing the final summary.


### FINDING_20:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:23-24 / skills/implement/SKILL.md:420-429 / skills/implement/SKILL.md:1801
- **Concern**: ROOT CAUSE D dismissed as NEVER-only; many paths jump straight to Step 18 and skip Step 17. Scenario: Early bail (tracking-init-failed, coder probe failure, checks fail → skip to Step 18, etc.) never runs write-final-report.sh --print-stdout; Step 18 refresh omits --print-stdout so chat has no structured Cost line on exactly the bail/stall outcomes Decision 5 requires
- **Proposed resolution**: Add an in-scope step: either route every skip-to-18 path through Step 17 first, or add --print-stdout to the Step 18 write-final-report.sh call and document that contract in skills/implement/SKILL.md; add a harness case that simulates skip-to-18 without Step 17


### FINDING_21:
- **Reviewer(s)**: Codex-Requirements, Codex-dyn-test-path-injection
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:49; scripts/render-run-summary.sh:38-43,110-140,152-164,222-224
- **Concern**: 1. Plan assumes omitting token args makes Cost N/A, but render-run-summary defaults missing token args to zero and still calls token-cost.sh. Scenario: Stage 1 fallback and token-data-missing paths can print a $0.00 per-agent line instead of - **Cost**: N/A, violating the plan's own unavailable-cost acceptance
- **Proposed resolution**: Change the plan to add an explicit renderer unavailable-cost mode such as --cost-unavailable, or make fallback self-compose - **Cost**: N/A without reusing the normal zero-token pricing path; update tests to pin no-token versus legitimate-zero behavior


### FINDING_22:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:51,69; scripts/render-run-summary.sh:215-224
- **Concern**: 2. Self-composed fallback schema omits the renderer's conditional Outcome bullet. Scenario: Bailed, stalled, cancelled-*, and failed-plan-write fallback summaries would not mirror the full schema for the exact terminal outcomes the goal enumerates
- **Proposed resolution**: Specify that both implement and design fallback composers must apply the same Outcome bullet condition as render-run-summary.sh, and add assertions for bailed/stalled/cancelled/failed outcomes


### FINDING_23:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: plan.txt:95-113,157-167; skills/design/SKILL.md:262-285,970-974
- **Concern**: 3. Regression plan does not exercise every terminal outcome or the cancellation Final summary block required by the goal. Scenario: Approved or merged cases can pass while cancelled-sprawl, cancelled-tier-gate, cancelled-plan-size-hard, cancelled-already-planned, failed-plan-write, forked-dry-run, design-only, or stalled chat paths regress and drop the Cost line
- **Proposed resolution**: Add parametrized script tests for the full implement and design terminal outcome enums through the actual chat-print path, including the design Final summary block/cancellation callsite, asserting Cost is present and Outcome appears where the renderer requires it


### FINDING_24:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: code-quality
- **Location**: skills/design/scripts/render-final-summary.sh:75-83; plan.txt:113
- **Concern**: 4. Design per-agent happy-path test setup pre-creates token-report-final.json, but render-final-summary.sh deletes and regenerates that file before rendering. Scenario: The proposed test may not actually verify nonzero Claude/Codex/Cursor breakdowns, leaving the user-visible per-agent acceptance criterion unpinned
- **Proposed resolution**: Stub token-report.sh in the test plugin root or generate real ledger inputs so render-final-summary.sh produces token-report-final.json with nonzero Claude, Codex, and Cursor buckets before asserting the Cost line


### FINDING_25:
- **Reviewer(s)**: Cursor-dyn-fallback-schema-parity
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/write-final-report.sh:49-50
- **Concern**: scripts/render-run-summary.sh:130-223. Scenario: Stage 1 claims re-invoking `render-run-summary.sh` with no token flags yields `- **Cost**: N/A` via `cost_lines=""`.
- **Proposed resolution**: Omitting flags leaves defaults at 0; `token-cost.sh` still succeeds and emits `TOTAL_COST=0.00`, so the cost branch prints a `$0.00` breakdown—not `N/A`. Stage 1 may “succeed” without meeting the plan’s N/A cost contract. Revise Stage 1: either document `$0.00` as acceptable degraded cost, or add a renderer/caller path that treats “no token inputs / unavailable” as `N/A` before relying on re-invoke; do not cite empty `cost_lines` as the mechanism.


### FINDING_26:
- **Reviewer(s)**: Cursor-dyn-fallback-schema-parity
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/test-write-final-report.sh:97-99
- **Concern**: skills/implement/scripts/write-final-report.sh:292-340. Scenario: Regression case 2 asserts stdout `- **Cost**: N/A` when `token-report.json` is missing.
- **Proposed resolution**: Happy-path `run_body_render` always passes explicit `--claude-tokens 0` (etc.); renderer emits `$0.00`, not `N/A`. Test will fail unless implement also omits token args on missing-token paths (design FINDING_12 style). Align test with intended behavior: assert `$0.00` if zeros are passed, or add implement-side “omit all token flags when no token JSON” and then assert `N/A`.


### FINDING_27:
- **Reviewer(s)**: Cursor-dyn-fallback-schema-parity
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-render-run-summary.sh:59-240
- **Concern**: skills/implement/scripts/test-write-final-report.sh:95-99. Scenario: skills/design/scripts/test-render-final-summary.sh:109-113
- **Proposed resolution**: Proposed fallback tests only pin `- **Cost**: N/A` and substring breakdown checks, not the full bullet list. `test-render-run-summary.sh` pins design PR/code-review omission (236-237) but not a canonical ordered bullet list; self-composed Stage 2 bodies can drift (extra PR, wrong Outcome, wrong defaults) without CI failure. Add shared schema assertions (ordered `grep -Fq` list or golden fixture) for implement vs design fallback bodies, or extract a `compose-fallback-body` helper tested once beside `test-render-run-summary.sh`.


### FINDING_29:
- **Reviewer(s)**: Codex-dyn-fallback-schema-parity
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/render-run-summary.sh:214-238; <TMPDIR>/plan.txt:51-69
- **Concern**: FINDING_1 proposed fallback schema omits the renderer Outcome bullet. Scenario: The renderer emits - **Outcome** only for bailed*/stalled/cancelled-*/failed-* for both skills, but the proposed self-composed implement and design fallbacks list Mode first and would drop Outcome on stalled, bailed, cancelled, and failed-plan-write terminal summaries.
- **Proposed resolution**: Add the same case branch immediately after the title in both self-composed fallbacks and cover implement bailed/stalled plus design cancelled/failed fallback cases.


### FINDING_30:
- **Reviewer(s)**: Codex-dyn-fallback-schema-parity
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/render-run-summary.sh:38-43,110-128,130-156,222-224; scripts/token-cost.sh:86-90,168-236; <TMPDIR>/plan.txt:49-49,135-135
- **Concern**: FINDING_2 no-token Stage 1 does not produce Cost N/A. Scenario: Omitting token args leaves renderer defaults at zero and still invokes token-cost.sh, which outputs TOTAL_COST=0.00 and zero vendor costs; the Stage 1 fallback the plan expects to render N/A will instead render a real-looking $0.00 cost line when telemetry is unavailable.
- **Proposed resolution**: Add an explicit renderer-supported cost-unavailable mode/flag and use it from fallbacks, or skip Stage 1 for N/A fallback and self-compose only after exact schema tests are added.


### FINDING_31:
- **Reviewer(s)**: Codex-dyn-fallback-schema-parity
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/render-run-summary.sh:179-186,225-231; scripts/render-run-summary.md:33-39,50-52; <TMPDIR>/plan.txt:51-51,69-69
- **Concern**: FINDING_3 proposed implement fallback emits PR unconditionally. Scenario: The renderer suppresses PR when the normalized PR display is N/A or when --skill design; the plan’s implement Stage 2 bullet list includes PR as an all-bullets field, so no-PR implement outcomes would gain - **PR**: N/A. The design omission of PR and Code review is correct and is a --skill design branch, not a --no-pr flag.
- **Proposed resolution**: Replicate the exact renderer conditions: emit PR only when skill is not design and pr_disp is not N/A; emit Code review when skill is not design; add an implement-without-PR fallback test.


### FINDING_33:
- **Reviewer(s)**: Cursor-dyn-test-path-injection
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:95-96
- **Concern**: PATH='' cannot force render-run-summary failure. Scenario: write-final-report.sh and render-final-summary.sh invoke "$PLUGIN_ROOT/scripts/render-run-summary.sh" (write-final-report.sh:285-318; render-final-summary.sh:298-301), not a PATH lookup; PATH='' leaves the real renderer callable
- **Proposed resolution**: Replace PATH='' with a CLAUDE_PLUGIN_ROOT plugin stub: copy the harness pattern from test-write-final-report.sh:19-50 / test-render-final-summary.sh:42-83 and install a render-run-summary.sh stub that exits 1 (or emits empty output)


### FINDING_34:
- **Reviewer(s)**: Codex-dyn-test-path-injection
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/scripts/write-final-report.sh:282-352; skills/design/scripts/render-final-summary.sh:271-302; skills/implement/scripts/test-write-final-report.sh:19-25; skills/design/scripts/test-render-final-summary.sh:42-83
- **Concern**: Plan suggests PATH= as a renderer-fail technique, but both subjects invoke $PLUGIN_ROOT/scripts/render-run-summary.sh directly. Scenario: PATH isolation will not hide render-run-summary.sh and can break dirname, mktemp, mkdir, cp, jq, token-cost, and sourced helpers before exercising the target fallback
- **Proposed resolution**: Require a CLAUDE_PLUGIN_ROOT test plugin whose scripts/render-run-summary.sh is an executable failing or empty-output stub; keep PATH intact and follow the existing harness stub-injection pattern


### FINDING_35:
- **Reviewer(s)**: Codex-dyn-test-path-injection
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/render-final-summary.sh:75-83,113-128; skills/design/scripts/test-render-final-summary.sh:42-68; skills/implement/scripts/test-write-final-report.sh:19-25
- **Concern**: Design happy-path plan says to precreate token-report-final.json, but the subject deletes and regenerates that file via token-report.sh. Scenario: The new per-agent test can silently ignore the authored fixture; the existing design stub only gives Codex nonzero bucket data, and there is no shared lib-test.sh or adjacent all-three-vendor fixture to reuse
- **Proposed resolution**: Add or inline a token-report.sh stub that writes a valid JSON report with nonzero Claude, Codex, and Cursor totals plus BUCKETS_claude, BUCKETS_codex, and BUCKETS_cursor; for implement, place the same shape at larch-logs/implement/<run>/token-report.json or use a shared fixture


