### [rejected] FINDING_12

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_12: risk-integration: scripts/ship-pr.sh:3385-3401
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] No harness pins inline 600s codex-first rebase conflict launcher Recovery-waterfall tests cover codex-first at 1800s; inline launch-codex-ci.sh --timeout 600 when both binaries exist is untested and could regress to cursor-first silently Add a test-ship-pr.sh fixture that hits skip_vendor=false inline path and asserts launch-codex-ci.sh with --timeout 600 before any cursor launcher
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_15

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_15: **Part 1 (`docs/installation-and-setup.md`):** Advises removing file-level `apiKeyHelper` from `~/.claude/settings.json` so subprocesses that read settings directly do not get broken OAuth/API-key precedence. Example `*_api` / `*_login` aliases use placeholders only; no new runtime secret handling in-repo.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Part 1 (`docs/installation-and-setup.md`):** Advises removing file-level `apiKeyHelper` from `~/.claude/settings.json` so subprocesses that read settings directly do not get broken OAuth/API-key precedence. Example `*_api` / `*_login` aliases use placeholders only; no new runtime secret handling in-repo.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_16: **Part 2 (routing):** `_phase_coder_implicit`, `run_ci_fix_vendor` `tiers=(codex cursor claude)`, `run_recovery_waterfall`, and `run_rebase_rebump` inline conflict path flip probe order only. `first-fixer-non-health` still keys off `first_tier` / `waterfall_iter`, not a hardcoded `cursor` tier.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Part 2 (routing):** `_phase_coder_implicit`, `run_ci_fix_vendor` `tiers=(codex cursor claude)`, `run_recovery_waterfall`, and `run_rebase_rebump` inline conflict path flip probe order only. `first-fixer-non-health` still keys off `first_tier` / `waterfall_iter`, not a hardcoded `cursor` tier.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_17

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_17: **`SECURITY.md`:** Omitted-`--coder` narrative and pin guidance aligned with Codex-first (#3337); delegation/sandbox paragraphs for review vs implementer lanes unchanged.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **`SECURITY.md`:** Omitted-`--coder` narrative and pin guidance aligned with Codex-first (#3337); delegation/sandbox paragraphs for review vs implementer lanes unchanged.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_18

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_18: **Tests:** Tier-order stub/message updates only; `#3338` hermetic `PATH` stubs reduce accidental real external-agent invocation during lint (positive for CI isolation, not a new attack surface).
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Tests:** Tier-order stub/message updates only; `#3338` hermetic `PATH` stubs reduce accidental real external-agent invocation during lint (positive for CI isolation, not a new attack surface). No command injection, path traversal, auth bypass, or secret leakage introduced by the diff. Codex-first default shifts which **already workspace-write** external launcher runs first when both are available; existing mitigations (dispatcher gates, no external commits, read-only review lanes) are unchanged.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_19

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_19: correctness: skills/implement/SKILL.md:1169; scripts/ship-pr.md:72
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] first-fixer-non-health prose pins Codex as the first CI-fix tier, but rotation makes the first tier depend on start_attempt % 3 On start_attempt=1 or 2, Cursor or Claude can trigger first-fixer-non-health without Codex being tried; operators mis-debug Exit 3 as a Codex-only path Reword to rotated-first-tier language only; cite start_attempt / first_tier, not Codex on attempt 0
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: code-quality: scripts/ship-pr.sh:3385-3402
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Inline run_rebase_rebump conflict launcher order flipped without a dedicated harness. Codex-first inline resolve-conflict could regress while three-tier recovery tests stay green. Add a stubbed test that asserts launch-codex-ci before launch-cursor on the inline path.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_20

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_20: risk-integration: docs/installation-and-setup.md:147
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Dual-auth alias guidance implies shell aliases control billing for all Claude subprocesses, including larch-spawned claude --print children Plugin session keeps ANTHROPIC_API_KEY while the user uses claude_login in another shell; larch subprocesses still API-bill Clarify that larch subprocesses inherit the Claude Code / plugin process env; aliases apply only in shells where defined
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_21

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_21: architecture: scripts/ship-pr.sh:2806-2835; scripts/ship-pr.sh:3385-3402; scripts/ship-pr.md
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Two conflict-resolution paths use different external-tool strategies (3-tier recovery vs single-shot inline rebase) Operator expects CI-fix-style waterfall during inline rebase conflict resolution and misreads a single launcher call as a routing bug Cross-link inline vs recovery contracts from implement SKILL or runbook docs
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_25

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_25: **correctness** `scripts/test-ship-pr-fix-loop-2632.inc.sh:225-267` — `t4e` validates rotated-first-tier bail only for `start_attempt=1` (cursor-first). There is no symmetric harness for `start_attempt=2` (claude-first: `offset=2`, `first_tier=claude`, loop order claude → codex → cursor per `scripts/ship-pr.sh:2069-2072`). The rotation math for offset 2 matches offset 0/1, but a regression in indexing or bail gating at that offset would not be caught by the new tests added on this branch. **Suggested fix:** Add a `t4f` case mirroring `t4e`: `run_ci_fix_vendor ... 2`, stub `launch-claude-ci.sh` with `LAUNCHER_FAILURE_CLASS=other` and `wrapper_rc=0`, assert a single Claude launch and `BAIL_REASON=first-fixer-non-health` in state.
- **Reviewer**: dyn-waterfall-rotation-output.txt
- **Concern**: - **correctness** `scripts/test-ship-pr-fix-loop-2632.inc.sh:225-267` — `t4e` validates rotated-first-tier bail only for `start_attempt=1` (cursor-first). There is no symmetric harness for `start_attempt=2` (claude-first: `offset=2`, `first_tier=claude`, loop order claude → codex → cursor per `scripts/ship-pr.sh:2069-2072`). The rotation math for offset 2 matches offset 0/1, but a regression in indexing or bail gating at that offset would not be caught by the new tests added on this branch. **Suggested fix:** Add a `t4f` case mirroring `t4e`: `run_ci_fix_vendor ... 2`, stub `launch-claude-ci.sh` with `LAUNCHER_FAILURE_CLASS=other` and `wrapper_rc=0`, assert a single Claude launch and `BAIL_REASON=first-fixer-non-health` in state.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_6: **`run_ci_fix_vendor`**: `offset=$((start_attempt % 3))`, `first_tier=${tiers[$offset]}`, bail when `waterfall_iter=0`, `wrapper_rc=0`, `tier=$first_tier`, and `LAUNCHER_FAILURE_CLASS=other` — correct for codex-first base order and rotation (`t4e` covers `start_attempt=1` → Cursor as rotated first tier).
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - **`run_ci_fix_vendor`**: `offset=$((start_attempt % 3))`, `first_tier=${tiers[$offset]}`, bail when `waterfall_iter=0`, `wrapper_rc=0`, `tier=$first_tier`, and `LAUNCHER_FAILURE_CLASS=other` — correct for codex-first base order and rotation (`t4e` covers `start_attempt=1` → Cursor as rotated first tier).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_7: **Python parity**: `agents.run_waterfall` short-circuit matches Bash (`idx==0`, `wrapper_rc==0`, `failure_class=="other"`).
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - **Python parity**: `agents.run_waterfall` short-circuit matches Bash (`idx==0`, `wrapper_rc==0`, `failure_class=="other"`).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_8: **Explicit `--coder`**: `--coder cursor` → codex → claude; `--coder codex` → cursor → claude (unchanged).
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - **Explicit `--coder`**: `--coder cursor` → codex → claude; `--coder codex` → cursor → claude (unchanged). ---
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

