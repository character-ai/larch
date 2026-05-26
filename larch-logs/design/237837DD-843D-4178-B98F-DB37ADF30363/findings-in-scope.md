### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:48-50
- **Concern**: Misclassifies zero_findings_prose_finding_ids as narrow-trigger (validation-exhausted). Scenario: Stub output at skills/review/scripts/test-aggregate-findings.sh:217-223 has no attestation and uses ### FINDING_ids prose; validator emits missing-attestation (MERGE_PIPELINE_RC=2), not preamble/empty_merge. Harness at :1204-1220 explicitly expects validation-failed.
- **Proposed resolution**: Keep zero_findings_prose_finding_ids in the validation-failed bucket. Only map zero_findings, preamble_contradiction, numbered_prose_contradiction, and other true MERGE_PIPELINE_RC=1 stubs to validation-exhausted.

### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/dispatch-with-waterfall.sh:278-287; skills/review/scripts/aggregate-findings.sh:543-566; skills/review/scripts/review-core.sh:514-515
- **Concern**: Pattern gate prevents the proposed narrow-trigger validator mapping from running for normal empty-merge or preamble-only outputs. Scenario: The plan requires --require-result-pattern ^[[:space:]]*### FINDING_[0-9], and the dispatcher rejects STATUS=OK files that lack that pattern before aggregate-findings.sh sees them. The validator's MERGE_PIPELINE_RC=1 cases are precisely zero structured output blocks, so normal empty-merge attestation and preamble_finding_substring outputs become DISPATCH_OK=false and aggregate REASON=dispatch-failed. review-core.sh only stalls on validation-exhausted, so the preserved downstream contract is not actually preserved.
- **Proposed resolution**: Either broaden the dispatcher gate for this slot to admit validator-owned narrow-trigger candidates, for example structured FINDING heading OR exact empty-merge attestation where appropriate, or explicitly map all-pattern-exhausted aggregator dispatch failures that correspond to these narrow outputs to REASON=validation-exhausted. Add a real-dispatch test, not only an AGGREGATE_DISPATCH_SH stub, proving review-core receives validation-exhausted.

### FINDING_3:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/dispatch-with-waterfall.sh:311-332; scripts/test-dispatch-with-waterfall.sh:302-323
- **Concern**: The proposed aggregate test describes Cursor primary narration falling through to Codex phase 2, but the new aggregate slot is codex-primary. Scenario: With a slot row tool=codex and both externals present, phase 1 is Codex and phase 2 is Cursor. Cursor-primary to Codex-phase2 is the dispatcher unit-test shape for a cursor slot, not the proposed aggregate-findings integration. A copied test can pass only by stubbing around the real ordering, leaving the new codex-primary aggregate path untested.
- **Proposed resolution**: Rewrite the aggregate regression as Codex phase 1 narration-only then Cursor phase 2 valid ballot, or Codex absent then Cursor phase 2 narration-only then Claude phase 3 valid ballot. If keeping a dispatcher unit test for Cursor to Codex, leave it in scripts/test-dispatch-with-waterfall.sh rather than using it as aggregate integration coverage.

### FINDING_4:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review/scripts/aggregate-findings.sh:257-262; skills/review/scripts/test-aggregate-findings.sh:1204-1220
- **Concern**: The plan says zero_findings_prose_finding_ids is a preamble-trigger MERGE_PIPELINE_RC=1 case, contradicting the validator contract. Scenario: The validator explicitly excludes non-numeric FINDING_ids prose from the preamble signal, and the existing regression asserts it must not emit AGGREGATOR_VALIDATION_FAILED=preamble_finding_substring. Updating this case to expect validation-exhausted will either fail the harness or remove coverage for a documented negative case.
- **Proposed resolution**: Keep zero_findings_prose_finding_ids as validation-failed. Use the existing numbered_prose_contradiction or preamble_contradiction stub for a preamble-trigger validation-exhausted test, subject to the pattern-gate issue above.

### FINDING_5:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review/scripts/aggregate-findings.sh:2 (planned --require-result-pattern)
- **Concern**: Pattern gate omits empty-merge attestation line. Scenario: `orchestrator-aggregator.md` requires valid empty merges to end with `LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED` and no `### FINDING_N:` blocks; `dispatch-with-waterfall.sh` only accepts `STATUS=OK` when `grep -Eq` matches `^[[:space:]]*### FINDING_[0-9]` (scripts/dispatch-with-waterfall.sh:278-287). Attestation-only outputs fail every phase → `DISPATCH_OK=false` → `REASON=dispatch-failed`. `review-core.sh` only stalls on `validation-exhausted` (514-559), so `/implement` Step 5 continues voting on unmerged `findings.md` instead of `aggregator-validation-exhausted`.
- **Proposed resolution**: Extend the planned pattern to also accept the attestation line (e.g. `'^[[:space:]]*(### FINDING_[0-9]|LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED)'`), document it in `aggregate-findings.md`, and add a harness case where stub/real dispatch returns attestation-only output and stdout is `REASON=validation-exhausted` (not `dispatch-failed`).

### FINDING_6:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review/scripts/test-aggregate-findings.sh:1082-1112
- **Concern**: Plan omits preamble narrow-trigger REASON rewrites. Scenario: `preamble_contradiction` and `numbered_prose_contradiction` stubs emit attestation plus narrow-trigger stderr (`AGGREGATOR_VALIDATION_FAILED=preamble_finding_substring`) but tests still expect `REASON=validation-failed` with `LARCH_AGGREGATE_MAX_OUTER_PHASES=1`. After collapse, `MERGE_PIPELINE_RC=1` must map to `validation-exhausted` per plan step 4.
- **Proposed resolution**: Tests fail or ship wrong contract if only the `zero_findings*` cases listed in the plan are updated. Add these two cases to the plan’s expected-REASON table (→ `validation-exhausted`) and drop the `LARCH_AGGREGATE_MAX_OUTER_PHASES` lines.

### FINDING_7:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/review/scripts/test-aggregate-findings.sh:1114-1202
- **Concern**: Outer-waterfall harness cases not scoped for removal/rewrite. Scenario: `waterfall_exhausted`, `waterfall_recover_on_phase2`, `zero_findings_input_nonempty progresses outer waterfall (#2782)`, and `waterfall_skip_unavailable_external` depend on multi-outer-phase iteration, `PHASES_ATTEMPTED`, and `aggregator-output-{codex,claude}.txt`. Plan only lists ~10 `LARCH_AGGREGATE_MAX_OUTER_PHASES` edits and two new tests.
- **Proposed resolution**: `make test-aggregate-findings` fails or retains false confidence in removed behavior if these blocks remain unchanged. Explicitly delete or rewrite each waterfall_ctr case: exhaustion → single-dispatch `validation-exhausted`; #2782 recovery → dispatcher phase-2 success test (see next finding); drop `PHASES_ATTEMPTED` and per-outer output path assertions.

### FINDING_8:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review/scripts/test-aggregate-findings.sh:1162-1180
- **Concern**: #2782 cross-outer recovery not replaced at dispatcher layer. Scenario: `zero_findings_waterfall_ctr` simulates Cursor empty-merge then Codex success via outer-loop counter increments across multiple `AGGREGATE_DISPATCH_SH` invocations. Collapse allows one dispatch call; stub counter cannot advance across removed outer iterations.
- **Proposed resolution**: Regression in “empty-merge slip then sibling tool succeeds” unless covered elsewhere; production relies on dispatcher phase-2, not aggregate outer retry. Add a planned test (real `dispatch-with-waterfall.sh` stubs or multi-phase stub) asserting phase-1 narration/attestation-only failure and phase-2 structured `### FINDING_1:` → `REASON=ok` / `AGGREGATED=true`, replacing the deleted #2782 case.

### FINDING_9:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/review/scripts/test-aggregate-findings.sh:24-52
- **Concern**: Stub dispatch ignores `--require-result-pattern`. Scenario: `write_stub_dispatch` drops unknown flags (`*) shift 1`) and never records `--require-result-pattern`. A regression that omits the flag on `$DISPATCH_SH` still passes all stub-based cases.
- **Proposed resolution**: #2881 root fix (pattern-gated narration) is untested in the default harness path; only the optional real-dispatcher case would catch it. Require `test_dispatcher_pattern_gate_*` to grep `aggregator-dispatch.stderr` or a wf log for `--require-result-pattern`, or teach the stub to fail when the flag is absent; mirror `test-decompose-aggregator.sh:86-87`.

### FINDING_10:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/dispatch-with-waterfall.sh:275-278
- **Concern**: `STATUS=cap_hit` bypasses pattern gate. Scenario: Under `--require-result-pattern`, only `STATUS=OK` is content-checked; `cap_hit` is terminal (dispatch-with-waterfall.sh:275-278). Aggregator `cap_hit` output without a FINDING heading can become the candidate and fail python validation as `validation-failed`, not `validation-exhausted`.
- **Proposed resolution**: Step 5 continues with unmerged findings (same as today for `validation-failed`) but without the stall path operators may expect after “all tools degraded.” Document in plan Edge cases; optional follow-up: treat aggregator `cap_hit` without pattern match like a pattern failure at the dispatcher.

### FINDING_11:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review/scripts/test-aggregate-findings.sh:217-231
- **Concern**: Test-case mapping in the plan misclassifies existing zero-findings fixtures. Scenario: The plan says zero_findings_prose_finding_ids is a preamble-trigger MERGE_PIPELINE_RC=1 case and zero_findings_padded_attest_rejected is an RC=2 case, but current validator treats FINDING_ids prose as missing-attestation validation-failed and trims padded attestation into empty_merge_from_nonempty_input. Updating expectations as written will either fail the harness or push an unintended validator behavior change.
- **Proposed resolution**: Revise the test rewrite matrix: zero_findings_prose_finding_ids should remain REASON=validation-failed; zero_findings_padded_attest_rejected should expect REASON=validation-exhausted under the new RC=1 mapping.

### FINDING_12:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/dispatch-with-waterfall.sh:155-164
- **Concern**: The plan's new pattern-gate positive test describes an impossible phase order for a Codex-primary slot. Scenario: With slot tool=codex, dispatch order is Codex phase1 then Cursor phase2 then Claude phase3 when both externals are present; Cursor primary then Codex phase2 only happens for a cursor-primary slot, which the proposed aggregate-findings change explicitly removes. A test named dispatcher_pattern_gate_routes_narration_to_phase2 using Cursor primary and Codex phase2 would not exercise the aggregate-findings contract.
- **Proposed resolution**: Change the aggregate test to simulate Codex primary narration-only and Cursor phase2 valid output, or Codex absent with Cursor narration-only and Claude phase3 valid output. Keep Cursor-primary/Codex-phase2 coverage only in dispatcher-level tests.

### FINDING_13:
- **Reviewer(s)**: Codex-Edge
- **Severity**: latent
- **Focus area**: architecture
- **Location**: scripts/dispatch-with-waterfall.sh:155-164
- **Concern**: The docs update instruction says the candidate path is uniformly aggregator-output.txt, conflicting with dispatcher fallback paths. Scenario: On phase2 or phase3 fallback, dispatch-with-waterfall rewrites the output path to aggregator-output-phase2.txt or aggregator-output-phase3.txt. If an implementer follows the uniform-path wording, aggregate-findings can validate stale primary narration from aggregator-output.txt instead of the dispatcher-resolved fallback ballot.
- **Proposed resolution**: Reword docs and plan text to say the slot base output is aggregator-output.txt, but the resolved candidate must come from ALL_OUTPUT_FILES_PATH and may be aggregator-output-phase2.txt or aggregator-output-phase3.txt.

