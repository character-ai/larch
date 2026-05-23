### FINDING_1: Per-phase output filename mismatch with output_for_phase
- **Reviewer(s)**: Cursor-Arch, Cursor-Edge, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Codex-Arch, Codex-Innovation, Codex-Pragmatic, Codex-Requirements
- **Concern**: Plan §1/§8 names per-phase output files `aggregator-output.txt.phase1` / `.phase2` / `.phase3` and claims they match `output_for_phase` in `scripts/dispatch-with-waterfall.sh:125-134`. Actual `output_for_phase` produces: phase1 = `aggregator-output.txt` (the base path unchanged), phase2 = `aggregator-output-phase2.txt`, phase3 = `aggregator-output-phase3.txt`. Tests and aggregate-findings.md asserting `.phaseN` suffix would fail.
- **Proposed resolution**: Align plan, tests, and aggregate-findings.md with the dispatcher's actual naming (`aggregator-output.txt`, `aggregator-output-phase2.txt`, `aggregator-output-phase3.txt`). Drive candidate selection from the dispatcher's emitted `ALL_OUTPUT_FILES` rather than constructing filenames in the aggregator.


### FINDING_10: Missing test for final Step 5 wrapper stall reason
- **Reviewer(s)**: Codex-Requirements
- **Concern**: Plan §6 modifies `review-implement-step5-loop.sh` to emit `STALL_REASON=aggregator-validation-exhausted`, but no harness case asserts this end-to-end.
- **Proposed resolution**: Add a loop-mode review-and-fix or run-step5-review harness case stubbing `REVIEW_CORE_STATUS=aggregator-validation-exhausted` and asserting rc=2, `STEP5_REVIEW_STATUS=stall`, `STALL_REASON=aggregator-validation-exhausted`.


### FINDING_11: Stub counter $TMP scoping risk
- **Reviewer(s)**: Codex-Arch
- **Concern**: Plan §8 proposes a per-call counter file at `$TMP/aggregate-stub-call-count` inside the generated stub. `TMP` is a test-harness local; if not exported into the stub's subshell environment, the counter path would resolve to a different location under `set -u`.
- **Proposed resolution**: Either `export TMP` before invoking the stub, derive the counter path inside the stub via `$(dirname "$0")`, or bake the absolute counter path into the generated stub via heredoc substitution.


### FINDING_12: Trigger-rule contradiction with existing test contracts
- **Reviewer(s)**: Codex-Innovation, Codex-Pragmatic
- **Concern**: Plan says (a) "any aggregate-validate.py non-zero exit triggers waterfall progression" AND (b) "existing tests like zero_findings_no_attest, zero_findings_impure_attest, zero_findings_nonconforming_heading must continue to pass unchanged." But several of those existing tests assert `REASON=validation-failed` after a single-call stub — under (a), the same path would now progress through 3 phases and terminate with `REASON=validation-exhausted`. The two rules conflict.
- **Proposed resolution**: Choose either: (a) narrow the waterfall trigger to ONLY the new "zero blocks + `### FINDING_` substring" rejection (smallest scope, all existing tests pass unchanged), OR (b) keep the broad trigger and update every existing `REASON=validation-failed` fixture to be either single-phase-capped or expect `REASON=validation-exhausted`. Prefer (a) for minimal scope; the discussion-round1.md "any non-zero exit" choice should be revisited in light of this collision.


### FINDING_13: append_warning fires on recoverable phase failures
- **Reviewer(s)**: Codex-Innovation
- **Concern**: The existing failure branches inside aggregate-findings.sh (dispatch-failed, validation-failed, strip-failed, empty-merge) all call `append_warning(...)` to write entries into execution-issues.md. If the loop wraps these branches without modification, each recoverable phase failure (phase 1 fails → phase 2 succeeds) would still log a warning, polluting execution-issues.md.
- **Proposed resolution**: Refactor the dispatch+repair+validate block into an internal helper that returns phase status (success/failure + REASON code) without calling `append_warning`. Only call `append_warning` on the OUTER loop's terminal failure (validation-exhausted), passing a single consolidated warning that names which phases were attempted.


### FINDING_14: Substring rule is too broad — could false-positive on negative prose
- **Reviewer(s)**: Codex-Requirements
- **Concern**: The rule "zero blocks + `### FINDING_` substring anywhere in output" could false-positive on legitimate empty-merge prose like "no `### FINDING_` blocks were emitted because all inputs were dupes" or backticked references mentioning the heading. The intent is to catch contradictory preambles claiming findings exist; the heuristic is structurally broader than the intent.
- **Proposed resolution**: Add a regression fixture for genuine empty-merge prose that mentions `### FINDING_` negatively (e.g., backticked, or with words like "no", "without", "absent"). Either accept the false-positive cost (operator can rephrase) and document the rule's breadth, or add a polarity-aware exception. Smallest viable mitigation: require the `### FINDING_` substring to appear OUTSIDE backtick spans (raw text only).

## Out-of-Scope Observations


### FINDING_2: review-core.sh short-circuit must exit 2, not 0, and mirror full panel-failed envelope
- **Reviewer(s)**: Cursor-Arch (twice), Cursor-Edge, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Concern**: Plan §4 snippet uses `exit 0` and emits a partial KV set. The existing `panel-failed` branch at `review-core.sh:386-429` exits 2, runs `emit_tally_with_failure_isolation`, `flush_round_log`, `copy_to_parent`, and emits a broader KV set (OUT_OF_SCOPE_DRIFT_COUNT, FINDINGS_FILE, ACCEPTED_FINDINGS_FILE, REJECTED_FINDINGS_FILE, PANEL_MODE, PANEL_SHAPE, THRESHOLD_REASON). `test-review-core.sh` (line 427-434) asserts rc=2 on panel-failed. The plan's `exit 0` would diverge from established voting-abort semantics.
- **Proposed resolution**: Mirror the full panel-failed isolation block: run `emit_tally_with_failure_isolation` with a distinct failure label `aggregator-validation-exhausted`, `flush_round_log`, `copy_to_parent`, emit the broader KV set, and `exit 2`. Update plan §4 snippet accordingly.


### FINDING_3: Test fixture REASON expectation conflicts with waterfall semantics
- **Reviewer(s)**: Cursor-Arch (twice), Cursor-Edge (twice), Cursor-Innovation, Cursor-Pragmatic, Codex-Arch, Codex-Edge, Codex-Pragmatic
- **Concern**: Plan §8 says `zero_findings_preamble_contradiction` (single-call) expects `REASON=validation-failed`. The waterfall rule (any validation failure triggers retry through all 3 phases) means a single-call invocation that fails phase 1 would advance to phase 2 and phase 3, ending with `REASON=validation-exhausted` — not `validation-failed`. Either the test must be explicitly scoped to single-phase (e.g., by setting a `LARCH_AGGREGATOR_PHASE_CAP=1` env var, or by stub-returning success on phase 2+), OR the assertion must be `REASON=validation-exhausted`.
- **Proposed resolution**: Two-test split — keep `zero_findings_preamble_contradiction` as a focused unit test against the validator only (via a separate `aggregate-validate.py` direct-invocation helper, or by setting stub success on phase 2 so the substring rejection IS the first-phase signal), and let `waterfall_exhausted` cover the full 3-phase exhaust path. Document the test boundary explicitly.


### FINDING_4: SECURITY.md missing from file modifications
- **Reviewer(s)**: Cursor-Arch (twice), Codex-Requirements
- **Concern**: AGENTS.md explicitly says "Update SECURITY.md when security-relevant behavior changes." The change introduces validation-driven multi-tool retries against potentially adversarial vendor output — security-relevant per the existing SECURITY.md §"Pre-vote findings aggregation" section (lines 64-65).
- **Proposed resolution**: Add `SECURITY.md` to the file list. Refresh the §"Pre-vote findings aggregation" bullet to document the validation-driven Cursor → Codex → Claude retry, per-phase artifacts, and the validation-exhausted stall.


