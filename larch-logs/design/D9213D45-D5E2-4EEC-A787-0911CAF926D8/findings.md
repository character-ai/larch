### FINDING_1:
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review-and-fix/scripts/test-review-and-fix.sh (plan §4 case 4a)
- **Concern**: Cap-boundary test variant 1 asserts hoisted mav-resume-past-cap for STARTING_ROUND=6 with five prior DEGRADED_ROUND=true rounds (entry_effective_cap=10). Scenario: 6 > 10 is false; hoisted and in-loop guards never fire; test fails or passes for the wrong reason while missing the real MAV resume case (STARTING_ROUND=base_cap+1 with prior_deg=0)
- **Proposed resolution**: Use variant 2 parameters for hoisted past-cap (rounds 1–5 clean, STARTING_ROUND=6, ROUND_CAP=5) or raise STARTING_ROUND to entry_effective_cap+1 (e.g. 11) when all five prior rounds are degraded

### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:41; skills/review-and-fix/scripts/review-implement-step5-loop.sh:107-115
- **Concern**: Cap-boundary test matrix contradicts the proposed condition. Scenario: With five prior DEGRADED_ROUND=true artifacts, STARTING_ROUND=6 and base_cap=5 gives entry_effective_cap=10, so STARTING_ROUND > entry_effective_cap is false and mav-resume-past-cap must not fire. Conversely, with clean prior rounds the hoisted check fires before the loop, not the existing in-loop check.
- **Proposed resolution**: Revise the regression cases so clean prior rounds with STARTING_ROUND=6/base_cap=5 assert entry-time mav-resume-past-cap, and degraded prior rounds either use STARTING_ROUND=11 to test past inflated cap or STARTING_ROUND=6 to assert the loop proceeds.

### FINDING_3:
- **Reviewer(s)**: Codex-Arch, Codex-Edge, Codex-Requirements
- **Severity**: important
- **Focus area**: code-quality
- **Location**: skills/review-and-fix/scripts/test-review-and-fix.sh:33-40; Makefile:714-727
- **Concern**: New gated test section is not wired into the section registry or lint shard targets. Scenario: The plan adds section_runs step5-starting-round, but the current harness only accepts dispatch, convergence, and parsers, and Makefile only shards those three. A sibling section would either be rejected with --section or never run under make lint.
- **Proposed resolution**: Either place these cases under an existing sharded section, or update the --section allowlist, add a Makefile test-review-and-fix-step5-starting-round target, and include it in a test-harnesses shard.

### FINDING_4:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/review-and-fix/scripts/test-review-and-fix.sh:2003-2005; skills/review-and-fix/scripts/review-implement-step5-loop.sh:74-113
- **Concern**: Planned direct loop tests reuse the parser-only source pattern without the loop dependencies. Scenario: run_implement_loop depends on emit_kv, larch_err, emit_breadcrumb, flush_review_batches, count_prior_degraded_rounds, and kv_get; sourcing only review-implement-step5-loop.sh as the parsers section does will make the new tests fail for harness setup rather than behavior.
- **Proposed resolution**: In the new test section, explicitly source scripts/lib-implement-round-cap.sh and provide local stubs for emit_kv, larch_err, emit_breadcrumb, flush_review_batches, and kv_get before calling run_implement_loop, or exercise the public review-and-fix.sh entrypoint instead.

### FINDING_5:
- **Reviewer(s)**: Codex-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/review-and-fix/scripts/review-implement-step5-loop.md:5; skills/review-and-fix/scripts/review-and-fix.md:29-62
- **Concern**: Primary contract documentation is left stale for the changed Step 5 loop envelope. Scenario: The plan updates the loop sidecar doc and implement prose, but the loop doc names review-and-fix.md as the primary contract, and that file still documents only single-round diff mode output, not STEP5_REVIEW_STATUS, mav-resume-past-cap, or starting-round-invalid STALL_TRACKING=false.
- **Proposed resolution**: Update review-and-fix.md with the loop-mode flags and final-envelope statuses, or change the sidecar doc to name the loop md as authoritative for Step 5 loop envelopes.

