### FINDING_1: code-quality: skills/implement/scripts/test-implement-bootstrap.sh:881-935,1119-1188,2119-2125,2676-2694
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Offline bootstrap harness still asserts cursor-first implicit coder selection and old fallback warnings. make test-implement-bootstrap / test-harnesses-7 fails after codex-first _phase_coder_implicit (e.g. B4-all expects coder=cursor when both tools are available). Update implicit-waterfall cases and warning strings; add make test-implement-bootstrap to the issue test plan.
- **Suggested revision**: Address the concern above.

### FINDING_2: code-quality: scripts/ship-pr.sh:3385-3402
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Inline run_rebase_rebump conflict launcher order flipped without a dedicated harness. Codex-first inline resolve-conflict could regress while three-tier recovery tests stay green. Add a stubbed test that asserts launch-codex-ci before launch-cursor on the inline path.
- **Suggested revision**: Address the concern above.

### FINDING_3: code-quality: docs/installation-and-setup.md:119-147
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Intro still claims API-key-only recipes above new subscription dual-auth content. Readers may think subscription aliases contradict the section header. Reword the intro to cover both API-key and subscription setup for Claude.
- **Suggested revision**: Address the concern above.

### FINDING_4: code-quality: scripts/launch-cursor-ci.md:191-192
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] launch-codex-ci.md not synced on first-fixer / tier-order prose. Maintainers reading only the Codex launcher doc miss rotated-first-tier bail semantics. Mirror launch-cursor-ci.md first-tier language in launch-codex-ci.md per Edit In Sync.
- **Suggested revision**: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] code-quality: git log main..HEAD
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] N/A Unrelated larch-logs and #3338 commits clutter the PR diff. Filter by touched paths when reviewing; no change required for #3337 correctness.
- **Suggested revision**: Address the concern above.

### FINDING_6: **`run_ci_fix_vendor`**: `offset=$((start_attempt % 3))`, `first_tier=${tiers[$offset]}`, bail when `waterfall_iter=0`, `wrapper_rc=0`, `tier=$first_tier`, and `LAUNCHER_FAILURE_CLASS=other` — correct for codex-first base order and rotation (`t4e` covers `start_attempt=1` → Cursor as rotated first tier).
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - **`run_ci_fix_vendor`**: `offset=$((start_attempt % 3))`, `first_tier=${tiers[$offset]}`, bail when `waterfall_iter=0`, `wrapper_rc=0`, `tier=$first_tier`, and `LAUNCHER_FAILURE_CLASS=other` — correct for codex-first base order and rotation (`t4e` covers `start_attempt=1` → Cursor as rotated first tier).
- **Suggested revision**: Address the concern above.

### FINDING_7: **Python parity**: `agents.run_waterfall` short-circuit matches Bash (`idx==0`, `wrapper_rc==0`, `failure_class=="other"`).
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - **Python parity**: `agents.run_waterfall` short-circuit matches Bash (`idx==0`, `wrapper_rc==0`, `failure_class=="other"`).
- **Suggested revision**: Address the concern above.

### FINDING_8: **Explicit `--coder`**: `--coder cursor` → codex → claude; `--coder codex` → cursor → claude (unchanged).
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - **Explicit `--coder`**: `--coder cursor` → codex → claude; `--coder codex` → cursor → claude (unchanged). ---
- **Suggested revision**: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] Branch history includes many `chore(larch-logs)` commits and a version bump to `47.0.42`; per instructions, those are not flagged as scope drift.
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 1. Branch history includes many `chore(larch-logs)` commits and a version bump to `47.0.42`; per instructions, those are not flagged as scope drift.
- **Suggested revision**: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] The `### Claude` JSON example in `docs/installation-and-setup.md` still lacks a top-level `{` (pre-existing; not introduced by this change).
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 2. The `### Claude` JSON example in `docs/installation-and-setup.md` still lacks a top-level `{` (pre-existing; not introduced by this change).
- **Suggested revision**: Address the concern above.

### FINDING_11: risk-integration: skills/implement/scripts/test-implement-bootstrap.sh:1119-1187
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] B5-coder-implicit-* cases still assert Cursor-first coder selection and old fallback warnings make lint runs test-implement-bootstrap on harness-15; B5-coder-implicit-cursor expects coder=cursor when both tools are healthy, and sibling cases expect pre-#3337 warning text, so CI fails after the bootstrap.sh flip Rework B5-coder-implicit-cursor/codex/claude for Codex-first probes and new warning strings; run make test-implement-bootstrap
- **Suggested revision**: Address the concern above.

