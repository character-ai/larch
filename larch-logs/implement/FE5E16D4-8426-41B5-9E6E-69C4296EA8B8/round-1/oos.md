### FINDING_11: risk-integration: scripts/test-implement-step2-routing.md:7
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Harness doc still documents Cursor-first omitted --coder waterfall. Contributors reading the harness .md get the wrong contract though .sh pins were updated. Change line 7 to Codex → Cursor → Claude to match test-implement-step2-routing.sh.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_12: [OUT_OF_SCOPE] risk-integration: skills/design/scripts/test-plan-review-loop.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] #3338 PATH STUB_BIN backstop is bundled on the branch but outside #3337 scope. Improves make lint hermeticity when externals are installed; unrelated to codex-first defaults. No action required for #3337; keep as separate fix.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=0 JUDGE_ERROR=1 Result=rejected

### FINDING_13: [OUT_OF_SCOPE] risk-integration: CHANGELOG.md:55-63
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Released 47.0.42 changelog covers #3338 only not #3337. Consumers may not see #3337 in shipped notes until a later bump commit. Add #3337 bullets when version is bumped for this feature.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted

### FINDING_18: [OUT_OF_SCOPE] architecture: scripts/ship-pr.sh:2069-2122
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] first-fixer bail can miss when rotated first tier is skipped (e.g. missing launch-claude-ci.sh). start_attempt=2 with Claude first skipped: later tier other-class does not short-circuit to exit 3. Fix waterfall_iter/first_tier coupling separately from #3337.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted

### FINDING_19: [OUT_OF_SCOPE] risk-integration: SECURITY.md:105
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Explicit --coder fail-closed wording predates #3207 waterfall. Operators expect hard bail on unavailable pinned coder. Sync SECURITY.md with #3207 waterfall semantics in a dedicated doc fix.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted

### FINDING_21: [OUT_OF_SCOPE] architecture: CHANGELOG.md
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] CHANGELOG may still document Cursor-first omitted --coder routing; plan did not require updating it in this issue. Operators reading only CHANGELOG could see stale routing until the next version entry. Add a CHANGELOG bullet when the version bump lands for #3337 (if not handled by bump-version Step 8).
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted

### FINDING_22: **correctness** `python/test_ci_monitor.py:943-944` — `test_evaluate_failure_verify_failed_then_pushed` was retargeted for codex-first rotation (commit-message mocks and comment at 901–903) but still only asserts `len(launch_calls) == 2`, not tier order. A regression that invoked Codex twice (or Cursor twice) on the verify-failed retry path would still pass, so Python parity with Bash `run_ci_fix_vendor` rotation (`start_attempt` 0 → codex, 1 → cursor) is not mechanically pinned. **Suggested fix:** Add `assert launch_calls == ["codex", "cursor"]` (or the exact sequence your scenario intends) so outer-attempt rotation stays locked to `FIXER_TIER_ORDER` after the #3337 flip.
- **Reviewer**: dyn-waterfall-routing-output.txt
- **Concern**: - **correctness** `python/test_ci_monitor.py:943-944` — `test_evaluate_failure_verify_failed_then_pushed` was retargeted for codex-first rotation (commit-message mocks and comment at 901–903) but still only asserts `len(launch_calls) == 2`, not tier order. A regression that invoked Codex twice (or Cursor twice) on the verify-failed retry path would still pass, so Python parity with Bash `run_ci_fix_vendor` rotation (`start_attempt` 0 → codex, 1 → cursor) is not mechanically pinned. **Suggested fix:** Add `assert launch_calls == ["codex", "cursor"]` (or the exact sequence your scenario intends) so outer-attempt rotation stays locked to `FIXER_TIER_ORDER` after the #3337 flip.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_23: [OUT_OF_SCOPE] Runtime waterfall changes look internally consistent on this branch: `_phase_coder_implicit` probes Codex then Cursor then Claude (`scripts/implement-bootstrap.sh:1257-1270`); explicit `--coder` waterfalls in `_phase_coder_explicit` / `_phase_coder_explicit_waterfall` are unchanged; `run_ci_fix_vendor` uses `tiers=(codex cursor claude)` with `first_tier=${tiers[$(( start_attempt % 3 ))]}` (`scripts/ship-pr.sh:2039-2072, 2115-2121`); `run_recovery_waterfall` iterates `codex cursor claude` (`scripts/ship-pr.sh:2815-2826`); the legacy single-vendor rebase path prefers Codex over Cursor (`scripts/ship-pr.sh:3390-3401`); Python `FIXER_TIER_ORDER` and `agents.run_waterfall` rotation match Bash (`python/config.py:30`, `python/ci_monitor.py:912-916`, `python/agents.py:244-246`).
- **Reviewer**: dyn-waterfall-routing-output.txt
- **Concern**: - Runtime waterfall changes look internally consistent on this branch: `_phase_coder_implicit` probes Codex then Cursor then Claude (`scripts/implement-bootstrap.sh:1257-1270`); explicit `--coder` waterfalls in `_phase_coder_explicit` / `_phase_coder_explicit_waterfall` are unchanged; `run_ci_fix_vendor` uses `tiers=(codex cursor claude)` with `first_tier=${tiers[$(( start_attempt % 3 ))]}` (`scripts/ship-pr.sh:2039-2072, 2115-2121`); `run_recovery_waterfall` iterates `codex cursor claude` (`scripts/ship-pr.sh:2815-2826`); the legacy single-vendor rebase path prefers Codex over Cursor (`scripts/ship-pr.sh:3390-3401`); Python `FIXER_TIER_ORDER` and `agents.run_waterfall` rotation match Bash (`python/config.py:30`, `python/ci_monitor.py:912-916`, `python/agents.py:244-246`).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=0 JUDGE_ERROR=1 Result=rejected