### FINDING_6:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:1214
- **Concern**: Stall branch still mandates Set STALL_TRACKING=true after parsing STALL_TRACKING from the envelope. Scenario: An orchestrator following the stall bullet literally overwrites envelope STALL_TRACKING=false and Step 18 can still rename the tracking issue to [STALLED]
- **Proposed resolution**: Replace unconditional Set STALL_TRACKING=true with assign STALL_TRACKING from the parsed envelope token (default true only when the token is absent); explicitly forbid overriding false for starting-round-invalid

### FINDING_7:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review-and-fix/scripts/review-implement-step5-loop.sh:82-87
- **Concern**: Hoisted past-cap check can turn arbitrary invalid resumes into success before validating any prior artifact. Scenario: With STARTING_ROUND=999 and no round-998 artifact, count_prior_degraded_rounds treats missing envs as non-degraded, STARTING_ROUND > base cap, and the proposed entry check emits mav-resume-past-cap/exit 0 instead of starting-round-invalid; Step 5 then proceeds as if review completed, silently skipping validation/review state
- **Proposed resolution**: Constrain the pre-artifact mav-resume-past-cap fast path to the MAV resume shape, e.g. require STARTING_ROUND == entry_effective_cap + 1 and the immediately prior round artifact exists or FINAL_ROUND_NUM/EFFECTIVE_ROUND_CAP provenance confirms the MAV round; otherwise run the artifact probe and return starting-round-invalid on miss

### FINDING_8:
- **Reviewer(s)**: Codex-Edge, Codex-dyn-test-scaffold-validity
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review-and-fix/scripts/test-review-and-fix.sh:1285-1292
- **Concern**: The cap-boundary regression fixture asserts the opposite of degraded-cap math. Scenario: The plan says round-1..round-5 all DEGRADED_ROUND=true gives prior_deg=5 and entry_effective_cap=10 for STARTING_ROUND=6, then expects mav-resume-past-cap. That condition is false under the proposed formula, so either the test fails or an implementation is bent to consume degraded rounds as if they did not extend the cap
- **Proposed resolution**: Swap the variants: all prior rounds DEGRADED_ROUND=false with STARTING_ROUND=6/base_cap=5 should assert entry-time mav-resume-past-cap; degraded prior rounds should assert the loop proceeds to round 6

### FINDING_9:
- **Reviewer(s)**: Codex-Edge
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: skills/review-and-fix/scripts/review-implement-step5-loop.sh:74-87
- **Concern**: The sync retry helper needs an explicit non-fatal sync contract under set -e. Scenario: review-and-fix.sh runs with set -euo pipefail; a helper implemented as sync >/dev/null 2>&1 between probes will abort the whole wrapper if sync returns non-zero, despite the plan's edge-case claim that sync failures still retry and then return a deterministic stall
- **Proposed resolution**: Specify and test sync >/dev/null 2>&1 || true inside step5_probe_prior_round_env, then perform the second -f check and return 1 on miss

### FINDING_10:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: code-quality
- **Location**: skills/review-and-fix/scripts/test-review-and-fix.sh:2000-2005
- **Concern**: The proposed direct run_implement_loop tests omit required sourced helpers/stubs. Scenario: The parsers section currently sources only review-implement-step5-loop.sh; run_implement_loop also calls count_prior_degraded_rounds, emit_kv, larch_err, emit_breadcrumb, flush_review_batches, and kv_get. A new section that sources the loop "the same way" and calls run_implement_loop will fail before exercising the planned cases
- **Proposed resolution**: Have the test section either invoke review-and-fix.sh through the existing harness path or explicitly source scripts/lib-implement-round-cap.sh and provide local stubs for emit_kv/larch_err/emit_breadcrumb/flush_review_batches/kv_get plus controlled checks/lint helpers

### FINDING_11:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:1214
- **Concern**: Stall bullet still unconditionally sets STALL_TRACKING=true. Scenario: Envelope may emit STALL_TRACKING=false but prose orders true; Step 18 rename reads ship-pr-state/finalize-state STALL_TRACKING
- **Proposed resolution**: Amend stall bullet: for starting-round-invalid set STALL_TRACKING from parsed envelope; else true; if seeding ship-pr-state before Step 16 persist that value

