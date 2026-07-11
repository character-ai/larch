## Goal
Implement issue #6837: [IMPLEMENTING] Step 8 assessment lane 4/4: Activate the combined Step 8 route.

## Implementation Plan
## Plan

Activate the combined Step 8 assessment adapter for every architectural-assessment route while keeping all runtime implementation from Pieces 1–3 unchanged.

The main agent will normalize the route handoff, invoke one blocking `skills/implement/scripts/step-8-assessment.sh` fence through `implement-run-$PPID.sh`, and consume only its validated terminal KV envelope. The adapter remains solely responsible for bgjob start, repeated documented `python/cli.py bgjob wait --max-wait-s 270` calls, retry, deterministic pre-filtering, delegated assessment authoring, durable persistence, scoped reuse and reassessment, and timeout-to-unavailable handling.

Immediately before the single adapter fence, normalize `.ship-route-exit-handoff.env` without changing unrelated handoff keys:

- For `NEXT_ACTION=assessments`, retain the existing valid combined requested-kind payload from `DETAIL` or its existing `DETAIL_FILE` source.
- For `NEXT_ACTION=invariants-assessment`, rewrite `NEXT_ACTION=assessments` and set the canonical requested kind to `DETAIL=invariants`.
- For `NEXT_ACTION=guidelines-assessment`, rewrite `NEXT_ACTION=assessments` and set the canonical requested kind to `DETAIL=guidelines`.
- Reject malformed, empty, duplicate, unknown, or otherwise noncanonical requested-kind payloads through the existing fail-closed route; do not invent a new kind token, per-kind writer path, or fallback parser.

The adapter fence is repeated **only** when the Bash tool itself times out while the adapter bgjob remains live. In that case, repeat the identical adapter fence with no intervening prose, polling, sleeps, process inspection, alternate waits, normalization rewrite, or ship relaunch. Do not treat a nonzero adapter exit, `ASSESSMENT_STATUS=fail-closed`, a stale-identity error, or any failed validation as a Bash-tool timeout.

After a normal adapter return, require all of the following before continuing:

- adapter exit success;
- `BGJOB_RC=0`;
- `STEP=implement-step8-assessment`;
- a non-empty `ASSESSMENT_COVERED_FINGERPRINT`;
- `ASSESSMENT_REQUESTED_KINDS` matching the canonical normalized request;
- `ASSESSMENT_STATUS=complete`;
- complete persisted result coverage for every requested kind; and
- a result identity and fingerprint that match the current Step 8 request.

A validated existing timeout-to-unavailable result may count only where the adapter’s existing complete result-envelope contract represents it as durable coverage. Do not reinterpret unavailable, fail-closed, stale, or partial output as success.

For any adapter exit error other than the Bash-tool timeout re-entry case, nonzero `BGJOB_RC`, `ASSESSMENT_STATUS` other than `complete`, missing or malformed KV, stale or mismatched identity, kind mismatch, incomplete result coverage, or failed fingerprint validation:

- route to the existing Step 8 `tool-failure` handling;
- append the existing Tool Failures record and hard-stop using that route;
- do not relaunch `step-8-ship.sh`;
- do not retry or replace the assessment job from prompt-side orchestration;
- do not use an inline assessment, diff-reading, draft-writing, compose-writer, or operator-override escape hatch; and
- preserve the existing invariant-violation hard stop and no-override policy.

Only after successful normalization and validation, relaunch the existing `step-8-ship.sh` bgjob route exactly once. Never relaunch once per kind.

Preserve the existing deterministic docs-only reuse and once-per-run scope semantics: a later `HEAD` change re-runs the pre-filter against the incremental scope, reuses valid covered results when no new architectural scope intersects, and reauthors only when a newly touched scope requires it. Remove any remaining Step 7a or Step 8 language that claims unconditional reassessment after every `HEAD` change.

## Files to modify/create

### UPDATED: skills/implement/SKILL.md

- Replace inline `assessments`, `invariants-assessment`, and `guidelines-assessment` authorship instructions with one shared adapter route.
- Add an explicit pre-adapter handoff-normalization step immediately before the sole `step-8-assessment.sh` fence:
  - preserve valid combined `assessments` requested-kind detail;
  - map `invariants-assessment` to `NEXT_ACTION=assessments` with `DETAIL=invariants`;
  - map `guidelines-assessment` to `NEXT_ACTION=assessments` with `DETAIL=guidelines`;
  - preserve unrelated handoff keys; and
  - fail closed rather than attempting to repair malformed combined requested-kind data.