### FINDING_24: [OUT_OF_SCOPE] `CHANGELOG.md:44` (Unreleased) still documents omitted-`--coder` as **Cursor → Codex → Claude** while live code and `SECURITY.md` now say Codex-first; the branch adds a `47.0.42` entry for #3338 but no Unreleased/released note for #3337.
- **Reviewer**: dyn-waterfall-routing-output.txt
- **Concern**: - `CHANGELOG.md:44` (Unreleased) still documents omitted-`--coder` as **Cursor → Codex → Claude** while live code and `SECURITY.md` now say Codex-first; the branch adds a `47.0.42` entry for #3338 but no Unreleased/released note for #3337.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted

### FINDING_25: [OUT_OF_SCOPE] `scripts/test-implement-step2-routing.md:7` still says **Cursor → Codex → Claude**; the `.sh` harness and `implement-bootstrap.md` were updated, but the sibling contract doc was not (not CI-gated).
- **Reviewer**: dyn-waterfall-routing-output.txt
- **Concern**: - `scripts/test-implement-step2-routing.md:7` still says **Cursor → Codex → Claude**; the `.sh` harness and `implement-bootstrap.md` were updated, but the sibling contract doc was not (not CI-gated).
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted

### FINDING_26: [OUT_OF_SCOPE] Branch tip includes unrelated commits (`#3338` plan-review-loop hang fix, several `larch-logs` flushes); waterfall review above targets the #3337 routing surfaces in the precomputed diff.
- **Reviewer**: dyn-waterfall-routing-output.txt
- **Concern**: - Branch tip includes unrelated commits (`#3338` plan-review-loop hang fix, several `larch-logs` flushes); waterfall review above targets the #3337 routing surfaces in the precomputed diff.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=1 Result=exonerated

### FINDING_29: [OUT_OF_SCOPE] **Pre-existing `waterfall_iter` vs skipped Claude launcher:** In `scripts/ship-pr.sh:2073-2078`, an unavailable `launch-claude-ci.sh` increments `waterfall_iter` before any launcher runs. When outer rotation starts at `claude` (`start_attempt=2`), a later tier’s `other` failure may not satisfy `waterfall_iter -eq 0` at `2115-2121`, so `first-fixer-non-health` may not fire even though docs describe “rotated first tier” policy (`scripts/ship-pr.md:152-154`). Not introduced by the tuple flip; same structure existed cursor-first.
- **Reviewer**: dyn-rotation-policy-output.txt
- **Concern**: - **Pre-existing `waterfall_iter` vs skipped Claude launcher:** In `scripts/ship-pr.sh:2073-2078`, an unavailable `launch-claude-ci.sh` increments `waterfall_iter` before any launcher runs. When outer rotation starts at `claude` (`start_attempt=2`), a later tier’s `other` failure may not satisfy `waterfall_iter -eq 0` at `2115-2121`, so `first-fixer-non-health` may not fire even though docs describe “rotated first tier” policy (`scripts/ship-pr.md:152-154`). Not introduced by the tuple flip; same structure existed cursor-first.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted

### FINDING_30: [OUT_OF_SCOPE] **Pre-existing #3134 “no commit” bail:** `scripts/ship-pr.sh:2144-2166` classifies `first-fixer-non-health` from the **winning** tier after staging, not from `first_tier` of the rotated list. That is separate from the `LAUNCHER_FAILURE_CLASS=other` short-circuit and unchanged by this branch.
- **Reviewer**: dyn-rotation-policy-output.txt
- **Concern**: - **Pre-existing #3134 “no commit” bail:** `scripts/ship-pr.sh:2144-2166` classifies `first-fixer-non-health` from the **winning** tier after staging, not from `first_tier` of the rotated list. That is separate from the `LAUNCHER_FAILURE_CLASS=other` short-circuit and unchanged by this branch.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=1 Result=exonerated

