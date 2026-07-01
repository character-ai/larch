### OOS_1: [OUT_OF_SCOPE] Panel-pruning round-5 re-probe wording shortened
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: nit
- **Concern**: Panel-pruning convergence text shortens round-5 re-probe to round 5. Behavior is unchanged under #5255, but operators debugging prune-to-empty may not connect round 5 with the full-panel re-probe semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Restore round-5 re-probe wording while keeping the compressed sentence structure.

### OOS_2: [OUT_OF_SCOPE] In-scope prose shrink slightly below ~15% target
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: nit
- **Concern**: Prose shrink is ~12.3% by bytes, slightly under the plan's ~15% token target. Acceptance density goal may be considered partially met; CI ratchet still depends on baseline byte-match after regen. Optionally compress more in prose-heavy sections or note achieved shrink in the PR if 15% is non-binding.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_3: [OUT_OF_SCOPE] Testing verification — change appears correctly scoped
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: Baseline ratchet update matches the plan (`closure_content_estimated_tokens` 69046→68300, `closure_lines` 2040→2037) for `test_committed_baseline_matches_fresh_scan`. Structural pins preserved (readability preamble line 19, MAV literals, tally-error routing, three numbered dedup bullets, byte-preserved `FINDING_N`/`OOS_N` templates, voter-line fence, `python/cli.py` invocations). Header contract triplet remains anchored. Harness mapping already routes `plan-review.md` edits to relevant tests; no new execution paths, so missing new tests is expected. `python/plan_review.py` and rendering code are untouched.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_4: [OUT_OF_SCOPE] Contract pin vs Topology anchor path drift
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: **Contract** still pins `python/plan_review_panel.py` (legacy S030 anchor; file absent on disk) while **Topology anchor** now points at `python/larch/review/plan_review_panel.py`. Pre-existing drift, amplified by this edit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Align both references to the real module path in a follow-up, or document the legacy pin explicitly.

### OOS_5: [OUT_OF_SCOPE] Closure/token reduction slightly below ~15% target
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-prose-contracts, dyn-dyn-closure-baseline
- **Severity**: nit
- **Concern**: Multiple reviewers note design-closure / `plan-review.md` shrink landed around ~12% (bytes or ~746 content tokens) versus the plan's roughly ~15% target. Likely acceptable under "roughly," but short of the stated goal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Optional further safe compression in non-byte-stable sections if operators want the full budget back.
  - From cursor-specialist-testing: None required unless the issue explicitly gates on ≥15%; otherwise document actual shrink in the PR if precision matters.

### OOS_6: [OUT_OF_SCOPE] Prompt injection framing thinned
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: nit
- **Concern**: `{CONTEXT_BLOCK}` prose at `skills/design/references/plan-review.md:84` no longer names "prompt injection"; the XML delimiter block inside the fence is unchanged. Documentation-only thinning on a trust-boundary surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Restore a brief "prompt injection" phrase in the parenthetical if operator-facing security framing is preferred over density.

### OOS_7: [OUT_OF_SCOPE] Aggregator waterfall cross-link (optional follow-up)
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: The decomposition cross-link dropped "(aggregator slot still uses waterfall)"; that detail remains in `skills/design/references/decompose-panel.md`. Low operator-confusion risk on Split-path only. Residual risk: the testing reviewer did not execute the plan's 11 acceptance commands in this read-only pass; CI failure would most likely come from stale baseline byte mismatch or undetected prose pin drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Optional one-word pointer ("see decompose-panel.md for aggregator waterfall") if you want zero semantic loss; not CI-blocking.

### OOS_8: [OUT_OF_SCOPE] Implement run-log commit widens PR surface
- **Reviewer(s)**: dyn-dyn-prose-contracts, dyn-dyn-closure-baseline
- **Severity**: latent
- **Concern**: The branch ships five unrelated implement run-log files (+190 lines) alongside the planned `plan-review.md` and `skill-closure-baseline.json` edits, adding merge/audit noise unrelated to prose compression or baseline refresh.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-closure-baseline: Drop the `chore(larch-logs): flush ...` commit from the PR branch (rebase or revert) so the branch contains only `plan-review.md` and `skill-closure-baseline.json`.

### OOS_9: [OUT_OF_SCOPE] Positive verification — preserved surfaces and baseline refresh
- **Reviewer(s)**: dyn-dyn-prose-contracts, dyn-dyn-closure-baseline
- **Severity**: nit
- **Concern**: Preserved surfaces look correct on inspection: readability preamble line 19, voter-line fence, `FINDING_N`/`OOS_N` templates, MAV `design-step3-mav.sh --phase pre|post` pins, all three numbered dedup bullets, `python/skill-closure-baseline.json` refresh, and the `--require-first-line-pattern` prohibition in Dispatch. Baseline refresh changes only the `design` row; the `implement` row and all `skill_md_*` fields are unchanged; `test_committed_baseline_matches_fresh_scan` passes.
- **Suggested revisions (informational for voters; coder decides)**:

