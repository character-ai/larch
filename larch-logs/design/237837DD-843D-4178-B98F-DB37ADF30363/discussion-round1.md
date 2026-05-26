## Decision 1: Fix scope (Step 1c clarifying answer)
- **Question**: Which fixes from the issue are in scope for THIS PR?
- **Resolution**: All three fixes (1 + 2 + 3). Fix 3 reframed in Decision 5 below.
- **Source**: user

## Decision 2: Architecture (Step 1c clarifying answer)
- **Question**: Keep the outer cursor→codex→claude waterfall in aggregate-findings.sh, or collapse to single slot like decompose-aggregator.sh (post-#2895)?
- **Resolution**: Collapse to single slot. dispatch-with-waterfall.sh handles the cursor/codex/claude fallback internally via its phase-1/phase-2/phase-3 chain plus the new `--require-result-pattern` gate.
- **Source**: user

## Decision 3: Regression test location (Step 1c clarifying answer)
- **Question**: Where should the regression test for narration-only fallback live?
- **Resolution**: Extend the existing sibling `skills/review/scripts/test-aggregate-findings.sh` (the file already exists — 49KB — so "new sibling" is reinterpreted as extending the canonical sibling).
- **Source**: user + codebase (codebase confirmed the file exists)

## Decision 4: Fix 3 OOS deferral (Step 1c clarifying answer)
- **Question**: Defer Fix 3 OOS filing?
- **Resolution**: Defer the OOS decision until after plan review. Plan-review reviewers may flag whether the historical round-1 inconsistency is worth tracking separately.
- **Source**: user

## Decision 5: Fix 3 reframing
- **Question**: After collapsing the outer loop, "investigate the round-1 inconsistency" becomes archaeological. How should Fix 3 be interpreted?
- **Resolution**: Reframe Fix 3 as "regression test for the new collapse design" — drop the forensic investigation; add a test asserting that a narration-only Cursor primary triggers the dispatcher's internal phase-2 Codex fallback (via `--require-result-pattern`), restoring the symptom-free state. No archaeological writeup in aggregate-findings.md.
- **Source**: user

## Decision 6: Backward compat — `REASON=validation-exhausted`
- **Question**: Must `REASON=validation-exhausted` and its consumer path remain functional after the collapse?
- **Resolution**: YES. review-core.sh:514–545 branches on it to empty accepted/rejected/oos and emit `REVIEW_CORE_STATUS=aggregator-validation-exhausted`; review-and-fix.sh, review-implement-step5-loop.sh, and test-review-core.sh all consume that path. It MUST remain reachable. Post-collapse semantics: emit `validation-exhausted` when the dispatcher returned a `STATUS=OK` pattern-matching candidate but the python post-dispatch validator failed narrow-trigger AND no further automatic retry is possible (i.e., the dispatcher has exhausted its internal phases or we cannot meaningfully retry from this layer).
- **Source**: codebase (review-core.sh:514, review-and-fix.sh, review-implement-step5-loop.sh, test-review-core.sh)

## Decision 7: Test harness migration scope
- **Question**: What should happen to the ~10 LARCH_AGGREGATE_MAX_OUTER_PHASES test cases?
- **Resolution**: Rewrite/delete the ~10 cases in this PR. The env var becomes meaningless under single-slot collapse; deleting deletes dead code. Cases that simulate phase-mismatch via the outer loop can be re-expressed as dispatch-with-waterfall fixtures (or deleted if no longer testable from the aggregate-findings.sh layer).
- **Source**: user

## Decision 8: Acceptance reconciliation
- **Question**: Should the plan rewrite the issue's acceptance criteria, since the original wording references the removed outer loop?
- **Resolution**: YES. The composed plan's Acceptance section will reframe to match the collapse design: single Codex-primary slot with `--require-result-pattern`; tool-level fallback delegated to dispatch-with-waterfall internal phases (Codex → Cursor → Claude); regression test asserts pattern-mismatch on Cursor triggers internal phase-2 Codex fallback.
- **Source**: user

## Decision 9: Adjacent surface (out-of-scope guardrail)
- **Question**: Which adjacent scripts/docs may this PR touch?
- **Resolution**: aggregate-findings.sh (primary script), aggregate-findings.md (sibling contract), test-aggregate-findings.sh (sibling harness), CHANGELOG.md (Unreleased entry), SECURITY.md (line ~81 describes the outer-waterfall behavior — must be updated to reflect collapse). review-core.sh / review-core.md are in-bounds IF removing dead code becomes warranted, but per Decision 6 the validation-exhausted branch stays — so likely no-op. No edits to dispatch-with-waterfall.sh (its `--require-result-pattern` flag is already merged via #2895).
- **Source**: user + codebase

## Decision 10: Non-goal — propagation to other callers
- **Question**: Should this PR also thread `--require-result-pattern` into other call sites (e.g., plan-review reviewers, code-review per-slot launches)?
- **Resolution**: NO. Out of scope. Other callers (plan-review reviewer slots, individual code-review reviewer launches) have different output structures (findings vs ballots vs narratives) and would need their own per-caller pattern decisions. Restrict this PR to aggregate-findings.sh's single dispatch call.
- **Source**: codebase + scope guardrail (Decision 9 lists adjacent surface; no other callers listed)

Recorded 10 decisions resolved.
