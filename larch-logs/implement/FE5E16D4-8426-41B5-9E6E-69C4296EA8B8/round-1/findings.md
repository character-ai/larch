### FINDING_1: code-quality: CHANGELOG.md:57-63
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] #3337 Codex-first behavior change has no CHANGELOG entry; 47.0.42 only documents #3338. Operators or release consumers read 47.0.42 notes and miss that omitted --coder and CI/merge fixers now prefer Codex over Cursor. Add a Changed bullet for #3337 under the appropriate version section (47.0.42 or next bump).
- **Suggested revision**: Address the concern above.

### FINDING_2: code-quality: docs/installation-and-setup.md:124
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Stale instruction to replace <your-API-key> in settings.json conflicts with apiKeyHelper-free JSON and env/alias guidance. New readers may still put API keys in settings.json despite the new apiKeyHelper removal section. Reword the bullet to reference ANTHROPIC_API_KEY in the shell env only, or remove the placeholder from the settings.json step.
- **Suggested revision**: Address the concern above.

### FINDING_3: code-quality: scripts/ship-pr.sh:3390-3401
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Legacy single-launcher conflict resolution prefers Codex first but ship-pr.md only documents the three-tier waterfall order. Debugging a path that uses the legacy launcher without reading run_recovery_waterfall may assume Cursor-first ordering. Document the legacy codex-then-cursor launcher in scripts/ship-pr.md next to the recovery waterfall section.
- **Suggested revision**: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] correctness
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 1. **correctness** `CHANGELOG.md:44` — Unreleased still documents omitted `--coder` as “Cursor → Codex → Claude” while runtime and `SECURITY.md` now say Codex-first. The #3337 commit did not update that bullet (only added a #3338 entry). **Suggested fix:** When cutting the #3337 release note, rewrite line 44 to Codex → Cursor → Claude (or fold into the versioned entry for 47.0.42+).
- **Suggested revision**: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] architecture
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 2. **architecture** `scripts/ship-pr.sh:3390-3401` — The legacy `run_rebase_rebump` conflict block still picks at most one vendor (`codex` if on `PATH`, else `cursor`) with no tier waterfall on failure; the full Codex→Cursor→Claude path is `run_recovery_waterfall` only. Pre-existing; not introduced by this branch.
- **Suggested revision**: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] correctness
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 3. **correctness** `SECURITY.md:105` — Still says explicit `--coder=cursor` / `--coder=codex` “fail closed” when unavailable; #3207 explicit waterfalls were not part of this diff. Pre-existing doc inaccuracy. --- **Verdict:** #3337 implementation is **correct and complete** relative to the plan. Safe to merge from a correctness standpoint once the usual harnesses (`test-implement-step2-routing.sh`, `test-ship-pr.sh`, `make py-test`) are green in CI. Consider updating the Unreleased `CHANGELOG.md` bullet before release to avoid operator confusion.
- **Suggested revision**: Address the concern above.

### FINDING_7: risk-integration: CHANGELOG.md:46
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Unreleased Changed bullet still says omitted --coder uses Cursor → Codex → Claude after #3337 flipped runtime and SECURITY.md to Codex-first. Release notes and operator expectations contradict live phase_coder_select / fixer behavior; no harness greps CHANGELOG routing prose. Update the Unreleased bullet to Codex → Cursor → Claude or add a versioned #3337 entry when bumping plugin version.
- **Suggested revision**: Address the concern above.

### FINDING_8: risk-integration: scripts/test-ship-pr.sh:4681-4684
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Multi-tier CI-fix cases assert both launchers appear but not invocation order. Cursor-first regression in run_ci_fix_vendor could still pass falls_through_to_cursor / t4b-style cases. Assert launcher-calls line count and first line launch-codex-ci.sh before launch-cursor-ci.sh.
- **Suggested revision**: Address the concern above.

### FINDING_9: risk-integration: python/test_ci_monitor.py:943-944
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] test_evaluate_failure_verify_failed_then_pushed checks launch count only not tier order. Wrong FIXER_TIER_ORDER rotation might not fail despite codex/cursor commit mocks keyed to attempt order. Assert launch_calls == ["codex", "cursor"].
- **Suggested revision**: Address the concern above.

### FINDING_10: risk-integration: scripts/implement-bootstrap.sh:681-710
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] No offline test exercises _phase_coder_implicit PATH availability probing. Swapped codex/cursor branches could regress with only static string pins staying green. Add PATH-stubbed implement-bootstrap --up-to-phase coder cases asserting coder= and coder_fallback= KV output.
- **Suggested revision**: Address the concern above.

### FINDING_11: risk-integration: scripts/test-implement-step2-routing.md:7
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Harness doc still documents Cursor-first omitted --coder waterfall. Contributors reading the harness .md get the wrong contract though .sh pins were updated. Change line 7 to Codex → Cursor → Claude to match test-implement-step2-routing.sh.
- **Suggested revision**: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] risk-integration: skills/design/scripts/test-plan-review-loop.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] #3338 PATH STUB_BIN backstop is bundled on the branch but outside #3337 scope. Improves make lint hermeticity when externals are installed; unrelated to codex-first defaults. No action required for #3337; keep as separate fix.
- **Suggested revision**: Address the concern above.

### FINDING_13: [OUT_OF_SCOPE] risk-integration: CHANGELOG.md:55-63
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Released 47.0.42 changelog covers #3338 only not #3337. Consumers may not see #3337 in shipped notes until a later bump commit. Add #3337 bullets when version is bumped for this feature.
- **Suggested revision**: Address the concern above.

### FINDING_14: security: docs/installation-and-setup.md:139-140
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Documented apiKeyHelper uses echo $ANTHROPIC_API_KEY without quoting. A malicious or malformed ANTHROPIC_API_KEY value (e.g. containing $(cmd) or unescaped quotes) executed when Claude runs apiKeyHelper from *_api aliases could run arbitrary shell commands on the operator machine. Use printf '%s\n' "$ANTHROPIC_API_KEY" in a tiny wrapper script referenced by apiKeyHelper, or document that keys must be shell-safe single-line tokens.
- **Suggested revision**: Address the concern above.

### FINDING_15: risk-integration: scripts/ship-pr.sh:2039-2125
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] CI fix vendor order ignores Step 0 codex_available; always tries Codex first even when implementer already fell back to Cursor. Probe-failed Codex + healthy Cursor: /implement uses Cursor implementer then CI fix wastes first attempt on Codex before Cursor. Thread session availability into run_ci_fix_vendor tier selection or align base tuple with resolved coder.
- **Suggested revision**: Address the concern above.

### FINDING_16: risk-integration: CHANGELOG.md:46
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Unreleased Changed bullet still says Cursor-first omitted-coder routing. Release prep or contributors follow CHANGELOG and document wrong default vs code. Update Unreleased #3337 entry; fix line 46 to Codex-first wording.
- **Suggested revision**: Address the concern above.

### FINDING_17: architecture: scripts/ship-pr.sh:3390-3401
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] run_rebase_rebump inline conflict launcher flipped to codex-first without dedicated test. Inline single-shot path regresses to cursor-first silently for conflicts that skip recovery waterfall. Add launcher-order regression or document inline vs waterfall paths in ship-pr.md.
- **Suggested revision**: Address the concern above.

### FINDING_18: [OUT_OF_SCOPE] architecture: scripts/ship-pr.sh:2069-2122
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] first-fixer bail can miss when rotated first tier is skipped (e.g. missing launch-claude-ci.sh). start_attempt=2 with Claude first skipped: later tier other-class does not short-circuit to exit 3. Fix waterfall_iter/first_tier coupling separately from #3337.
- **Suggested revision**: Address the concern above.

### FINDING_19: [OUT_OF_SCOPE] risk-integration: SECURITY.md:105
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Explicit --coder fail-closed wording predates #3207 waterfall. Operators expect hard bail on unavailable pinned coder. Sync SECURITY.md with #3207 waterfall semantics in a dedicated doc fix.
- **Suggested revision**: Address the concern above.

### FINDING_20: correctness: branch vs main (commits aef717bf1 + design larch-logs)
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Branch diff includes #3338 test-plan-review-loop fix, version 47.0.42 bump, CHANGELOG, and implement larch-logs not in the #3337 plan. Reviewers and merge history conflate two issues; failures or version changes may be mis-attributed to #3337. Isolate #3337 to commit 3a76166c9 (or rebase) so the PR diff matches the implementation plan scope.
- **Suggested revision**: Address the concern above.

### FINDING_21: [OUT_OF_SCOPE] architecture: CHANGELOG.md
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] CHANGELOG may still document Cursor-first omitted --coder routing; plan did not require updating it in this issue. Operators reading only CHANGELOG could see stale routing until the next version entry. Add a CHANGELOG bullet when the version bump lands for #3337 (if not handled by bump-version Step 8).
- **Suggested revision**: Address the concern above.

### FINDING_22: **correctness** `python/test_ci_monitor.py:943-944` — `test_evaluate_failure_verify_failed_then_pushed` was retargeted for codex-first rotation (commit-message mocks and comment at 901–903) but still only asserts `len(launch_calls) == 2`, not tier order. A regression that invoked Codex twice (or Cursor twice) on the verify-failed retry path would still pass, so Python parity with Bash `run_ci_fix_vendor` rotation (`start_attempt` 0 → codex, 1 → cursor) is not mechanically pinned. **Suggested fix:** Add `assert launch_calls == ["codex", "cursor"]` (or the exact sequence your scenario intends) so outer-attempt rotation stays locked to `FIXER_TIER_ORDER` after the #3337 flip.
- **Reviewer**: dyn-waterfall-routing-output.txt
- **Concern**: - **correctness** `python/test_ci_monitor.py:943-944` — `test_evaluate_failure_verify_failed_then_pushed` was retargeted for codex-first rotation (commit-message mocks and comment at 901–903) but still only asserts `len(launch_calls) == 2`, not tier order. A regression that invoked Codex twice (or Cursor twice) on the verify-failed retry path would still pass, so Python parity with Bash `run_ci_fix_vendor` rotation (`start_attempt` 0 → codex, 1 → cursor) is not mechanically pinned. **Suggested fix:** Add `assert launch_calls == ["codex", "cursor"]` (or the exact sequence your scenario intends) so outer-attempt rotation stays locked to `FIXER_TIER_ORDER` after the #3337 flip.
- **Suggested revision**: Address the concern above.

### FINDING_23: [OUT_OF_SCOPE] Runtime waterfall changes look internally consistent on this branch: `_phase_coder_implicit` probes Codex then Cursor then Claude (`scripts/implement-bootstrap.sh:1257-1270`); explicit `--coder` waterfalls in `_phase_coder_explicit` / `_phase_coder_explicit_waterfall` are unchanged; `run_ci_fix_vendor` uses `tiers=(codex cursor claude)` with `first_tier=${tiers[$(( start_attempt % 3 ))]}` (`scripts/ship-pr.sh:2039-2072, 2115-2121`); `run_recovery_waterfall` iterates `codex cursor claude` (`scripts/ship-pr.sh:2815-2826`); the legacy single-vendor rebase path prefers Codex over Cursor (`scripts/ship-pr.sh:3390-3401`); Python `FIXER_TIER_ORDER` and `agents.run_waterfall` rotation match Bash (`python/config.py:30`, `python/ci_monitor.py:912-916`, `python/agents.py:244-246`).
- **Reviewer**: dyn-waterfall-routing-output.txt
- **Concern**: - Runtime waterfall changes look internally consistent on this branch: `_phase_coder_implicit` probes Codex then Cursor then Claude (`scripts/implement-bootstrap.sh:1257-1270`); explicit `--coder` waterfalls in `_phase_coder_explicit` / `_phase_coder_explicit_waterfall` are unchanged; `run_ci_fix_vendor` uses `tiers=(codex cursor claude)` with `first_tier=${tiers[$(( start_attempt % 3 ))]}` (`scripts/ship-pr.sh:2039-2072, 2115-2121`); `run_recovery_waterfall` iterates `codex cursor claude` (`scripts/ship-pr.sh:2815-2826`); the legacy single-vendor rebase path prefers Codex over Cursor (`scripts/ship-pr.sh:3390-3401`); Python `FIXER_TIER_ORDER` and `agents.run_waterfall` rotation match Bash (`python/config.py:30`, `python/ci_monitor.py:912-916`, `python/agents.py:244-246`).
- **Suggested revision**: Address the concern above.

