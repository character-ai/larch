### OOS_1: [OUT_OF_SCOPE] Primary dedup commit reviewed; diff matches stated scope
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases
- **Severity**: nit
- **Concern**: Commit `b5bc906cc` deduplicates implement checks-failed prose as the primary change. Edge review confirms prose dedup is consistent, load-bearing `--site` / `--checks-site` tokens are preserved, harnesses were updated in sync, and acceptance harnesses pass locally.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_2: [OUT_OF_SCOPE] Step 3 relevant-checks commit outside provided diff slice
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases
- **Severity**: nit
- **Concern**: Commit `be6362c2a` (Apply relevant-checks fixes, Step 3) is not in the provided diff slice. Edge review notes shellcheck comment-only change in the anti-halt harness and verdict that the diff matches the plan.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_3: [OUT_OF_SCOPE] Test harness migrations align with plan (positive coverage review)
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: `test-implement-structure.sh` pins the shared Step 5 block well (ordering, single `--site step5-mav --checks-site step5-review-fixes`, success-path continuation, forbids old inline combo). `test-plan-adequacy-audit.sh` correctly migrates `STATE=*` ownership. Anti-halt harness asserts macro-definition authority while call sites need only nearby macro invocation. `test-implement-fence-shape.sh` unchanged as expected. Anti-halt checks `Checks Failure Entry Macro` nearby but not per-site `--site step3` / `--site step6` tokens; only Step 5 gets explicit site pinning in structure tests. Runtime behavior: no Python, fence, or CLI changes; `--site` / `--checks-site` tokens at call sites unchanged.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_4: [OUT_OF_SCOPE] Step 6 post-fence prose uses “enter the repair macro” instead of explicit macro name
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: latent
- **Concern**: `skills/implement/SKILL.md:610` Step 6 post-fence text still says "enter the repair macro" instead of naming **Checks Failure Entry Macro** explicitly, while the pre-fence blockquote was collapsed to the macro name. Behavior is likely unchanged because `checks-repair-loop.md` still owns repair semantics, but the mixed wording is maintainability drift outside this PR's stated call-site edits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Align line 610 with the macro invocation phrasing used in the blockquote above.
  - From cursor-specialist-testing: Align wording for consistency; not required for this change to ship.

### OOS_5: [OUT_OF_SCOPE] Exit-code 3 pointer heading not byte-exact vs reference
- **Reviewer(s)**: cursor-specialist-edge-cases, dyn-dyn-harness-pins
- **Severity**: latent
- **Concern**: `skills/implement/SKILL.md:256` exit-code `3` pointer cites `## Clarify-request flow after AUDIT=refuse` without the inner backticks used in the actual reference heading at `skills/implement/references/preflight-plan-audit.md:67` (`after \`AUDIT=refuse\``). Unlikely to break routing because item 5 still mandates reading the full reference file, but the pointer is not byte-exact.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Match the reference heading literally in the pointer.

### OOS_6: [OUT_OF_SCOPE] Anti-halt does not pin per-site `--site step3` / `--site step6` tokens
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: latent
- **Concern**: `skills/implement/scripts/test-implement-relevant-checks-anti-halt.sh` verifies a nearby `Checks Failure Entry Macro` mention but not pinned `--site step3` / `--site step6` at each launcher. A future edit could drop those tokens and still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add per-site `--site` token checks in the awk window for each invocation line (plan-accepted tradeoff; optional hardening).

### OOS_7: [OUT_OF_SCOPE] Optional `require_near` for self-review success continuation
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: latent
- **Concern**: `scripts/test-implement-structure.sh:880-908` checks file-level presence of `> **Continue after child returns.**` and macro needles for `self-review.md`, but not nearness to the composite launcher (coverage removed when the site left `SKILL.md`).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add `require_near(self_review_ref, self_review_composite, '> **Continue after child returns.**', ...)` mirroring the immediate-background pins.

### OOS_8: [OUT_OF_SCOPE] Self-review anti-halt coverage moved to structure tests
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: Self-review checks-failed routing now depends on macro indirection in always-loaded `SKILL.md` rather than inline `REDACTED_LOG_FILE` / mandatory-read pins in `self-review.md`. That is intentional and covered by `test-implement-structure.sh`, but anti-halt coverage for self-review moved out of `test-implement-relevant-checks-anti-halt.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: None required for this PR; optional follow-up is a dedicated self-review anti-halt pin if halt-rate data ever regresses on `--self-review` runs.

### OOS_9: [OUT_OF_SCOPE] `chore(larch-logs)` flush commit is intentional artifact
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases
- **Severity**: nit
- **Concern**: Commit `7fceefaf0` chore(larch-logs) flush is an intentional `/implement` artifact; not reviewed as scope drift.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_10: [OUT_OF_SCOPE] `response-pending` path gap in preflight clarify documentation
- **Reviewer(s)**: dyn-dyn-harness-pins
- **Severity**: latent
- **Concern**: `skills/implement/references/preflight-plan-audit.md:67-79` — the old SKILL Sub-case A mentioned `response-pending` as a typical post path; the authoritative clarify flow documents `clean`, `ambiguous`, and `awaiting-response` only. That documentation gap was not introduced by this branch’s harness migration.
- **Suggested revisions (informational for voters; coder decides)**:

