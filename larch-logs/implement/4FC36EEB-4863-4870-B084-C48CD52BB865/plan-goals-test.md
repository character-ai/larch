## Goal
Add script-side attestation synthesis pre-pass in aggregate-findings.sh to deterministically recover when the aggregator model omits the empty-merge attestation token, preventing spurious 'merged output failed validation' execution-issue warnings.

## Implementation Plan
## Plan

### Files / globs to touch

1. `agents/orchestrator-aggregator.md` — strengthen the empty-merge
   attestation directive (lines ~40–42).
2. `skills/review/scripts/aggregate-findings.sh` — add an
   `_attempt_attestation_repair` Python helper invoked between the
   `dispatch-with-waterfall.sh` raw output and the existing validate
   block (around line 480, before the `_validate_output` invocation).
3. `skills/review/scripts/test-aggregate-findings.sh` — add two
   regression cases pinning the new behavior.
4. `skills/review/scripts/aggregate-findings.md` — document the
   synthesis pre-pass in the runtime contract section that introduced
   the empty-merge attestation prose (search anchor: `Empty-merge
   attestation (runtime contract)`).

### Sequenced steps

1. **Prompt hardening (orchestrator-aggregator.md)**.
   Rewrite the empty-merge attestation paragraph (lines ~40) as a
   numbered checklist with one literal-formatted example block. The
   example block shows the token alone on its own line at the end of
   the file, optionally preceded by one paragraph of narrative. Keep
   the existing non-empty exclusion rule (line ~42) unchanged. Verify
   reachable links: the change is prompt-only; no other agent file
   pulls from this template.

2. **Script-side synthesis pre-pass (aggregate-findings.sh)**.
   Add a Python `_attempt_attestation_repair(raw_text, input_text)`
   function near the existing `EMPTY_MERGE_ATTESTATION = "..."` constant
   (line 289). The helper:
   - Counts merged FINDING blocks in `raw_text` (reuse the existing
     `count_finding_blocks` / `blocks` paths).
   - Counts structured input slots (reuse `input_slot_set` /
     `input_blocks_by_slot`).
   - When `blocks == 0` AND `input_slot_set != {}` AND no line's
     trimmed text equals `EMPTY_MERGE_ATTESTATION`, return
     `raw_text + "\n" + EMPTY_MERGE_ATTESTATION + "\n"`.
   - Otherwise return `raw_text` unchanged.

   Wire the helper into the bash driver: after the model dispatch
   captures the raw output to `out_file` and before invoking the
   existing Python validate block (search anchor:
   `_validate_output` / line ~480), run the repair function via the
   same heredoc pattern already used for the strip pass (line ~582).
   Emit a single-line breadcrumb to `$REVIEW_TMPDIR/aggregator-repair.stderr`
   when synthesis fires (one line: `ATTESTATION_SYNTHESIZED=true
   input_slots=<N>`); the strip pass already runs after validation and
   will remove the synthesized attestation line from `findings.md`.

3. **Regression coverage (test-aggregate-findings.sh)**.
   Add two cases under the existing test rig (look for the `cleanup_case`
   helper anchor in the file):
   - `empty_merge_synthesis_succeeds`: feed input with one structured
     FINDING block and a mock vendor output that has zero FINDING
     blocks AND no attestation line; assert
     `count_finding_blocks(findings.md) == 0`,
     `REASON=ok`, AND `aggregator-repair.stderr`
     contains `ATTESTATION_SYNTHESIZED=true`. Confirm the persisted
     `findings.md` does NOT contain the attestation token (strip pass
     ran).
   - `empty_merge_existing_token_passthrough`: feed the same input but
     a mock vendor output that already includes the attestation token;
     assert behavior is unchanged from today's pass path, and the
     repair stderr is absent (or has `ATTESTATION_SYNTHESIZED=false`).

   Both cases share the harness's `assert_log_contains` /
   `assert_findings_count` primitives.

4. **Docs (aggregate-findings.md)**.
   Under the existing `Empty-merge attestation (runtime contract)`
   bullet, append a sub-bullet: when the model omits the token, the
   script synthesizes it deterministically and emits
   `ATTESTATION_SYNTHESIZED=true` to `aggregator-repair.stderr`. Note
   that the security purpose is preserved (the guardrail's claim still
   appears in the raw output) and link to the orchestrator-aggregator
   prompt for the model-side directive.

5. **Run the full lint suite**.
   `/relevant-checks` after step 4 to ensure pre-commit + agent-lint
   pass. Add `make test-aggregate-findings` invocation if a Makefile
   target exists; otherwise the test harness runs through pre-commit.

### Breaking changes

None. The synthesis pre-pass converts what is today an "executed but
failed validation → findings.md unchanged" path into a successful
zero-finding round. The persisted `findings.md` shape is unchanged
(attestation is stripped before write, same as today). External
consumers reading `aggregator-output.txt` and `aggregator-validate.stderr`
still see the raw model output and the validator's pass/fail decision;
the new `aggregator-repair.stderr` is additive.

### Closed decisions

- **Prefer script-side synthesis over treating validator-fail as
  acceptable**. Treating validation failure as a no-op would weaken
  the guardrail (no machine-readable claim for the empty-merge path),
  whereas synthesizing the attestation preserves the security signal
  while making the runtime resilient to model non-compliance.
- **Synthesize at the bash-driver layer, not inside the Python
  validate function**. The validator's responsibility is to accept or
  reject; synthesis is a recovery concern that belongs upstream.
- **No new flag** (`--no-attestation-synthesis` etc.). The recovery is
  always-on; operators who want to surface model non-compliance can
  read the breadcrumb stderr.

## Acceptance

1. `make test-aggregate-findings` (or `bash skills/review/scripts/test-aggregate-findings.sh`)
   exits 0 with the two new cases reported as PASS.
2. A staged synthetic run where the merging model emits zero FINDING
   blocks AND no attestation line ends with `REASON=ok`, no
   `External Reviewer Issues — findings aggregator: merged output failed
   validation` entry in `execution-issues.md`, and persisted
   `findings.md` containing no attestation token.
3. The existing `empty_merge_with_attestation` (or equivalent) PASS
   case in `test-aggregate-findings.sh` continues to PASS without
   modification (passthrough is unchanged for the happy path).
4. `/relevant-checks` (pre-commit + agent-lint) passes with no new
   warnings introduced under `skills/review/`, `agents/`, or
   `scripts/`.
5. After landing, a follow-up `/audit-runs since last audit` run that
   includes any PR whose review round triggered the empty-merge path
   reports zero `execution-issues-categories` non-Warnings entries for
   `findings aggregator: merged output failed validation` originating
   in `round-N/aggregator-validate.stderr`.

## Test plan
(no test plan section in plan-file)