- State that the adapter alone owns bgjob start, internal documented wait-loop behavior, retry, deterministic filtering, delegated authored work, persistence, docs-only reuse, scoped code-change reassessment, and timeout-to-unavailable handling.
- State that the main agent must not load `architectural-guidelines-present.md` or `architectural-invariants-present.md` on an assessment branch as an assessment-work prompt; those files become durable route references, not prompt-side assessment instructions.
- On a Bash-tool timeout only, direct the main agent to repeat the identical adapter fence with no intervening actions. Explicitly distinguish this re-entry case from adapter errors and validation failures.
- Validate adapter exit and terminal KVs before continuing: `BGJOB_RC`, `STEP`, `ASSESSMENT_COVERED_FINGERPRINT`, `ASSESSMENT_REQUESTED_KINDS`, `ASSESSMENT_STATUS`, requested-result completeness, and request/fingerprint identity.
- Define the terminal failure branch beside the validation list: any non-timeout adapter failure, `ASSESSMENT_STATUS=fail-closed`, adapter stale-identity error, nonzero `BGJOB_RC`, missing or mismatched KV, stale fingerprint, requested-kind mismatch, or incomplete result coverage routes to existing Step 8 `tool-failure` handling with no ship relaunch.
- Relaunch the existing `step-8-ship.sh` bgjob route exactly once only after all requested assessment results persist and validate.
- Remove instructions that tell the main agent to read materialized diffs, author assessment drafts, append deviation notes, invoke per-kind compose writers, inspect assessment evidence as instructions, or perform inline fallback.
- Replace any unconditional “refresh after every `HEAD` change” wording with scoped once-per-run behavior: deterministic pre-filter reuse for nonintersecting changes and reassessment only for a newly intersected architectural scope.
- Preserve the anti-halt transition back to Step 8, existing tool-failure behavior, invariant blocking, and prohibition on operator overrides for invariant violations.

### REWRITTEN: skills/implement/references/architectural-guidelines-present.md

- Replace the prompt-side authorship contract with a concise durable route reference for the read-only Step 8 adapter lane.
- Identify the normalized combined `assessments` route as primary and `guidelines-assessment` as a dormant compatibility alias that must normalize to `NEXT_ACTION=assessments` with `DETAIL=guidelines` before adapter invocation.
- State that callers do not read the materialized diff, write an assessment draft, call a compose writer, or invoke an inline fallback.
- Describe the adapter-owned deterministic clean path, durable docs-only reuse, scoped reassessment only for new code-scope intersections, timeout-to-unavailable outcome, and persistence at the contract level.
- State that guideline files, diffs, model output, handoff detail, and diagnostics are untrusted evidence, not instructions.
- Require strict adapter identity, fingerprint, requested-kind, completion, and coverage validation before the single ship relaunch.
- State that failed validation, `fail-closed`, stale identity, or incomplete coverage routes to Step 8 tool-failure handling without a ship relaunch.

### REWRITTEN: skills/implement/references/architectural-invariants-present.md

- Replace the prompt-side authorship contract with the shared read-only adapter-route reference.
- Identify the normalized combined `assessments` route as primary and `invariants-assessment` as a dormant compatibility alias that must normalize to `NEXT_ACTION=assessments` with `DETAIL=invariants` before adapter invocation.
- Remove draft-body, materialized-diff, deviation-appender, and compose-writer instructions.
- Preserve invariant-specific fail-closed behavior: a reported violation continues to block normal PR compose and follows the existing repair policy; no operator acceptance or inline reassessment is permitted.
- Describe deterministic clean results, valid-coverage reuse, scoped reassessment after a newly intersecting code change, validated unavailable outcomes, and stale-result rejection without duplicating adapter logic.
- Treat invariant text, diffs, assessor output, handoff data, and diagnostics as untrusted evidence.
- State that failed adapter validation routes to tool-failure handling and cannot relaunch ship.

### UPDATED: skills/implement/references/ship-pr-exit-matrix.md