### FINDING_12:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review-and-fix/scripts/review-implement-step5-loop.sh:82-86
- **Concern**: Hoisted cap check would allow cap-resume success without proving the previous round exists. Scenario: With --starting-round 999 or a missing round artifact, the proposed STARTING_ROUND > entry_effective_cap branch returns mav-resume-past-cap and Step 5 can proceed as complete without a real prior review round
- **Proposed resolution**: Only emit mav-resume-past-cap after validating evidence of a completed prior round or MAV resume source; keep missing artifacts as starting-round-invalid unless the prior round artifact/sentinel exists

### FINDING_13:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review-and-fix/scripts/test-review-and-fix.sh:1285-1292
- **Concern**: Proposed cap-boundary test math contradicts the cap logic. Scenario: Five prior DEGRADED_ROUND=true files make entry_effective_cap=10, so STARTING_ROUND=6 is not past cap and the asserted mav-resume-past-cap path will not fire
- **Proposed resolution**: Use DEGRADED_ROUND=false for the STARTING_ROUND=6/base_cap=5 past-cap case, and add a separate degraded-inflation case with STARTING_ROUND=11 when five prior rounds are degraded

### FINDING_14:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/review-and-fix/scripts/test-review-and-fix.sh:33-40, Makefile:714-727
- **Concern**: New test section can be added but not exercised by targeted harnesses. Scenario: The harness currently accepts only dispatch/convergence/parsers and CI shard targets call only those three sections, so a sibling step5-starting-round section would be rejected directly and skipped by make lint
- **Proposed resolution**: Integrate the cases into an existing section or update the section whitelist plus Makefile shard target and shard coverage wiring

### FINDING_15:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/review-and-fix/scripts/review-implement-step5-loop.sh:319-342
- **Concern**: Plan assumes sync can fix a MAV writer race, but mav-apply does not write the probed env artifact. Scenario: If the missing file is tied to the MAV apply handoff, retrying stat after sync cannot create round-N/review-and-fix.env, so the root handoff remains uncontracted
- **Proposed resolution**: Make the writer contract explicit: have mav-apply write or preserve a minimal resume sentinel/env file, or probe an artifact that mav-apply actually writes such as coder.env plus a completion marker

### FINDING_16:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/review-and-fix/scripts/review-implement-step5-loop.sh:111-114
- **Concern**: Planned entry-time mav-resume-past-cap exits before the existing tally/findings flush side effect. Scenario: The current in-loop cap path calls flush_review_batches before exit; the hoisted path described in the plan emits the envelope and exits directly, so a resume that is past cap can skip code-review-tally and review-findings-full batch refreshes
- **Proposed resolution**: Preserve the existing side effect in the hoisted branch by calling flush_review_batches with the same best-effort pattern before exit, or explicitly justify and test why the flush is no longer required

### FINDING_17:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review-and-fix/scripts/review-implement-step5-loop.sh:107-114
- **Concern**: The planned cap-boundary test cases contradict the effective-cap math. Scenario: The plan says STARTING_ROUND=6 with five degraded prior rounds gives effective_cap=10 but should fire mav-resume-past-cap; 6 > 10 is false, so the test would fail or force wrong behavior. The clean prior-round variant would now be caught by the hoisted check, not the in-loop check
- **Proposed resolution**: Revise the tests so clean rounds 1-5 with STARTING_ROUND=6 verifies the hoisted past-cap path, and use STARTING_ROUND=11 when five degraded prior rounds should be past the inflated cap

### FINDING_18:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: code-quality
- **Location**: skills/review-and-fix/scripts/test-review-and-fix.sh:33-40
- **Concern**: The new gated test section is not fully wired or self-contained. Scenario: If implemented as a sibling section, the current --section allowlist rejects it and Makefile shards will not run it; if appended under parsers, helpers from convergence and runtime functions used by run_implement_loop are unavailable in --section parsers runs
- **Proposed resolution**: Add the new section to the allowlist and Makefile target, or keep it inside an existing section with local setup; move shared helpers outside gated blocks and source/stub emit_kv, larch_err, emit_breadcrumb, count_prior_degraded_rounds, kv_get, count_high_severity_accepted, flush_review_batches, and run run_implement_loop in subshells because it exits

### FINDING_19:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:1214
- **Concern**: Unconditional Set STALL_TRACKING=true contradicts envelope STALL_TRACKING=false. Scenario: Envelope reclassification never prevents [STALLED] rename because stall branch still forces true
- **Proposed resolution**: Replace with explicit rule: set STALL_TRACKING from parsed envelope; default true only for other stall reasons

### FINDING_20:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review-and-fix/scripts/review-implement-step5-loop.sh:108-113
- **Concern**: Plan's cap-boundary regression case contradicts the effective-cap comparison. Scenario: The plan asks STARTING_ROUND=6 with five prior DEGRADED_ROUND=true files to assert mav-resume-past-cap, but the loop computes effective cap 10 and 6 > 10 is false, so the proposed test would fail or encode the wrong contract
- **Proposed resolution**: Revise the case to use DEGRADED_ROUND=false for rounds 1-5 when STARTING_ROUND=6, or keep five degraded rounds and set STARTING_ROUND=11; also fix the line claiming degraded inflation makes base_cap+1 past-cap

### FINDING_21:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: code-quality
- **Location**: skills/review-and-fix/scripts/test-review-and-fix.sh:2000-2005 skills/review-and-fix/scripts/review-implement-step5-loop.sh:60-84
- **Concern**: The planned direct-source loop tests omit required dependencies. Scenario: The parsers section can source review-implement-step5-loop.sh alone because it only calls parse helpers, but run_implement_loop needs emit_kv, larch_err, count_prior_degraded_rounds, and on some paths flush_review_batches or other review-and-fix helpers, so the new tests can fail before validating the behavior
- **Proposed resolution**: Specify the test scaffold: source scripts/lib-quiet.sh and scripts/lib-implement-round-cap.sh, or stub emit_kv/larch_err/emit_breadcrumb/flush_review_batches and any post-round helpers before calling run_implement_loop

### FINDING_22:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review-and-fix/scripts/review-implement-step5-loop.sh:82-84
- **Concern**: The retry behavior may be left unvalidated. Scenario: The plan allows the first-miss then present-on-retry case to become a covered-by-inspection skip, but the new acceptance criterion is specifically the two-attempt sync retry that prevents the false positive
- **Proposed resolution**: Make the retry test deterministic, for example by shadowing sync in the test shell so it creates the env file before the second probe, then assert the loop proceeds past the artifact guard

### FINDING_23:
- **Reviewer(s)**: Cursor-dyn-shell-retry-semantics
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:41
- **Concern**: Test case 4 variant 1 asserts hoisted mav-resume-past-cap for STARTING_ROUND=6 with prior_deg=5 and entry_effective_cap=10. Scenario: 6 > 10 is false so the hoisted branch must not fire; the test would fail on correct code or force a wrong implementation
- **Proposed resolution**: Change variant 1 to assert normal loop entry (no mav-resume) when STARTING_ROUND=6 and inflated cap is 10; keep mav-resume assertion for STARTING_ROUND=11 or use variant 2 only for hoisted past-cap

### FINDING_24:
- **Reviewer(s)**: Codex-dyn-shell-retry-semantics
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:11,51,63; skills/review-and-fix/scripts/review-implement-step5-loop.sh:82-85
- **Concern**: sync retry is not a semantic visibility or cache-invalidation barrier. Scenario: If the first [[ -f ]] misses because the writer is still in flight, a negative lookup is cached, or the path is wrong, sync does not force the writer to close, does not validate the pathname, and does not guarantee VFS/name-cache invalidation before the second stat; on local APFS a closed directory entry should already be visible, so this does not defeat Hypothesis A as claimed
- **Proposed resolution**: Reframe sync as best-effort only, or replace it with a deterministic contract: write the env atomically before the producing command returns and verify the artifact after child completion; if retry remains, use bounded wait/backoff and do not claim it proves cache invalidation

### FINDING_25:
- **Reviewer(s)**: Codex-dyn-shell-retry-semantics
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lib-implement-round-cap.sh:28-38; skills/review-and-fix/scripts/review-and-fix.sh:1330-1343; <TMPDIR>/plan.txt:9,64
- **Concern**: Hoisted degraded-round counting can undercount a partially written env before the artifact probe. Scenario: review-and-fix.env is written with > and then appended; a concurrent reader can observe an empty or incomplete file, and count_prior_degraded_rounds treats missing or malformed DEGRADED_ROUND as false. The proposed entry-time cap check can then emit mav-resume-past-cap before the within-loop recomputation has a chance to see the completed file
- **Proposed resolution**: Make review-and-fix.env writes atomic via temp file plus mv, or require a complete marker before count_prior_degraded_rounds contributes a file to cap math; alternatively move the stability check ahead of hoisted cap math for the prior artifact set

### FINDING_26:
- **Reviewer(s)**: Codex-dyn-shell-retry-semantics
- **Severity**: latent
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:9; scripts/run-step5-review.sh:207-211; scripts/lib-implement-round-cap.sh:38
- **Concern**: entry_prior_deg is not validated before 10# arithmetic. Scenario: Bash arithmetic with an empty entry_prior_deg in $((10#$base_cap + 10#$entry_prior_deg)) silently treats the degraded count as 0, while an unset variable under nounset aborts. The single-round launcher already validates DEGRADED_ROUNDS before arithmetic, but the plan does not add the same guard for the hoisted loop path
- **Proposed resolution**: Add a case validation for entry_prior_deg after count_prior_degraded_rounds and before entry_effective_cap arithmetic; emit a tool-failure diagnostic if it is empty or non-numeric

### FINDING_27:
- **Reviewer(s)**: Codex-dyn-shell-retry-semantics
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: <TMPDIR>/plan.txt:41
- **Concern**: The proposed cap-boundary regression test expects the opposite of the proposed predicate. Scenario: With STARTING_ROUND=6, base_cap=5, and five prior degraded rounds, entry_effective_cap is 10, so STARTING_ROUND > entry_effective_cap is false. The planned assertion that mav-resume-past-cap fires immediately would fail or push the implementer toward incorrect >= or base-cap-only logic
- **Proposed resolution**: Change that test to use zero degraded prior rounds for the immediate mav-resume-past-cap case; add a separate degraded-prior case expecting the loop to proceed because 6 <= 10

### FINDING_28:
- **Reviewer(s)**: Cursor-dyn-envelope-consumer-coverage
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:1206-1214
- **Concern**: Step 5 stall bullet unconditionally overwrites parsed STALL_TRACKING. Scenario: After parsing STALL_TRACKING=false from the step5 envelope (line 1206), line 1214 still says Set STALL_TRACKING=true for every stall; an orchestrator following the stall bullet verbatim will still force true and Step 18 can still rename to [STALLED] despite the envelope flip
- **Proposed resolution**: Replace Set STALL_TRACKING=true with explicit retain-the-parsed-STALL_TRACKING-from-the-envelope-above; do-not-overwrite language for all stall reasons (starting-round-invalid is false; other stalls remain true via envelope)

### FINDING_29:
- **Reviewer(s)**: Codex-dyn-envelope-consumer-coverage
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lib-implement-round-cap.sh:20-38; skills/review-and-fix/scripts/review-implement-step5-loop.sh:80-84
- **Concern**: The proposed cap-boundary tests use inverted expectations for degraded prior rounds. Scenario: With round-1..round-5 all DEGRADED_ROUND=true and STARTING_ROUND=6, count_prior_degraded_rounds returns 5 and entry_effective_cap is 10, so the proposed entry check 6 > 10 will not emit mav-resume-past-cap. Conversely the all-clean STARTING_ROUND=6 case will be caught by the new entry-time check, not the existing in-loop check. This makes the planned regression tests either fail or miss the intended boundary behavior.
- **Proposed resolution**: Revise the test matrix: for clean cap-boundary use STARTING_ROUND=6 with base_cap=5 and assert entry-time mav-resume-past-cap, ideally with round-5 missing to prove the artifact guard is bypassed. For degraded inflated-cap boundary use STARTING_ROUND=11 with five prior degraded rounds contributing entry_effective_cap=10, or assert STARTING_ROUND=6 proceeds normally when effective_cap=10.

### FINDING_30:
- **Reviewer(s)**: Codex-dyn-envelope-consumer-coverage
- **Severity**: nit
- **Focus area**: risk-integration
- **Location**: skills/review-and-fix/scripts/test-review-and-fix.sh:33-40
- **Concern**: The proposed new section name is not added to the harness section allowlist. Scenario: The plan suggests a new section_runs step5-starting-round block, but the current --section validator only accepts dispatch, convergence, and parsers. Running the new section directly would fail before tests execute unless the allowlist is updated.
- **Proposed resolution**: Either add step5-starting-round to the case allowlist or place the new cases under an existing accepted section such as parsers/convergence and document that choice.

### FINDING_31:
- **Reviewer(s)**: Cursor-dyn-test-scaffold-validity
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:41-41
- **Concern**: Case 4 first subcase cap math is wrong for mav-resume-past-cap. Scenario: With base_cap=5 and five prior rounds DEGRADED_ROUND=true, count_prior_degraded_rounds(..., 6) yields prior_deg=5 and entry_effective_cap=10; STARTING_ROUND=6 is not > 10, so hoisted mav-resume never fires and the test fails or passes for the wrong reason
- **Proposed resolution**: Use STARTING_ROUND=11 (or base_cap+prior_deg+1) for the inflated-cap mav-resume subcase, or change the assertion to expect normal loop entry (not mav-resume) when STARTING_ROUND is within the inflated cap

### FINDING_32:
- **Reviewer(s)**: Codex-dyn-test-scaffold-validity
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:39; <TMPDIR>/plan.txt:75-77
- **Concern**: The Hypothesis A test is marked skippable even though deterministic shell coverage is achievable. Scenario: If the plan lands with only a COVERAGE_NOTE skip, the first-miss-then-retry path in step5_probe_prior_round_env can regress while all tests pass; that is the exact filesystem-visibility path the change claims to defend.
- **Proposed resolution**: Require a deterministic test: shadow sync with a shell function or PATH stub that creates the expected review-and-fix.env between the first failed probe and retry, or add a test-only retry hook to the helper, then assert the loop reaches the _implement_round_body stub.

### FINDING_33:
- **Reviewer(s)**: Codex-dyn-test-scaffold-validity
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: <TMPDIR>/plan.txt:43; skills/review-and-fix/scripts/test-review-and-fix.sh:2000-2005; skills/review-and-fix/scripts/test-review-and-fix.sh:1281-1292
- **Concern**: Sourcing the loop helper like the parsers section is not enough to run run_implement_loop cases. Scenario: The parsers section only sources review-implement-step5-loop.sh, but run_implement_loop also needs emit_kv, emit_breadcrumb, larch_err, count_prior_degraded_rounds, kv_get, count_high_severity_accepted, and flush_review_batches depending on the branch. The plan also reuses write_prior_round even though it is defined inside the convergence section and will be absent when the new section runs alone via --section.
- **Proposed resolution**: Move shared fixture helpers outside gated sections, source scripts/lib-implement-round-cap.sh or stub count_prior_degraded_rounds deliberately, and define minimal emit_kv/emit_breadcrumb/larch_err/kv_get/flush_review_batches/count_high_severity_accepted test doubles before invoking run_implement_loop.

### FINDING_34:
- **Reviewer(s)**: Codex-dyn-test-scaffold-validity
- **Severity**: latent
- **Focus area**: code-quality
- **Location**: <TMPDIR>/plan.txt:77; skills/review-and-fix/scripts/review-implement-step5-loop.sh:60-71; scripts/lib-quiet.sh:122-128
- **Concern**: The planned STALL_TRACKING and STALL_REASON grep co-occurrence assertion is ambiguous for the actual envelope format. Scenario: step5_emit_final_envelope emits each key through emit_kv, and emit_kv prints one KEY=value per line. A same-line co-occurrence grep would false-fail; two independent greps can false-pass if a stub, diagnostic, or second envelope contributes one token while the final envelope contributes the other.
- **Proposed resolution**: Parse the captured output into envelope variables with the same token-aware key scanner used by the orchestrator, assert exactly one final STEP5_REVIEW_STATUS envelope for each invocation, then compare STALL_TRACKING and STALL_REASON values from that parsed envelope.