### FINDING_24: [OUT_OF_SCOPE] `CHANGELOG.md:44` (Unreleased) still documents omitted-`--coder` as **Cursor → Codex → Claude** while live code and `SECURITY.md` now say Codex-first; the branch adds a `47.0.42` entry for #3338 but no Unreleased/released note for #3337.
- **Reviewer**: dyn-waterfall-routing-output.txt
- **Concern**: - `CHANGELOG.md:44` (Unreleased) still documents omitted-`--coder` as **Cursor → Codex → Claude** while live code and `SECURITY.md` now say Codex-first; the branch adds a `47.0.42` entry for #3338 but no Unreleased/released note for #3337.
- **Suggested revision**: Address the concern above.

### FINDING_25: [OUT_OF_SCOPE] `scripts/test-implement-step2-routing.md:7` still says **Cursor → Codex → Claude**; the `.sh` harness and `implement-bootstrap.md` were updated, but the sibling contract doc was not (not CI-gated).
- **Reviewer**: dyn-waterfall-routing-output.txt
- **Concern**: - `scripts/test-implement-step2-routing.md:7` still says **Cursor → Codex → Claude**; the `.sh` harness and `implement-bootstrap.md` were updated, but the sibling contract doc was not (not CI-gated).
- **Suggested revision**: Address the concern above.

### FINDING_26: [OUT_OF_SCOPE] Branch tip includes unrelated commits (`#3338` plan-review-loop hang fix, several `larch-logs` flushes); waterfall review above targets the #3337 routing surfaces in the precomputed diff.
- **Reviewer**: dyn-waterfall-routing-output.txt
- **Concern**: - Branch tip includes unrelated commits (`#3338` plan-review-loop hang fix, several `larch-logs` flushes); waterfall review above targets the #3337 routing surfaces in the precomputed diff.
- **Suggested revision**: Address the concern above.

### FINDING_27: **risk-integration** `CHANGELOG.md:46` — The Unreleased “Changed” bullet still documents omitted `--coder` as **Cursor → Codex → Claude**, while commit `3a76166c9` flips live routing and synced docs (`SECURITY.md`, `implement-bootstrap.md`, `ship-pr.sh`, `skills/implement/SKILL.md`) to **Codex → Cursor → Claude**. That mismatch is easy to hit when debugging CI-fix rotation or `first-fixer-non-health`, because the changelog still implies Cursor is the default first CI-fixer tier on `_fix_attempt=0`. **Suggested fix:** Update the Unreleased bullet (and add a `#3337` entry when you cut the release) so implementer and CI-fixer default order match runtime and `scripts/ship-pr.md:152-154`.
- **Reviewer**: dyn-rotation-policy-output.txt
- **Concern**: - **risk-integration** `CHANGELOG.md:46` — The Unreleased “Changed” bullet still documents omitted `--coder` as **Cursor → Codex → Claude**, while commit `3a76166c9` flips live routing and synced docs (`SECURITY.md`, `implement-bootstrap.md`, `ship-pr.sh`, `skills/implement/SKILL.md`) to **Codex → Cursor → Claude**. That mismatch is easy to hit when debugging CI-fix rotation or `first-fixer-non-health`, because the changelog still implies Cursor is the default first CI-fixer tier on `_fix_attempt=0`. **Suggested fix:** Update the Unreleased bullet (and add a `#3337` entry when you cut the release) so implementer and CI-fixer default order match runtime and `scripts/ship-pr.md:152-154`.
- **Suggested revision**: Address the concern above.