### FINDING_12: risk-integration: scripts/ship-pr.sh:3385-3401
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] No harness pins inline 600s codex-first rebase conflict launcher Recovery-waterfall tests cover codex-first at 1800s; inline launch-codex-ci.sh --timeout 600 when both binaries exist is untested and could regress to cursor-first silently Add a test-ship-pr.sh fixture that hits skip_vendor=false inline path and asserts launch-codex-ci.sh with --timeout 600 before any cursor launcher
- **Suggested revision**: Address the concern above.

### FINDING_13: risk-integration: scripts/test-ship-pr.sh:2155,2212
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Stale 600s timeout comments on cases that use recovery waterfall Maintainers may edit the wrong code path when fixing timeout regressions Reword comments to recovery-waterfall / 1800s to match current stubs
- **Suggested revision**: Address the concern above.

### FINDING_14: [OUT_OF_SCOPE] risk-integration: python/test_agents.py:267-268
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Hardcoded tier list in rotation unit test Does not fail today because it exercises first_tier parameter, not FIXER_TIER_ORDER Optionally use list(config.FIXER_TIER_ORDER) for consistency
- **Suggested revision**: Address the concern above.

### FINDING_15: **Part 1 (`docs/installation-and-setup.md`):** Advises removing file-level `apiKeyHelper` from `~/.claude/settings.json` so subprocesses that read settings directly do not get broken OAuth/API-key precedence. Example `*_api` / `*_login` aliases use placeholders only; no new runtime secret handling in-repo.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Part 1 (`docs/installation-and-setup.md`):** Advises removing file-level `apiKeyHelper` from `~/.claude/settings.json` so subprocesses that read settings directly do not get broken OAuth/API-key precedence. Example `*_api` / `*_login` aliases use placeholders only; no new runtime secret handling in-repo.
- **Suggested revision**: Address the concern above.

### FINDING_16: **Part 2 (routing):** `_phase_coder_implicit`, `run_ci_fix_vendor` `tiers=(codex cursor claude)`, `run_recovery_waterfall`, and `run_rebase_rebump` inline conflict path flip probe order only. `first-fixer-non-health` still keys off `first_tier` / `waterfall_iter`, not a hardcoded `cursor` tier.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Part 2 (routing):** `_phase_coder_implicit`, `run_ci_fix_vendor` `tiers=(codex cursor claude)`, `run_recovery_waterfall`, and `run_rebase_rebump` inline conflict path flip probe order only. `first-fixer-non-health` still keys off `first_tier` / `waterfall_iter`, not a hardcoded `cursor` tier.
- **Suggested revision**: Address the concern above.

### FINDING_17: **`SECURITY.md`:** Omitted-`--coder` narrative and pin guidance aligned with Codex-first (#3337); delegation/sandbox paragraphs for review vs implementer lanes unchanged.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **`SECURITY.md`:** Omitted-`--coder` narrative and pin guidance aligned with Codex-first (#3337); delegation/sandbox paragraphs for review vs implementer lanes unchanged.
- **Suggested revision**: Address the concern above.

### FINDING_18: **Tests:** Tier-order stub/message updates only; `#3338` hermetic `PATH` stubs reduce accidental real external-agent invocation during lint (positive for CI isolation, not a new attack surface).
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Tests:** Tier-order stub/message updates only; `#3338` hermetic `PATH` stubs reduce accidental real external-agent invocation during lint (positive for CI isolation, not a new attack surface). No command injection, path traversal, auth bypass, or secret leakage introduced by the diff. Codex-first default shifts which **already workspace-write** external launcher runs first when both are available; existing mitigations (dispatcher gates, no external commits, read-only review lanes) are unchanged.
- **Suggested revision**: Address the concern above.

### FINDING_19: correctness: skills/implement/SKILL.md:1169; scripts/ship-pr.md:72
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] first-fixer-non-health prose pins Codex as the first CI-fix tier, but rotation makes the first tier depend on start_attempt % 3 On start_attempt=1 or 2, Cursor or Claude can trigger first-fixer-non-health without Codex being tried; operators mis-debug Exit 3 as a Codex-only path Reword to rotated-first-tier language only; cite start_attempt / first_tier, not Codex on attempt 0
- **Suggested revision**: Address the concern above.

### FINDING_20: risk-integration: docs/installation-and-setup.md:147
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Dual-auth alias guidance implies shell aliases control billing for all Claude subprocesses, including larch-spawned claude --print children Plugin session keeps ANTHROPIC_API_KEY while the user uses claude_login in another shell; larch subprocesses still API-bill Clarify that larch subprocesses inherit the Claude Code / plugin process env; aliases apply only in shells where defined
- **Suggested revision**: Address the concern above.

### FINDING_21: architecture: scripts/ship-pr.sh:2806-2835; scripts/ship-pr.sh:3385-3402; scripts/ship-pr.md
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Two conflict-resolution paths use different external-tool strategies (3-tier recovery vs single-shot inline rebase) Operator expects CI-fix-style waterfall during inline rebase conflict resolution and misreads a single launcher call as a routing bug Cross-link inline vs recovery contracts from implement SKILL or runbook docs
- **Suggested revision**: Address the concern above.

### FINDING_22: [OUT_OF_SCOPE] architecture: python/ci_monitor.py:743-751
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Python _available_tiers does not skip missing codex/cursor binaries unlike Bash recovery_waterfall command -v guards Phase 7 Python port may attempt unavailable tiers differently than live Bash (pre-existing; not wired live) Filter tiers by binary availability when Python path is enabled
- **Suggested revision**: Address the concern above.

### FINDING_23: [OUT_OF_SCOPE] correctness: scripts/ship-pr.sh:2115-2122
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] first-fixer bail requires wrapper_rc=0; other-class failures with non-zero wrapper_rc fall through to next tiers Flaky wrapper exit may skip early Exit 3 bail and consume extra launcher budget Pre-existing; document or align wrapper_rc handling if product wants consistent bail
- **Suggested revision**: Address the concern above.

### FINDING_24: correctness: scripts/test-implement-step2-routing.sh:47
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] The assert_not_contains guard forbids Codex → Cursor → Claude in SKILL.md but the assertion label says old waterfall order. A maintainer retitling routing may think the forbidden string is the retired order and weaken or remove the guard while syncing docs. Rename the label to state that SKILL.md must not duplicate the script-side waterfall arrow order (e.g. script-side waterfall order not duplicated in SKILL.md).
- **Suggested revision**: Address the concern above.

### FINDING_25: **correctness** `scripts/test-ship-pr-fix-loop-2632.inc.sh:225-267` — `t4e` validates rotated-first-tier bail only for `start_attempt=1` (cursor-first). There is no symmetric harness for `start_attempt=2` (claude-first: `offset=2`, `first_tier=claude`, loop order claude → codex → cursor per `scripts/ship-pr.sh:2069-2072`). The rotation math for offset 2 matches offset 0/1, but a regression in indexing or bail gating at that offset would not be caught by the new tests added on this branch. **Suggested fix:** Add a `t4f` case mirroring `t4e`: `run_ci_fix_vendor ... 2`, stub `launch-claude-ci.sh` with `LAUNCHER_FAILURE_CLASS=other` and `wrapper_rc=0`, assert a single Claude launch and `BAIL_REASON=first-fixer-non-health` in state.
- **Reviewer**: dyn-waterfall-rotation-output.txt
- **Concern**: - **correctness** `scripts/test-ship-pr-fix-loop-2632.inc.sh:225-267` — `t4e` validates rotated-first-tier bail only for `start_attempt=1` (cursor-first). There is no symmetric harness for `start_attempt=2` (claude-first: `offset=2`, `first_tier=claude`, loop order claude → codex → cursor per `scripts/ship-pr.sh:2069-2072`). The rotation math for offset 2 matches offset 0/1, but a regression in indexing or bail gating at that offset would not be caught by the new tests added on this branch. **Suggested fix:** Add a `t4f` case mirroring `t4e`: `run_ci_fix_vendor ... 2`, stub `launch-claude-ci.sh` with `LAUNCHER_FAILURE_CLASS=other` and `wrapper_rc=0`, assert a single Claude launch and `BAIL_REASON=first-fixer-non-health` in state.
- **Suggested revision**: Address the concern above.