### FINDING_5: review-core.md sibling doc missing from file list
- **Reviewer(s)**: Cursor-Arch (twice), Codex-Requirements
- **Concern**: `.claude/rules/script-md-siblings.md` requires each `.sh` script to have an updated sibling `.md`. The plan touches `review-core.sh` (new short-circuit) but does not list `review-core.md` for update. Operator/subagent docs will drift.
- **Proposed resolution**: Add `skills/review/scripts/review-core.md` to the file list. Update the sibling's normative behavior section to document the new `REVIEW_CORE_STATUS=aggregator-validation-exhausted` short-circuit.


### FINDING_6: emit_result should be the documented extension point for new stdout KVs
- **Reviewer(s)**: Cursor-Arch (twice), Cursor-Pragmatic
- **Concern**: `aggregate-findings.sh` lines 104-112 centralize stdout emission in a single `emit_result()` function (with consistent KV ordering per lib-quiet conventions). Plan §1 describes adding `PHASES_ATTEMPTED` but doesn't say to extend `emit_result`. Ad-hoc `emit_kv PHASES_ATTEMPTED` calls outside `emit_result` could break ordering invariants tested by harness assertions.
- **Proposed resolution**: Extend `emit_result()` to optionally emit `PHASES_ATTEMPTED` (when non-empty) and the new `REASON=validation-exhausted` value. Document `emit_result` as the single stdout-extension locus in aggregate-findings.md.


### FINDING_7: Presence-flag manipulation lies to dispatcher about tool availability
- **Reviewer(s)**: Codex-Arch, Codex-Innovation
- **Concern**: Plan §1 forces `--cursor-present true --codex-present false` etc. per outer phase. This overrides truthful availability passed by review-core (CODEX_AVAILABLE/CURSOR_AVAILABLE). When the outer Phase 2 (Codex) runs but Codex is actually unavailable, the dispatcher's internal waterfall will silently fall through to its Phase 3 Claude — so the outer Phase 3 (Claude) becomes a redundant Claude run. The outer loop's accounting then mislabels "Phase 2 attempted = codex" when it was really Claude.
- **Proposed resolution**: Build the outer phase list from truthful availability (CODEX_AVAILABLE/CURSOR_AVAILABLE passed into aggregate-findings.sh). Skip a phase when its tool is unavailable. Inspect `ALL_OUTPUT_TOOLS` after each dispatch to detect internal fallback; treat an unexpected fallback as a failed outer phase (since the intended tool didn't actually run). Optionally add a `--no-fallback` / `--force-tool` flag to dispatch-with-waterfall.sh as a clean alternative, but the inspection-based approach avoids touching the shared dispatcher.


### FINDING_8: Substring guard should also block repair-stage synthesis, not just validation
- **Reviewer(s)**: Codex-Requirements
- **Concern**: Plan §3 adds the new `### FINDING_` substring check to `main()` (validation). But `_attempt_attestation_repair` synthesizes the attestation BEFORE main validation runs on the repaired output. If repair synthesizes attestation on the bug pattern, validation passes (zero blocks + attestation = OK), then strip removes the attestation and findings.md gets the preamble narrative — destroying findings. The substring check must run in `_attempt_attestation_repair` to suppress synthesis on contradictory output, mirroring the existing `has_nonconforming_finding_heading_markers` suppression logic.
- **Proposed resolution**: Add the same substring check inside `_attempt_attestation_repair` BEFORE the synthesis branch. When triggered, emit `AGGREGATOR_SYNTHESIS_SUPPRESSED=preamble_finding_substring` to `aggregator-repair.stderr` (parallel to the existing `nonconforming_finding_heading_markers` suppression).


### FINDING_9: Missing test-review-core.sh case for the new short-circuit
- **Reviewer(s)**: Codex-Requirements
- **Concern**: Plan §4 modifies `review-core.sh` to short-circuit on `REASON=validation-exhausted`, but plan §8/§9 doesn't list a `test-review-core.sh` case. Without it, the short-circuit is untested.
- **Proposed resolution**: Add a `test-review-core.sh` case that stubs `aggregate-findings.sh` to emit `REASON=validation-exhausted`. Assert `REVIEW_CORE_STATUS=aggregator-validation-exhausted`, voter dispatch is NOT invoked, and exit code matches the panel-failed contract (rc=2).