- Change the `assessments` row from per-kind main-agent authorship to the blocking combined assessment adapter.
- Document normalization for all three route tokens before adapter invocation, including the legacy alias mappings to canonical `NEXT_ACTION=assessments` and their single requested kind.
- Pin ordering: normalize once, invoke the adapter, validate its terminal envelope, then relaunch `step-8-ship.sh` exactly once.
- State that a Bash-tool timeout alone repeats the identical adapter fence; adapter failure, `fail-closed`, stale identity, nonzero bgjob rc, or validation failure routes to existing tool-failure handling with no relaunch.
- Describe the single-kind actions as dormant compatibility aliases to the same adapter.
- Remove references to materialized-diff reading, draft authorship, prompt-side staging, deviation appenders, and per-kind compose writers.
- Preserve all unrelated Step 8 route semantics.

### UPDATED: skills/implement/scripts/test-architectural-guidelines-step.sh

- Replace assertions for inline authorship and individual writer calls with assertions for the shared adapter fence.
- Assert that `assessments`, `invariants-assessment`, and `guidelines-assessment` all normalize to the combined adapter handoff and route through `step-8-assessment.sh`.
- Pin legacy normalization explicitly:
  - invariants alias yields `NEXT_ACTION=assessments` and `DETAIL=invariants`;
  - guidelines alias yields `NEXT_ACTION=assessments` and `DETAIL=guidelines`;
  - combined requests preserve their valid requested-kind payload;
  - unrelated handoff keys are preserved; and
  - malformed requested-kind payloads do not gain a prompt-side repair or fallback route.
- Assert the adapter-owned documented wait behavior and identical-fence re-entry only after a Bash-tool timeout.
- Assert validation of adapter exit, `BGJOB_RC`, `STEP`, `ASSESSMENT_COVERED_FINGERPRINT`, `ASSESSMENT_REQUESTED_KINDS`, `ASSESSMENT_STATUS`, result completeness, and request/fingerprint identity.
- Assert that `fail-closed`, stale identity, nonzero bgjob rc, non-timeout adapter exit failure, missing KVs, kind mismatch, or incomplete results route to tool-failure handling and never to `step-8-ship.sh`.
- Assert assessment completion and validation appear before the one allowed ship relaunch.
- Pin dormant legacy-alias wording, untrusted-evidence treatment, docs-only reuse, scoped code-change reassessment, timeout-to-unavailable behavior, and preserved invariant blocking.
- Update the stale Step 7a/Step 8 reassessment assertion to reject unconditional `HEAD`-based refresh language and require incremental scope/pre-filter semantics.
- Add negative assertions against loading either present-reference file as assessment-work instructions, main-agent diff reading, draft authorship, deviation-appender calls, both per-kind compose writers, explicit prompt-side bgjob waits, and inline fallback.

### UPDATED: scripts/test-implement-fence-shape.sh

- Replace the legacy Step 8 compose-write ordering assertions, including any per-kind compose-writer requirements and any guidelines-only relaunch expectation, with adapter-first assertions for the approved combined route.
- Update the Step 8 Bash-fence inventory for the pre-adapter normalization and one blocking adapter fence.
- Adjust `EXPECTED_OLD` and `EXPECTED_NEW` for the resulting SKILL fence count and adjacency.
- Pin exactly one `step-8-assessment.sh` launcher through the `implement-run-$PPID.sh` launcher for all three assessment route tokens after normalization.
- Verify that the adapter is not represented as a prompt-side assessment bgjob start/wait pair and that any normalization occurs immediately before the adapter route rather than as a second assessment launcher.
- Assert that no legacy ordering slice requires `step-architectural-guidelines-write-compose.sh`, an invariants compose writer, a per-kind writer sequence, or a ship relaunch limited to guidelines.
- Assert that the only permitted post-assessment continuation is one `step-8-ship.sh` relaunch after terminal-envelope validation, regardless of whether one or both requested kinds were assessed.
- Keep the existing Step 8 ship launcher and wait fence shape intact for the one post-validation relaunch.

### UPDATED: python/tests/implement/test_implement_dispatch.py