### FINDING_31: [OUT_OF_SCOPE] **Python parity (Phase 7):** `python/ci_monitor.py:912` rotates with `start_attempt % len(tiers)` while Bash always uses `% 3` on a fixed triple; only `FIXER_TIER_ORDER` changed here. Live path remains Bash until Phase 7.
- **Reviewer**: dyn-rotation-policy-output.txt
- **Concern**: - **Python parity (Phase 7):** `python/ci_monitor.py:912` rotates with `start_attempt % len(tiers)` while Bash always uses `% 3` on a fixed triple; only `FIXER_TIER_ORDER` changed here. Live path remains Bash until Phase 7.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=1 JUDGE_ERROR=1 Result=exonerated

### FINDING_32: [OUT_OF_SCOPE] **Historical changelog:** `CHANGELOG.md:1149` still names “first-tier fixer (Cursor)”; not updated in the `#3337` commit and predates this flip.
- **Reviewer**: dyn-rotation-policy-output.txt
- **Concern**: - **Historical changelog:** `CHANGELOG.md:1149` still names “first-tier fixer (Cursor)”; not updated in the `#3337` commit and predates this flip.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=1 Result=exonerated

### FINDING_37: [OUT_OF_SCOPE] `docs/installation-and-setup.md:189-212` still contains pre-existing broken/empty fenced-code blocks in the Cursor OAuth section; Part 1’s new Claude auth content (`134-147`) is otherwise consistent with the issue spec.
- **Reviewer**: dyn-doc-topology-output.txt
- **Concern**: - `docs/installation-and-setup.md:189-212` still contains pre-existing broken/empty fenced-code blocks in the Cursor OAuth section; Part 1’s new Claude auth content (`134-147`) is otherwise consistent with the issue spec.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted

### FINDING_38: [OUT_OF_SCOPE] Cursor-first defaults called out in the plan as intentionally unchanged (`docs/review-agents.md`, `docs/collaborative-sketches.md`, `skills/design/references/brainstorm.md`) remain cursor-first by design.
- **Reviewer**: dyn-doc-topology-output.txt
- **Concern**: - Cursor-first defaults called out in the plan as intentionally unchanged (`docs/review-agents.md`, `docs/collaborative-sketches.md`, `skills/design/references/brainstorm.md`) remain cursor-first by design.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=0 JUDGE_ERROR=1 Result=rejected

### FINDING_39: [OUT_OF_SCOPE] The branch tip includes design `larch-logs/` flush commits unrelated to #3337; the feature commit itself is the 15-file `3a76166c9` diff reviewed above.
- **Reviewer**: dyn-doc-topology-output.txt
- **Concern**: - The branch tip includes design `larch-logs/` flush commits unrelated to #3337; the feature commit itself is the 15-file `3a76166c9` diff reviewed above.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=1 Result=exonerated

### FINDING_4: [OUT_OF_SCOPE] correctness
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 1. **correctness** `CHANGELOG.md:44` — Unreleased still documents omitted `--coder` as “Cursor → Codex → Claude” while runtime and `SECURITY.md` now say Codex-first. The #3337 commit did not update that bullet (only added a #3338 entry). **Suggested fix:** When cutting the #3337 release note, rewrite line 44 to Codex → Cursor → Claude (or fold into the versioned entry for 47.0.42+).
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted

### FINDING_5: [OUT_OF_SCOPE] architecture
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 2. **architecture** `scripts/ship-pr.sh:3390-3401` — The legacy `run_rebase_rebump` conflict block still picks at most one vendor (`codex` if on `PATH`, else `cursor`) with no tier waterfall on failure; the full Codex→Cursor→Claude path is `run_recovery_waterfall` only. Pre-existing; not introduced by this branch.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted

### FINDING_6: [OUT_OF_SCOPE] correctness
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 3. **correctness** `SECURITY.md:105` — Still says explicit `--coder=cursor` / `--coder=codex` “fail closed” when unavailable; #3207 explicit waterfalls were not part of this diff. Pre-existing doc inaccuracy. --- **Verdict:** #3337 implementation is **correct and complete** relative to the plan. Safe to merge from a correctness standpoint once the usual harnesses (`test-implement-step2-routing.sh`, `test-ship-pr.sh`, `make py-test`) are green in CI. Consider updating the Unreleased `CHANGELOG.md` bullet before release to avoid operator confusion.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted

### FINDING_9: risk-integration: python/test_ci_monitor.py:943-944
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] test_evaluate_failure_verify_failed_then_pushed checks launch count only not tier order. Wrong FIXER_TIER_ORDER rotation might not fail despite codex/cursor commit mocks keyed to attempt order. Assert launch_calls == ["codex", "cursor"].
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