### FINDING_14:
- **Reviewer(s)**: Cursor-Innovation, Cursor-dyn-key-removal-survey
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review/scripts/test-aggregate-findings.sh:217-223
- **Concern**: Plan maps zero_findings_prose_finding_ids to validation-exhausted as a narrow-trigger case. Scenario: Stub output uses ### FINDING_ids (no digit); validator takes the missing-attestation path (MERGE_PIPELINE_RC=2), not preamble_finding_substring — harness at :665-679 expects validation-failed and explicitly denies preamble token
- **Proposed resolution**: Keep REASON=validation-failed for zero_findings_prose_finding_ids; remove it from the narrow-trigger → validation-exhausted bucket in plan step 2

### FINDING_15:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:16,54; scripts/dispatch-with-waterfall.sh:326-332
- **Concern**: Finding 1 - Proposed pattern-gate test contradicts the Codex-primary slot design. Scenario: A faithful aggregate-findings dispatch row uses tool=codex, so dispatcher phase 2 is Cursor, not Codex; the proposed Cursor-primary narration then Codex phase-2 test either forces the wrong slot tool or stubs around the real contract
- **Proposed resolution**: Rewrite the positive test around tool=codex: Codex primary narration/no heading falls to Cursor valid output; add a separate Codex-fails then Cursor-narration then Claude-valid case if the original Cursor narration failure must be covered

### FINDING_16:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:48-51; skills/review/scripts/test-aggregate-findings.sh:217-223,1217-1220; skills/review/scripts/aggregate-findings.sh:257-262
- **Concern**: Finding 2 - Plan misclassifies zero_findings_prose_finding_ids as a narrow-trigger preamble failure. Scenario: The existing stub emits ### FINDING_ids, and the validator explicitly documents that non-numeric FINDING_ids should not trip preamble_finding_substring; changing this case to validation-exhausted conflicts with the plan's preserve-validator instruction and current regression assertion
- **Proposed resolution**: Keep zero_findings_prose_finding_ids on REASON=validation-failed; use numbered_prose_contradiction or preamble_contradiction for the new validation-exhausted narrow-trigger assertion

### FINDING_17:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: latent
- **Focus area**: security
- **Location**: plan.txt:16,37,88; skills/review/scripts/aggregate-findings.sh:187-189,246,298-302
- **Concern**: Finding 3 - require-result-pattern is weaker than the validator's real structured-heading contract. Scenario: ^[[:space:]]*### FINDING_[0-9] accepts pseudo-headings like ### FINDING_1 not-a-valid-heading-line, so a narration payload with an invalid heading marker can pass dispatcher gating and then fail validation without trying fallback tools
- **Proposed resolution**: Use the validator-equivalent gate ^[[:space:]]*### FINDING_[0-9]+: and add a pattern-gate regression for nonconforming pseudo-headings routing to fallback instead of becoming the final candidate

### FINDING_18:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: nit
- **Focus area**: architecture
- **Location**: plan.txt:40-41,63-65; skills/review/scripts/review-core.md:60-63; skills/review-and-fix/scripts/review-and-fix.sh:1212-1214
- **Concern**: Finding 4 - Adjacent downstream docs and operator breadcrumb still name removed outer phases. Scenario: The plan updates aggregate-findings.md and SECURITY.md, but review-core.md will still list aggregator-output-codex.txt/aggregator-output-claude.txt as per-outer-phase captures and review-and-fix will still warn exhausted all outer phases
- **Proposed resolution**: Update review-core.md artifact prose and the review-and-fix breadcrumb to describe dispatcher-owned fallback / validator exhaustion; optionally remove PHASES_ATTEMPTED from the review-core test stub to avoid preserving stale contract shape

### FINDING_19:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review/scripts/test-aggregate-findings.sh:179-186,217-224,562-679
- **Concern**: Plan remaps narrow-trigger stubs to REASON=validation-exhausted but those fixtures lack any line matching ^[[:space:]]*### FINDING_[0-9]. Scenario: After --require-result-pattern dispatch never settles DISPATCH_OK=true on attestation-only/narration stubs; aggregate exits REASON=dispatch-failed before aggregate-validate.py runs, so tests expecting validation-exhausted fail and review-core never hits aggregator-validation-exhausted
- **Proposed resolution**: Add a plan step to retune narrow-trigger stub payloads (e.g. a non-block pseudo heading line like zero_findings_nonconforming_heading) so the pattern gate passes, then keep MERGE_PIPELINE_RC=1 mapping; or explicitly document dispatch-failed as the new terminal state and extend review-core stall logic

### FINDING_20:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/dispatch-with-waterfall.sh:275-288; agents/orchestrator-aggregator.md:45-55; skills/review/scripts/aggregate-findings.sh:655-658
- **Concern**: The proposed result gate only accepts files with a numeric ### FINDING heading, but the plan still expects zero-finding/narrow-trigger outputs to reach aggregate-validate.py and map to REASON=validation-exhausted.. Scenario: If every dispatcher phase returns the documented empty-merge attestation with no structured finding, --require-result-pattern rejects each result before aggregate-findings.sh can run the validator; aggregate-findings emits dispatch-failed instead of validation-exhausted, so review-core.sh never takes its aggregator-validation-exhausted branch.
- **Proposed resolution**: Decide which layer owns zero-heading outputs: either broaden the gate to admit the exact LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED terminal form and any validator-owned narrow-trigger forms, or update the plan/docs/tests so pattern misses are dispatch-failed. Add the narrow-trigger test through the real dispatcher, not only an AGGREGATE_DISPATCH_SH stub that can bypass the gate.

### FINDING_21:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review/scripts/test-aggregate-findings.sh:665-679
- **Concern**: Plan maps zero_findings_prose_finding_ids to REASON=validation-exhausted but that stub lacks attestation and does not emit AGGREGATOR_VALIDATION_FAILED=preamble_finding_substring or empty_merge_from_nonempty_input (MERGE_PIPELINE_RC=2). Scenario: Conflicts with the existing empty_merge_negative_finding_prose case at 1204-1220 which must stay validation-failed; implementing the plan would break one of the two tests
- **Proposed resolution**: Keep zero_findings_prose_finding_ids on REASON=validation-failed; only remap kinds that actually produce MERGE_PIPELINE_RC=1 (zero_findings, preamble_contradiction, numbered_prose_contradiction)

### FINDING_22:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review/scripts/test-aggregate-findings.sh:planned; scripts/test-dispatch-with-waterfall.sh:302-323
- **Concern**: Planned pattern-gate regression test contradicts the Codex-primary aggregate design. Scenario: The plan says aggregate-findings.sh will always build one slot with tool=codex, but the proposed test simulates Cursor primary returning narration and Codex phase-2 succeeding, which only exercises a cursor-primary dispatcher slot and would not validate the aggregate-findings.sh contract
- **Proposed resolution**: Rewrite the test to exercise aggregate-findings.sh with a codex-primary slot: for both-tools-present use Codex narration then Cursor phase-2 success, and add a separate Codex-absent or Codex-failed case where Cursor narration falls through to Claude if the original Cursor narration failure mode must be covered

### FINDING_23:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: security
- **Location**: SECURITY.md:81
- **Concern**: The SECURITY.md replacement is too narrow and would drop unchanged empty-merge fail-closed invariants. Scenario: The current security paragraph documents zero-output, missing-attestation, spurious-attestation, and near-token attestation handling; the plan says to replace it wholesale with only the new dispatcher collapse behavior, so security docs would lose validation constraints that still remain load-bearing after the PR
- **Proposed resolution**: Revise the SECURITY.md plan to update the waterfall and validation-exhausted wording while explicitly preserving the existing empty-merge attestation, zero-output fail-closed, spurious token, and near-token rejection guarantees

### FINDING_24:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/review/scripts/aggregate-findings.md:26; scripts/dispatch-with-waterfall.sh:309-338
- **Concern**: The planned docs describe Codex-absent fallback with the wrong dispatcher phase. Scenario: The plan says that when Codex is absent, phase 1 launches Cursor, but dispatch-with-waterfall queues an unavailable codex-primary slot from phase 1 and launches Cursor in phase 2; docs or tests that assert phase-1 Cursor paths will drift from runtime behavior
- **Proposed resolution**: Update the proposed aggregate-findings.md and SECURITY.md wording to avoid incorrect phase numbering, or state that a codex-primary slot with Codex absent resolves through phase 2 Cursor and then phase 3 Claude

### FINDING_25:
- **Reviewer(s)**: Cursor-dyn-test-fixture-sync
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:48-50
- **Concern**: skills/review/scripts/test-aggregate-findings.sh:665-679,1204-1221. Scenario: Plan maps `AGGREGATE_STUB_MERGE_KIND=zero_findings_prose_finding_ids` to `REASON=validation-exhausted` as a narrow-trigger case
- **Proposed resolution**: That stub has no attestation and `### FINDING_ids` prose explicitly does not emit `preamble_finding_substring` (tests assert missing-attestation diagnostic and `REASON=validation-failed`); remapping would break two regression cases and weaken the negative-control for preamble detection Keep `zero_findings_prose_finding_ids` on `REASON=validation-failed`; only remap kinds that actually produce `MERGE_PIPELINE_RC=1` (`zero_findings`, `preamble_contradiction`, `numbered_prose_contradiction`)

### FINDING_26:
- **Reviewer(s)**: Codex-dyn-test-fixture-sync
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:16,54; scripts/dispatch-with-waterfall.sh:311-332
- **Concern**: The new pattern-gate positive case describes Cursor as primary and Codex as phase 2, but the proposed aggregate slot is tool=codex, so dispatcher phase 1 is Codex and phase 2 is Cursor when both tools are present. Scenario: An implementation can satisfy this with an artificial AGGREGATE_DISPATCH_SH stub that writes Codex output directly while aggregate-findings.sh never proves it passed --require-result-pattern or followed the real dispatcher fallback order
- **Proposed resolution**: Rewrite the test to run the real dispatch-with-waterfall under PATH stubs with codex-primary order: Codex narration/no heading routes to Cursor phase 2 valid output; if specifically testing Cursor narration, make Codex fail first, Cursor narration fail phase 2, and Claude succeed in phase 3; assert ALL_OUTPUT_TOOLS and PHASE*_SLOTS

### FINDING_27:
- **Reviewer(s)**: Codex-dyn-test-fixture-sync
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: <TMPDIR>/plan.txt:45-55,79,87; skills/review/scripts/test-aggregate-findings.sh:24-56; skills/design/scripts/decompose-aggregator.sh:127-142
- **Concern**: The concrete test rewrite still allows AGGREGATE_DISPATCH_SH stubs to rely on ALL_OUTPUT_FILES fallback instead of mandating ALL_OUTPUT_FILES_PATH sidecar emission. Scenario: Candidate resolution bugs in the new ALL_OUTPUT_FILES_PATH branch can pass tests by falling back to the old lossy ALL_OUTPUT_FILES key, unlike the decompose-aggregator reference pattern
- **Proposed resolution**: Make the stub update mandatory: write a paths sidecar whose first line is the candidate, emit ALL_OUTPUT_FILES_PATH plus ALL_OUTPUT_FILES, and add at least one aggregate-findings assertion that resolution used the sidecar; keep fallback coverage as a separate compatibility case

### FINDING_28:
- **Reviewer(s)**: Codex-dyn-key-removal-survey
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/review/scripts/review-core.md:60-63
- **Concern**: Plan misses review-core.md artifact contract that still lists aggregator-output-codex.txt and aggregator-output-claude.txt as per-outer-phase captures. Scenario: After the collapse, operators following review-core.md will look for removed per-tool output files and infer the aggregator still has an outer-phase contract
- **Proposed resolution**: Add review-core.md to the plan and replace the artifact bullet with aggregator-output.txt plus aggregator-dispatch.env, aggregator-dispatch.stderr, and review-core-aggregate.env as appropriate

### FINDING_29:
- **Reviewer(s)**: Codex-dyn-key-removal-survey
- **Severity**: nit
- **Focus area**: risk-integration
- **Location**: skills/review-and-fix/scripts/review-and-fix.sh:1212-1214
- **Concern**: Runtime breadcrumb still says validation exhausted means all outer phases. Scenario: After the collapse, validation-exhausted is a single post-dispatch narrow-trigger validator outcome, so the warning misdiagnoses failures during real review-and-fix runs
- **Proposed resolution**: Add this file to the plan and change the breadcrumb to describe narrow-trigger aggregator validation exhaustion without all outer phases

### FINDING_30:
- **Reviewer(s)**: Codex-dyn-key-removal-survey
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/review/scripts/test-review-core.sh:318-321
- **Concern**: Test stub still emits removed PHASES_ATTEMPTED stdout key. Scenario: The plan removes PHASES_ATTEMPTED from aggregate-findings.sh and aggregate-findings.md, but this sibling test keeps an impossible post-collapse stdout shape and weakens the consumer-survey claim
- **Proposed resolution**: Drop PHASES_ATTEMPTED from aggregate-exhausted-stub.sh and keep the validation-exhausted status assertion focused on REASON

### FINDING_31:
- **Reviewer(s)**: Cursor-dyn-pattern-gate-parity
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:16-17; agents/orchestrator-aggregator.md:45-59; scripts/dispatch-with-waterfall.sh:278-288
- **Concern**: --require-result-pattern requires a ### FINDING_[0-9] line but valid empty-merge output is attestation-only. Scenario: When every waterfall phase returns only narrative plus LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED (orchestrator contract for duplicate-only merges), grep -Eq never matches, DISPATCH_OK=false, aggregate-findings emits REASON=dispatch-failed and review-core continues voting instead of REASON=validation-exhausted exit 2
- **Proposed resolution**: Extend the ERE to accept structured findings OR a full-line attestation (e.g. alternation with ^[[:space:]]*LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED[[:space:]]*$); document the dual gate in aggregate-findings.md

### FINDING_32:
- **Reviewer(s)**: Codex-dyn-pattern-gate-parity
- **Severity**: latent
- **Focus area**: correctness
- **Location**: plan.txt:16,88; agents/orchestrator-aggregator.md:27-29; skills/review/scripts/aggregate-findings.sh:96-100,182-189,292-295; scripts/dispatch-with-waterfall.sh:278-286
- **Concern**: Pattern gate permits leading whitespace before ### but the aggregator template and existing FINDING counters/parsers do not. Scenario: The dispatcher uses grep -E, so ^[[:space:]]*### FINDING_[0-9] will accept an indented heading; aggregate-findings then treats that same candidate as zero structured output because count_finding_blocks and output_blocks require ^### FINDING_, producing validation-exhausted instead of dispatcher fallback. The [0-9] piece is not single-digit-only for FINDING_10 because it matches the first digit prefix, and BRE vs ERE does not change that part.
- **Proposed resolution**: Align the gate with the actual aggregator contract by using ^### FINDING_[0-9], or deliberately broaden count_finding_blocks and the Python block parser to accept the same leading whitespace; add a parity regression for an indented ### FINDING_1: candidate.