- Preserve coverage that `architectural-assessments` maps to `NEXT_ACTION=assessments` and carries `DETAIL`.
- Preserve explicit coverage for the dormant `architectural-invariants-assessment` and `architectural-guidelines-assessment` aliases.
- Refine test expectations to show that Python dispatch continues to emit the legacy compatibility actions while prompt-side Step 8 normalization converts them to the combined adapter contract.
- Pin requested-kind detail preservation required by caller-side validation.
- Do not change production Python routing, add active Python routes, or alter adapter contracts.

### UPDATED: SECURITY.md

- Add a focused Step 8 architectural-assessment trust-boundary section.
- Revise the existing `ARCHITECTURAL_INVARIANTS.md` and `ARCHITECTURAL_GUIDELINES.md` guidance so it no longer describes main-agent diff reading, prompt-side staging, materialized-diff consumption, or per-kind assessment authorship.
- Document that all Step 8 assessment tokens normalize into the read-only bgjob adapter lane and that the main agent does not read the assessment diff or author assessment prose.
- Classify repository knowledge files, materialized diffs, model output, route-handoff detail, result envelopes, and diagnostics as untrusted evidence rather than instructions.
- Document strict validation of adapter exit, bgjob success, step identity, requested kinds, covered fingerprint, completion state, result completeness, and request identity before any result is consumed.
- State that stale, mismatched, malformed, incomplete, or `fail-closed` results are rejected and route to tool-failure handling without a ship relaunch.
- State that only a Bash-tool timeout while the adapter remains live permits identical-fence re-entry; bounded adapter retry and validated unavailable outcomes never authorize inline authoring.
- Require diagnostics to remain bounded and redacted before any egress surface.
- Preserve the existing invariant-violation hard stop and no-override policy, and cross-reference the Step 8 trust-boundary section from the revised architectural-knowledge guidance.

## Edge cases

- The routed kind list contains one kind, both kinds, reordered kinds, duplicates, empty tokens, or unknown tokens.
- The combined route supplies valid `DETAIL`, supplies only its existing supported detail source, or supplies malformed/missing requested-kind information.
- The invariants or guidelines compatibility route arrives with a legacy reason and no `DETAIL`; normalization must synthesize the corresponding single canonical kind while preserving unrelated handoff keys.
- The Bash tool times out while the adapter bgjob remains live. Repeating the identical adapter fence must rejoin rather than start duplicate work.
- The adapter exits nonzero, including its existing stale-identity path, without a Bash-tool timeout. Route tool-failure; do not repeat the fence.
- The adapter returns success text but its result env is absent, incomplete, stale, malformed, or for different requested kinds.
- The result fingerprint does not match the request identity.
- An assessment times out and persists a validated unavailable result under the existing complete-envelope contract.
- A docs-only change reuses valid coverage without another model call.
- A later code change enters a previously untouched architectural scope and triggers the existing scoped reassessment.
- An invariant violation persists and must block ship despite the new delegation route.
- Both assessment kinds complete, but only one result is present. Do not relaunch ship.
- Assessment succeeds, but the ship relaunch fails. Do not rerun assessment unless existing identity and scope rules require it.

## Failure modes

- Prompt prose accidentally keeps an inline authorship, materialized-diff, or per-kind compose-writer escape hatch.
- A legacy alias reaches the frozen adapter without canonical `NEXT_ACTION=assessments` and requested-kind detail.
- The main agent uses an explicit bgjob wait fence even though the adapter owns the wait loop.
- A Bash-tool timeout starts a second assessment instead of rejoining.
- A non-timeout adapter error is mistaken for a timeout re-entry condition.
- Validation trusts `DONE`, process exit, or `ASSESSMENT_STATUS=complete` alone without checking result identity, coverage, and completeness.
- A stale result causes ship to continue against a different diff.
- The combined route relaunches ship once per kind instead of once after all results persist.
- Legacy fence-shape assertions still require a per-kind compose writer, compose-write ordering, or a guidelines-only relaunch after the adapter-only flow replaces them.
- A failed, stale, fail-closed, or incomplete adapter result bypasses existing tool-failure handling.
- Durable references or SECURITY.md disagree with SKILL.md about delegation, normalization, untrusted evidence, or terminal failure routing.
- Security prose exposes raw assessor diagnostics or implies trusted model output.
- Fence-shape expectations drift from the changed SKILL.md Bash blocks.

## Testing strategy

1. Run `skills/implement/scripts/test-architectural-guidelines-step.sh` to verify the shared adapter contract, all alias-normalization mappings, negative assertions, validation fields, terminal tool-failure routing, scoped reassessment wording, and assessment-before-relaunch ordering.
2. Run `scripts/test-implement-fence-shape.sh` to verify the immediate normalization-to-adapter fence shape, exactly one adapter launcher through `implement-run-$PPID.sh`, absence of prompt-side assessment start/wait fences, removal of legacy compose-write and guidelines-only-relaunch expectations, and unchanged Step 8 ship start/wait shape.
3. Run the focused tests in `python/tests/implement/test_implement_dispatch.py` for combined assessment routing, requested-kind detail preservation, and dormant legacy alias mappings.
4. Run `skills/implement/scripts/test-step-8-assessment.sh` unchanged as an integration guard for the frozen Piece 3 adapter contract.
5. Lint only the changed Markdown, shell, and Python test files with the documented focused targets.
6. Confirm by targeted search that live Step 8 instructions no longer tell the main agent to load assessment-present references for authorship, read materialized assessment diffs, create assessment drafts, call deviation appenders, call per-kind compose writers, use explicit assessment wait fences, or fall back inline.
7. Confirm by targeted search that `scripts/test-implement-fence-shape.sh` contains no stale assertion requiring a per-kind compose writer, legacy compose-write ordering, or a guidelines-only ship relaunch.
8. Confirm by targeted search that no Step 7a or Step 8 prose claims unconditional reassessment after every `HEAD` change.
9. Confirm the implementation does not modify the adapter, its prompt, Python assessment drivers, production dispatch, route tokens, result states, kind tokens, deterministic pre-filter, or ship driver.

## Scope controls

- Do not change Piece 1 through Piece 3 runtime implementation.
- Do not modify `step-8-assessment.sh`, `step-8-assessment.md`, Python assessment drivers, production dispatch, route tokens, kind tokens, result states, deterministic pre-filter, or ship driver.
- Implement legacy alias normalization only in the approved Step 8 prompt/documentation surface immediately before the existing adapter fence.
- Do not introduce new route, kind, result-state, or KV tokens.
- Do not remove the legacy dispatch aliases during this release.
- Do not add another assessment retry, persistence implementation, or prompt-side wait loop.
- Do not alter `/design` architectural assessment behavior.
- Do not expand the change beyond the eight approved surfaces.

Confidence: high  
difficulty: HARD

## Acceptance

1. Run `skills/implement/scripts/test-architectural-guidelines-step.sh` to verify the shared adapter contract, all alias-normalization mappings, negative assertions, validation fields, terminal tool-failure routing, scoped reassessment wording, and assessment-before-relaunch ordering.
2. Run `scripts/test-implement-fence-shape.sh` to verify the immediate normalization-to-adapter fence shape, exactly one adapter launcher through `implement-run-$PPID.sh`, absence of prompt-side assessment start/wait fences, removal of legacy compose-write and guidelines-only-relaunch expectations, and unchanged Step 8 ship start/wait shape.
3. Run the focused tests in `python/tests/implement/test_implement_dispatch.py` for combined assessment routing, requested-kind detail preservation, and dormant legacy alias mappings.
4. Run `skills/implement/scripts/test-step-8-assessment.sh` unchanged as an integration guard for the frozen Piece 3 adapter contract.
5. Lint only the changed Markdown, shell, and Python test files with the documented focused targets.
6. Confirm by targeted search that live Step 8 instructions no longer tell the main agent to load assessment-present references for authorship, read materialized assessment diffs, create assessment drafts, call deviation appenders, call per-kind compose writers, use explicit assessment wait fences, or fall back inline.
7. Confirm by targeted search that `scripts/test-implement-fence-shape.sh` contains no stale assertion requiring a per-kind compose writer, legacy compose-write ordering, or a guidelines-only ship relaunch.
8. Confirm by targeted search that no Step 7a or Step 8 prose claims unconditional reassessment after every `HEAD` change.
9. Confirm the implementation does not modify the adapter, its prompt, Python assessment drivers, production dispatch, route tokens, result states, kind tokens, deterministic pre-filter, or ship driver.

diff_lines: 398

## Test plan
(no test plan section in plan-file)