### FINDING_28: **risk-integration** `scripts/test-ship-pr.sh`, `scripts/test-ship-pr-fix-loop-2632.inc.sh` — Order-sensitive regressions cover `start_attempt=0` (direct `run_ci_fix_vendor … 0` and full-ship `t4`–`t4d`), but nothing drives `run_ci_fix_vendor` with `start_attempt=1` where `first_tier=${tiers[1]}` is **cursor** after the base-order flip. The live gate at `scripts/ship-pr.sh:2069-2121` keys off `tier="$first_tier"` and `waterfall_iter=0`; outer `run_evaluate_failure` passes `_fix_attempt` through at `2638`/`2659`, so retry-1 autonomous bail semantics are unguarded. **Suggested fix:** Add a harness case (stub Codex health-fail or success-skip, Cursor `LAUNCHER_FAILURE_CLASS=other`, assert exit 3, `BAIL_REASON=first-fixer-non-health`, and a single Cursor launch) mirroring `run_ship_pr_2632_t4` but with `_fix_attempt=1` / `start_attempt=1`.
- **Reviewer**: dyn-rotation-policy-output.txt
- **Concern**: - **risk-integration** `scripts/test-ship-pr.sh`, `scripts/test-ship-pr-fix-loop-2632.inc.sh` — Order-sensitive regressions cover `start_attempt=0` (direct `run_ci_fix_vendor … 0` and full-ship `t4`–`t4d`), but nothing drives `run_ci_fix_vendor` with `start_attempt=1` where `first_tier=${tiers[1]}` is **cursor** after the base-order flip. The live gate at `scripts/ship-pr.sh:2069-2121` keys off `tier="$first_tier"` and `waterfall_iter=0`; outer `run_evaluate_failure` passes `_fix_attempt` through at `2638`/`2659`, so retry-1 autonomous bail semantics are unguarded. **Suggested fix:** Add a harness case (stub Codex health-fail or success-skip, Cursor `LAUNCHER_FAILURE_CLASS=other`, assert exit 3, `BAIL_REASON=first-fixer-non-health`, and a single Cursor launch) mirroring `run_ship_pr_2632_t4` but with `_fix_attempt=1` / `start_attempt=1`.
- **Suggested revision**: Address the concern above.

### FINDING_29: [OUT_OF_SCOPE] **Pre-existing `waterfall_iter` vs skipped Claude launcher:** In `scripts/ship-pr.sh:2073-2078`, an unavailable `launch-claude-ci.sh` increments `waterfall_iter` before any launcher runs. When outer rotation starts at `claude` (`start_attempt=2`), a later tier’s `other` failure may not satisfy `waterfall_iter -eq 0` at `2115-2121`, so `first-fixer-non-health` may not fire even though docs describe “rotated first tier” policy (`scripts/ship-pr.md:152-154`). Not introduced by the tuple flip; same structure existed cursor-first.
- **Reviewer**: dyn-rotation-policy-output.txt
- **Concern**: - **Pre-existing `waterfall_iter` vs skipped Claude launcher:** In `scripts/ship-pr.sh:2073-2078`, an unavailable `launch-claude-ci.sh` increments `waterfall_iter` before any launcher runs. When outer rotation starts at `claude` (`start_attempt=2`), a later tier’s `other` failure may not satisfy `waterfall_iter -eq 0` at `2115-2121`, so `first-fixer-non-health` may not fire even though docs describe “rotated first tier” policy (`scripts/ship-pr.md:152-154`). Not introduced by the tuple flip; same structure existed cursor-first.
- **Suggested revision**: Address the concern above.

### FINDING_30: [OUT_OF_SCOPE] **Pre-existing #3134 “no commit” bail:** `scripts/ship-pr.sh:2144-2166` classifies `first-fixer-non-health` from the **winning** tier after staging, not from `first_tier` of the rotated list. That is separate from the `LAUNCHER_FAILURE_CLASS=other` short-circuit and unchanged by this branch.
- **Reviewer**: dyn-rotation-policy-output.txt
- **Concern**: - **Pre-existing #3134 “no commit” bail:** `scripts/ship-pr.sh:2144-2166` classifies `first-fixer-non-health` from the **winning** tier after staging, not from `first_tier` of the rotated list. That is separate from the `LAUNCHER_FAILURE_CLASS=other` short-circuit and unchanged by this branch.
- **Suggested revision**: Address the concern above.

### FINDING_31: [OUT_OF_SCOPE] **Python parity (Phase 7):** `python/ci_monitor.py:912` rotates with `start_attempt % len(tiers)` while Bash always uses `% 3` on a fixed triple; only `FIXER_TIER_ORDER` changed here. Live path remains Bash until Phase 7.
- **Reviewer**: dyn-rotation-policy-output.txt
- **Concern**: - **Python parity (Phase 7):** `python/ci_monitor.py:912` rotates with `start_attempt % len(tiers)` while Bash always uses `% 3` on a fixed triple; only `FIXER_TIER_ORDER` changed here. Live path remains Bash until Phase 7.
- **Suggested revision**: Address the concern above.

