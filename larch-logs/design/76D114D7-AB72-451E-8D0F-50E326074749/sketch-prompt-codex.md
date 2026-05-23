Propose a high-level implementation approach for this feature: 

## Feature (Issue #2638)

**Bug**: In an `/implement --merge` Step 5 review round, the Cursor aggregator (`skills/review/scripts/aggregate-findings.sh`) produced a self-contradicting output: a preamble paragraph claiming "We have multiple `### FINDING_N:` blocks" followed by zero structural FINDING blocks and the empty-merge attestation token `LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED`. The current repair pass (embedded `aggregate-validate.py --repair-attestation`) only checks for drifted pseudo-headings (`### FINDING_X` regex); it does NOT detect prose that semantically claims findings exist when zero structural blocks were emitted. The 28 input findings were structurally clean and well-formed; the aggregator alone failed. Voting tallied zero findings, scout reported `validation-failed`, and the wrapper stalled with `STALL_REASON=round-failed-complete`. At least one finding lost contained a real envelope-aware-retry bug (acceptance criterion #3 of the issue under review).

**Chosen design direction (from discussion round 1, user-confirmed)**:

1. Extend the existing `dispatch-with-waterfall.sh` waterfall (Cursor → Codex → Claude) so that **semantic validation failure** (any `aggregate-validate.py` non-zero exit), not just launch/collection failure, triggers progression to the next phase. The waterfall already exists for launch failures; this extends the trigger surface.

2. Add a new validator check: when output has zero `### FINDING_` blocks AND output text contains the substring `### FINDING_` (raw bytes anywhere, not just heading position), reject as `validation-failed`. This catches the contradiction case where prose claims findings exist but no structural blocks were emitted.

3. The per-phase retry loop lives **inside `aggregate-findings.sh`** (NOT inside `dispatch-with-waterfall.sh`). The script builds a single-tool slot manifest per phase, calls `dispatch-with-waterfall.sh` once per phase with that manifest, validates after each, stops on first success. `dispatch-with-waterfall.sh` is unchanged.

4. After all 3 phases fail validation, exit with a distinct token. The downstream wrapper (`skills/review-and-fix/scripts/review-implement-step5-loop.sh`) routes this token to `STALL_REASON=aggregator-validation-exhausted`. `/implement` SKILL.md Step 5 stall-reason table gets a new row.

5. Add a new stdout KV `PHASES_ATTEMPTED=<comma-list>` (e.g. `PHASES_ATTEMPTED=cursor,codex`) so operators see how far the waterfall got.

6. Regression test: add new `AGGREGATE_STUB_MERGE_KIND` values in `skills/review/scripts/test-aggregate-findings.sh` that emit short preambles like "We have FINDING_N blocks" followed by zero structural blocks. Test assertions: (a) substring detection rejects degenerate output, (b) waterfall progresses through all 3 phases on consecutive validation failures, (c) exhausted-waterfall path emits the new IRF token.

**Hard constraints**: existing test cases at `test-aggregate-findings.sh` (zero_findings_no_attest #2563, zero_findings_impure_attest, zero_findings_nonconforming_heading, empty_merge_existing_token_passthrough, etc.) must continue to pass. `LARCH_AGGREGATOR_DISABLED=1` must remain a no-op. The existing stdout contract (AGGREGATED, INPUT_COUNT, MERGED_COUNT, REASON, FAILURE_LOG) is unchanged; PHASES_ATTEMPTED is additive. `collect-findings.sh` is unchanged (the bug was in the aggregator, not in reviewer-output collection).

**Non-goals**: no re-prompt-with-stricter-instructions retry (Option 1 in the issue body) — phase progression just swaps the model. No carry-through fallback (Option 3 in the issue body). No main-agent inline aggregation. No escape-hatch env var. No refactor of `dispatch-with-waterfall.sh`.

## Task

Explore the codebase. Write 2-3 paragraphs covering: (1) Key architectural decisions and approach, (2) Which files/modules to modify and why, (3) Main tradeoffs and risks. Do NOT modify files.