### FINDING_26: [OUT_OF_SCOPE] **Rotation arithmetic (Bash):** With `tiers=(codex cursor claude)`, `offset=$((start_attempt % 3))`, and `first_tier=${tiers[$offset]}`, the loop order is correct for `start_attempt=0` (codex, cursor, claude), `1` (cursor, claude, codex), and `2` (claude, codex, cursor). The `first-fixer-non-health` gate at `scripts/ship-pr.sh:2115-2122` keys on `waterfall_iter=0`, `wrapper_rc=0`, and `tier="$first_tier"`, which matches the first launched tier when all launchers exist.
- **Reviewer**: dyn-waterfall-rotation-output.txt
- **Concern**: - **Rotation arithmetic (Bash):** With `tiers=(codex cursor claude)`, `offset=$((start_attempt % 3))`, and `first_tier=${tiers[$offset]}`, the loop order is correct for `start_attempt=0` (codex, cursor, claude), `1` (cursor, claude, codex), and `2` (claude, codex, cursor). The `first-fixer-non-health` gate at `scripts/ship-pr.sh:2115-2122` keys on `waterfall_iter=0`, `wrapper_rc=0`, and `tier="$first_tier"`, which matches the first launched tier when all launchers exist.
- **Suggested revision**: Address the concern above.

### FINDING_27: [OUT_OF_SCOPE] **`t4e` sourcing:** `ship-pr.sh` is source-safe (`if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then main "$@"; fi` at `scripts/ship-pr.sh:3811`; guarded in `scripts/test-ship-pr.sh:894-910`). Direct-sourcing `run_ci_fix_vendor` without `ci-wait.sh` is intentional and does not reach post-vendor verify/stage paths on the early bail. Minimal state (`RUN_ID`, `REPO`, `FAILED_RUN_ID`) is enough because `read_state` defaults missing keys and `run_ci_fix_vendor` only needs `REPO` from state for `--repo`.
- **Reviewer**: dyn-waterfall-rotation-output.txt
- **Concern**: - **`t4e` sourcing:** `ship-pr.sh` is source-safe (`if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then main "$@"; fi` at `scripts/ship-pr.sh:3811`; guarded in `scripts/test-ship-pr.sh:894-910`). Direct-sourcing `run_ci_fix_vendor` without `ci-wait.sh` is intentional and does not reach post-vendor verify/stage paths on the early bail. Minimal state (`RUN_ID`, `REPO`, `FAILED_RUN_ID`) is enough because `read_state` defaults missing keys and `run_ci_fix_vendor` only needs `REPO` from state for `--repo`.
- **Suggested revision**: Address the concern above.

### FINDING_28: [OUT_OF_SCOPE] **Python parity:** `python/ci_monitor.py:912-916` rotates via `first_tier = tiers[start_attempt % len(tiers)]` and `agents.run_waterfall(..., first_tier=first_tier)`, which matches Bash when all three tiers are available. There is no Python unit test for `start_attempt=1`/`2` first-fixer rotation (only `start_attempt=0` in `python/test_ci_monitor.py:842-871`).
- **Reviewer**: dyn-waterfall-rotation-output.txt
- **Concern**: - **Python parity:** `python/ci_monitor.py:912-916` rotates via `first_tier = tiers[start_attempt % len(tiers)]` and `agents.run_waterfall(..., first_tier=first_tier)`, which matches Bash when all three tiers are available. There is no Python unit test for `start_attempt=1`/`2` first-fixer rotation (only `start_attempt=0` in `python/test_ci_monitor.py:842-871`).
- **Suggested revision**: Address the concern above.

### FINDING_29: [OUT_OF_SCOPE] **Pre-existing edge (not introduced here):** If the rotated-first tier is `claude` but `launch-claude-ci.sh` is not executable, the loop skips Claude with `waterfall_iter` already incremented (`scripts/ship-pr.sh:2073-2078`), so `first-fixer-non-health` will not fire on the next tier even though `first_tier` was `claude`.
- **Reviewer**: dyn-waterfall-rotation-output.txt
- **Concern**: - **Pre-existing edge (not introduced here):** If the rotated-first tier is `claude` but `launch-claude-ci.sh` is not executable, the loop skips Claude with `waterfall_iter` already incremented (`scripts/ship-pr.sh:2073-2078`), so `first-fixer-non-health` will not fire on the next tier even though `first_tier` was `claude`.
- **Suggested revision**: Address the concern above.