### FINDING_32: [OUT_OF_SCOPE] **Historical changelog:** `CHANGELOG.md:1149` still names “first-tier fixer (Cursor)”; not updated in the `#3337` commit and predates this flip.
- **Reviewer**: dyn-rotation-policy-output.txt
- **Concern**: - **Historical changelog:** `CHANGELOG.md:1149` still names “first-tier fixer (Cursor)”; not updated in the `#3337` commit and predates this flip.
- **Suggested revision**: Address the concern above.

### FINDING_33: **code-quality** `CHANGELOG.md:46` — The `[Unreleased]` bullet still documents omitted-`--coder` as a **Cursor → Codex → Claude** waterfall and claims cross-doc parity with `SECURITY.md` and `docs/linting.md`, but commit `3a76166c9` flipped runtime and those docs to **Codex → Cursor → Claude** without updating this entry or adding any shipped note for #3337 (HEAD sits on `47.0.42`, which only records #3338). Operators reading `[Unreleased]` get the opposite routing contract from the live scripts and synced security/linting docs. **Suggested fix:** Rewrite line 46 to Codex-first (or remove/supersede it) and add a `### Changed` entry for #3337### In-Scope Findings
- **Reviewer**: dyn-doc-topology-output.txt
- **Concern**: - **code-quality** `CHANGELOG.md:46` — The `[Unreleased]` bullet still documents omitted-`--coder` as a **Cursor → Codex → Claude** waterfall and claims cross-doc parity with `SECURITY.md` and `docs/linting.md`, but commit `3a76166c9` flipped runtime and those docs to **Codex → Cursor → Claude** without updating this entry or adding any shipped note for #3337 (HEAD sits on `47.0.42`, which only records #3338). Operators reading `[Unreleased]` get the opposite routing contract from the live scripts and synced security/linting docs. **Suggested fix:** Rewrite line 46 to Codex-first (or remove/supersede it) and add a `### Changed` entry for #3337### In-Scope Findings
- **Suggested revision**: Address the concern above.

### FINDING_34: **code-quality** `CHANGELOG.md:46` — The `[Unreleased]` bullet still documents omitted-`--coder` as a **Cursor → Codex → Claude** waterfall and claims cross-doc parity with `SECURITY.md` / `docs/linting.md`, but commit `3a76166c9` flipped runtime and those docs to **Codex → Cursor → Claude**. There is also no shipped `[47.x.x]` entry for #3337 (only #3338 appears under `[47.0.42]`), so the behavioral change ships without a user-facing release note and the Unreleased section actively contradicts live behavior. **Suggested fix:** Update or remove the stale `[Unreleased]` bullet to Codex-first wording, and add a versioned `### Changed` entry for #3337 (apiKeyHelper install guidance + Codex-first coder/CI/merge-fixer defaults) when the plugin version is next bumped.
- **Reviewer**: dyn-doc-topology-output.txt
- **Concern**: - **code-quality** `CHANGELOG.md:46` — The `[Unreleased]` bullet still documents omitted-`--coder` as a **Cursor → Codex → Claude** waterfall and claims cross-doc parity with `SECURITY.md` / `docs/linting.md`, but commit `3a76166c9` flipped runtime and those docs to **Codex → Cursor → Claude**. There is also no shipped `[47.x.x]` entry for #3337 (only #3338 appears under `[47.0.42]`), so the behavioral change ships without a user-facing release note and the Unreleased section actively contradicts live behavior. **Suggested fix:** Update or remove the stale `[Unreleased]` bullet to Codex-first wording, and add a versioned `### Changed` entry for #3337 (apiKeyHelper install guidance + Codex-first coder/CI/merge-fixer defaults) when the plugin version is next bumped.
- **Suggested revision**: Address the concern above.

### FINDING_35: **code-quality** `scripts/test-implement-step2-routing.md:6-7` — The harness markdown still pins “waterfall order (Cursor → Codex → Claude)” even though `scripts/test-implement-step2-routing.sh`, `scripts/implement-bootstrap.md`, and `docs/linting.md` were updated to Codex-first. `scripts/implement-bootstrap.md:169` lists this `.md` in its **Edit-in-sync** contract, so the miss is a documented sync obligation, not an optional doc. CI does not assert this file, so the drift will not fail `make test-implement-step2-routing`. **Suggested fix:** Reword line 7 to `Codex → Cursor → Claude` (matching `docs/linting.md:272`) and optionally add a harness assertion on `scripts/test-implement-step2-routing.md` to prevent recurrence.
- **Reviewer**: dyn-doc-topology-output.txt
- **Concern**: - **code-quality** `scripts/test-implement-step2-routing.md:6-7` — The harness markdown still pins “waterfall order (Cursor → Codex → Claude)” even though `scripts/test-implement-step2-routing.sh`, `scripts/implement-bootstrap.md`, and `docs/linting.md` were updated to Codex-first. `scripts/implement-bootstrap.md:169` lists this `.md` in its **Edit-in-sync** contract, so the miss is a documented sync obligation, not an optional doc. CI does not assert this file, so the drift will not fail `make test-implement-step2-routing`. **Suggested fix:** Reword line 7 to `Codex → Cursor → Claude` (matching `docs/linting.md:272`) and optionally add a harness assertion on `scripts/test-implement-step2-routing.md` to prevent recurrence.
- **Suggested revision**: Address the concern above.

### FINDING_36: **code-quality** `scripts/launch-cursor-ci.md:30` — Machine-readable failure-class prose still says `ship-pr.sh` may short-circuit the **Cursor→Codex→Claude** waterfall on first-tier non-health failures, but `run_ci_fix_vendor` now uses `(codex cursor claude)` and `scripts/ship-pr.md:72,118` were updated to **rotated-first-tier / Codex on `start_attempt=0`** language. Operators debugging Exit 3 / `first-fixer-non-health` from the Cursor launcher doc will misidentify which tier triggers the bail. **Suggested fix:** Replace the hard-coded tier order with rotated-first-tier wording aligned with `scripts/ship-pr.md` (e.g., “short-circuit the codex→cursor→claude waterfall when the rotated first tier reports `LAUNCHER_FAILURE_CLASS=other`”).
- **Reviewer**: dyn-doc-topology-output.txt
- **Concern**: - **code-quality** `scripts/launch-cursor-ci.md:30` — Machine-readable failure-class prose still says `ship-pr.sh` may short-circuit the **Cursor→Codex→Claude** waterfall on first-tier non-health failures, but `run_ci_fix_vendor` now uses `(codex cursor claude)` and `scripts/ship-pr.md:72,118` were updated to **rotated-first-tier / Codex on `start_attempt=0`** language. Operators debugging Exit 3 / `first-fixer-non-health` from the Cursor launcher doc will misidentify which tier triggers the bail. **Suggested fix:** Replace the hard-coded tier order with rotated-first-tier wording aligned with `scripts/ship-pr.md` (e.g., “short-circuit the codex→cursor→claude waterfall when the rotated first tier reports `LAUNCHER_FAILURE_CLASS=other`”).
- **Suggested revision**: Address the concern above.

### FINDING_37: [OUT_OF_SCOPE] `docs/installation-and-setup.md:189-212` still contains pre-existing broken/empty fenced-code blocks in the Cursor OAuth section; Part 1’s new Claude auth content (`134-147`) is otherwise consistent with the issue spec.
- **Reviewer**: dyn-doc-topology-output.txt
- **Concern**: - `docs/installation-and-setup.md:189-212` still contains pre-existing broken/empty fenced-code blocks in the Cursor OAuth section; Part 1’s new Claude auth content (`134-147`) is otherwise consistent with the issue spec.
- **Suggested revision**: Address the concern above.

### FINDING_38: [OUT_OF_SCOPE] Cursor-first defaults called out in the plan as intentionally unchanged (`docs/review-agents.md`, `docs/collaborative-sketches.md`, `skills/design/references/brainstorm.md`) remain cursor-first by design.
- **Reviewer**: dyn-doc-topology-output.txt
- **Concern**: - Cursor-first defaults called out in the plan as intentionally unchanged (`docs/review-agents.md`, `docs/collaborative-sketches.md`, `skills/design/references/brainstorm.md`) remain cursor-first by design.
- **Suggested revision**: Address the concern above.

### FINDING_39: [OUT_OF_SCOPE] The branch tip includes design `larch-logs/` flush commits unrelated to #3337; the feature commit itself is the 15-file `3a76166c9` diff reviewed above.
- **Reviewer**: dyn-doc-topology-output.txt
- **Concern**: - The branch tip includes design `larch-logs/` flush commits unrelated to #3337; the feature commit itself is the 15-file `3a76166c9` diff reviewed above.
- **Suggested revision**: Address the concern above.

