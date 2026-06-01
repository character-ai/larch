### FINDING_1: code-quality: CHANGELOG.md:57-63
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] #3337 Codex-first behavior change has no CHANGELOG entry; 47.0.42 only documents #3338. Operators or release consumers read 47.0.42 notes and miss that omitted --coder and CI/merge fixers now prefer Codex over Cursor. Add a Changed bullet for #3337 under the appropriate version section (47.0.42 or next bump).
- **Suggested revision**: Address the concern above.


### FINDING_16: risk-integration: CHANGELOG.md:46
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Unreleased Changed bullet still says Cursor-first omitted-coder routing. Release prep or contributors follow CHANGELOG and document wrong default vs code. Update Unreleased #3337 entry; fix line 46 to Codex-first wording.
- **Suggested revision**: Address the concern above.


### FINDING_17: architecture: scripts/ship-pr.sh:3390-3401
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] run_rebase_rebump inline conflict launcher flipped to codex-first without dedicated test. Inline single-shot path regresses to cursor-first silently for conflicts that skip recovery waterfall. Add launcher-order regression or document inline vs waterfall paths in ship-pr.md.
- **Suggested revision**: Address the concern above.


### FINDING_2: code-quality: docs/installation-and-setup.md:124
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Stale instruction to replace <your-API-key> in settings.json conflicts with apiKeyHelper-free JSON and env/alias guidance. New readers may still put API keys in settings.json despite the new apiKeyHelper removal section. Reword the bullet to reference ANTHROPIC_API_KEY in the shell env only, or remove the placeholder from the settings.json step.
- **Suggested revision**: Address the concern above.


### FINDING_20: correctness: branch vs main (commits aef717bf1 + design larch-logs)
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Branch diff includes #3338 test-plan-review-loop fix, version 47.0.42 bump, CHANGELOG, and implement larch-logs not in the #3337 plan. Reviewers and merge history conflate two issues; failures or version changes may be mis-attributed to #3337. Isolate #3337 to commit 3a76166c9 (or rebase) so the PR diff matches the implementation plan scope.
- **Suggested revision**: Address the concern above.


### FINDING_27: **risk-integration** `CHANGELOG.md:46` — The Unreleased “Changed” bullet still documents omitted `--coder` as **Cursor → Codex → Claude**, while commit `3a76166c9` flips live routing and synced docs (`SECURITY.md`, `implement-bootstrap.md`, `ship-pr.sh`, `skills/implement/SKILL.md`) to **Codex → Cursor → Claude**. That mismatch is easy to hit when debugging CI-fix rotation or `first-fixer-non-health`, because the changelog still implies Cursor is the default first CI-fixer tier on `_fix_attempt=0`. **Suggested fix:** Update the Unreleased bullet (and add a `#3337` entry when you cut the release) so implementer and CI-fixer default order match runtime and `scripts/ship-pr.md:152-154`.
- **Reviewer**: dyn-rotation-policy-output.txt
- **Concern**: - **risk-integration** `CHANGELOG.md:46` — The Unreleased “Changed” bullet still documents omitted `--coder` as **Cursor → Codex → Claude**, while commit `3a76166c9` flips live routing and synced docs (`SECURITY.md`, `implement-bootstrap.md`, `ship-pr.sh`, `skills/implement/SKILL.md`) to **Codex → Cursor → Claude**. That mismatch is easy to hit when debugging CI-fix rotation or `first-fixer-non-health`, because the changelog still implies Cursor is the default first CI-fixer tier on `_fix_attempt=0`. **Suggested fix:** Update the Unreleased bullet (and add a `#3337` entry when you cut the release) so implementer and CI-fixer default order match runtime and `scripts/ship-pr.md:152-154`.
- **Suggested revision**: Address the concern above.


### FINDING_28: **risk-integration** `scripts/test-ship-pr.sh`, `scripts/test-ship-pr-fix-loop-2632.inc.sh` — Order-sensitive regressions cover `start_attempt=0` (direct `run_ci_fix_vendor … 0` and full-ship `t4`–`t4d`), but nothing drives `run_ci_fix_vendor` with `start_attempt=1` where `first_tier=${tiers[1]}` is **cursor** after the base-order flip. The live gate at `scripts/ship-pr.sh:2069-2121` keys off `tier="$first_tier"` and `waterfall_iter=0`; outer `run_evaluate_failure` passes `_fix_attempt` through at `2638`/`2659`, so retry-1 autonomous bail semantics are unguarded. **Suggested fix:** Add a harness case (stub Codex health-fail or success-skip, Cursor `LAUNCHER_FAILURE_CLASS=other`, assert exit 3, `BAIL_REASON=first-fixer-non-health`, and a single Cursor launch) mirroring `run_ship_pr_2632_t4` but with `_fix_attempt=1` / `start_attempt=1`.
- **Reviewer**: dyn-rotation-policy-output.txt
- **Concern**: - **risk-integration** `scripts/test-ship-pr.sh`, `scripts/test-ship-pr-fix-loop-2632.inc.sh` — Order-sensitive regressions cover `start_attempt=0` (direct `run_ci_fix_vendor … 0` and full-ship `t4`–`t4d`), but nothing drives `run_ci_fix_vendor` with `start_attempt=1` where `first_tier=${tiers[1]}` is **cursor** after the base-order flip. The live gate at `scripts/ship-pr.sh:2069-2121` keys off `tier="$first_tier"` and `waterfall_iter=0`; outer `run_evaluate_failure` passes `_fix_attempt` through at `2638`/`2659`, so retry-1 autonomous bail semantics are unguarded. **Suggested fix:** Add a harness case (stub Codex health-fail or success-skip, Cursor `LAUNCHER_FAILURE_CLASS=other`, assert exit 3, `BAIL_REASON=first-fixer-non-health`, and a single Cursor launch) mirroring `run_ship_pr_2632_t4` but with `_fix_attempt=1` / `start_attempt=1`.
- **Suggested revision**: Address the concern above.


### FINDING_3: code-quality: scripts/ship-pr.sh:3390-3401
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Legacy single-launcher conflict resolution prefers Codex first but ship-pr.md only documents the three-tier waterfall order. Debugging a path that uses the legacy launcher without reading run_recovery_waterfall may assume Cursor-first ordering. Document the legacy codex-then-cursor launcher in scripts/ship-pr.md next to the recovery waterfall section.
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


### FINDING_7: risk-integration: CHANGELOG.md:46
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Unreleased Changed bullet still says omitted --coder uses Cursor → Codex → Claude after #3337 flipped runtime and SECURITY.md to Codex-first. Release notes and operator expectations contradict live phase_coder_select / fixer behavior; no harness greps CHANGELOG routing prose. Update the Unreleased bullet to Codex → Cursor → Claude or add a versioned #3337 entry when bumping plugin version.
- **Suggested revision**: Address the concern above.


### FINDING_8: risk-integration: scripts/test-ship-pr.sh:4681-4684
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Multi-tier CI-fix cases assert both launchers appear but not invocation order. Cursor-first regression in run_ci_fix_vendor could still pass falls_through_to_cursor / t4b-style cases. Assert launcher-calls line count and first line launch-codex-ci.sh before launch-cursor-ci.sh.
- **Suggested revision**: Address the concern above.


