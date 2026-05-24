### FINDING_1: Required-field check must include `RELEVANT_CHECKS_SKIPPED` as a third valid discriminator

- **Concern**: The plan's `step5_parse_checks_capture_file` sanity predicate treats only `STATUS` and `RELEVANT_CHECKS_OK` as valid discriminators. The real producer `scripts/run-relevant-checks-captured.sh` emits `RELEVANT_CHECKS_SKIPPED=true` (with neither `STATUS` nor `RELEVANT_CHECKS_OK`) when `scripts/relevant-checks.sh` is absent — a legitimate clean envelope. The proposed predicate would emit `required field missing` stderr on every legitimate skipped-checks run in consumer repos.
- **Proposed resolution**: Treat the discriminator as `STATUS || RELEVANT_CHECKS_OK || RELEVANT_CHECKS_SKIPPED`. Update the stderr wording, the Edge cases section, and the Failure modes "producers always emit a discriminator" prose. Add a positive parser fixture for `RELEVANT_CHECKS_SKIPPED=true` asserting no `required field missing` line is emitted.
- **Reviewers**: Cursor-Edge, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements (latent), Codex-Arch, Codex-Edge, Codex-Innovation, Codex-Pragmatic, Codex-Requirements (9 reviewers).


### FINDING_2: Wire the new `parsers` section into the sharded Makefile harness

- **Concern**: `make lint` and CI use `test-review-and-fix-dispatch` and `test-review-and-fix-convergence` section targets, not the full harness. A new `--section parsers` slice would never run in CI under `make lint` / `test-harnesses-*` unless the Makefile is extended.
- **Proposed resolution**: Add `test-review-and-fix-parsers` to the Makefile mirroring the existing two section targets, register it on a `test-harnesses-N` shard, ensure `.PHONY` covers it (per `scripts/test-harness-shards-coverage.sh` rules), and update any nearby comment block.
- **Reviewers**: Cursor-Arch (OOS), Cursor-Edge, Cursor-Innovation (nit), Cursor-Pragmatic, Cursor-Requirements, Codex-Arch, Codex-Edge, Codex-Innovation, Codex-Pragmatic, Codex-Requirements (9 reviewers).


### FINDING_3: Update `test-review-and-fix.md` sibling contract doc to document `--section parsers`

- **Concern**: Per `.claude/rules/script-md-siblings.md`, the sibling `.md` must reflect the new `--section` value. The plan adds `parsers` to the whitelist but does not edit the .md, leaving stale contract prose.
- **Proposed resolution**: Update `skills/review-and-fix/scripts/test-review-and-fix.md` to extend the documented `--section` union from `dispatch|convergence` to `dispatch|convergence|parsers` and note what the parsers slice covers (no drift-prone line numbers).
- **Reviewers**: Cursor-Innovation (OOS), Cursor-Pragmatic, Cursor-Requirements, Codex-Edge, Codex-Requirements (5 reviewers).


### FINDING_4: Fail-closed on malformed checks capture (set STATUS=fail + FAILURE_REASON=malformed-capture)

- **Concern**: The plan's stderr-only handling leaves `STEP5_CHK_STATUS` empty on a truly malformed capture. `run_implement_loop` then falls through past the `STATUS=fail` branch at line 182 (after `RELEVANT_CHECKS_SKIPPED`/`RELEVANT_CHECKS_OK` short-circuits also don't fire) — the loop continues silently, eventually emitting a `complete` envelope as if the round had succeeded. Lint wrapper already stalls via the `*` case at line 244, so this concern is checks-wrapper-only.
- **Proposed resolution**: In `step5_parse_checks_capture_file`, after the required-field check, when no discriminator was found, additionally set `STEP5_CHK_STATUS=fail` and `STEP5_CHK_FAILURE_REASON=malformed-capture`. The existing fail-handling at line 182-187 then emits a `stall` envelope with reason `relevant-checks-malformed-capture` and exits 2. Add a parser test asserting the wrapper sets these globals on malformed input.
- **Reviewers**: Cursor-Edge (latent), Codex-Arch, Codex-Edge, Codex-Innovation (4 reviewers).


### FINDING_5: Use a real `lint-fix-loop.sh` status value (e.g. `applied`) in the lint parser fixture, not synthetic `ok`

- **Concern**: The plan's testing strategy pins `LINT_FIX_STATUS=ok` for the happy-path lint parser test. The real producer at `scripts/lint-fix-loop.sh` only emits `applied`, `main-agent-required`, `failed`, or `no-changes`. The test would not exercise a realistic state.
- **Proposed resolution**: Change the happy-path lint fixture to `LINT_FIX_STATUS=applied` (or another real value). Document the four real values in the test comment.
- **Reviewers**: Codex-Edge (1 reviewer).


### FINDING_6: Reconcile "Files to modify" parsers bullets with "Testing strategy" cases

- **Concern**: The plan's `Files to modify` parsers checklist (bullets 1-6 inside `test-review-and-fix.sh`) does not fully encode the Testing strategy matrix. Specifically: the lint-malformed stderr case and the direct `step5_parse_kv_tokens` positive/negative/empty-line cases appear only under Testing strategy, not in the Files-to-modify subsection. An implementer who reads only the Files-to-modify section could ship a partial harness.
- **Proposed resolution**: Lift the missing test cases (lint-malformed; direct `step5_parse_kv_tokens` matrix) into the Files-to-modify parsers subsection so the checklist is the single source of truth for what must land. Either fold Testing strategy back into Files-to-modify or have both reference the same enumerated bullets.
- **Reviewers**: Cursor-Arch, Cursor-Edge (nit), Cursor-Innovation (nit), Cursor-Requirements (4 reviewers).


### FINDING_7: Reword "No other changes to either function" for clarity

- **Concern**: The sentence sits ambiguously between the post-loop stderr addition and the call-site note. A reader could interpret it as "wrappers must not change at all", conflicting with the proposed post-loop stderr/global edits.
- **Proposed resolution**: Reword to "no further edits inside the existing while-loop bodies besides the post-loop required-field guard; `run_implement_loop` call sites (lines ~172, ~195, ~210, ~235) are unchanged."
- **Reviewers**: Cursor-Arch, Cursor-Requirements (2 reviewers).


