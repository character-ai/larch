### OOS_1: [OUT_OF_SCOPE] correctness
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 1. **correctness** `scripts/launch-claude-ci.sh:249-256` — `record-vendor-task` still redirects stderr to `/dev/null`, so CI-fix timing failures remain invisible at that launcher boundary. Plan item 4 scoped only `launch-claude-subprocess.sh`; this is a parallel pre-existing gap.
- **Suggested revision**: Address the concern above.


### OOS_2: [OUT_OF_SCOPE] correctness
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 2. **correctness** `scripts/dispatch-with-waterfall.sh:227` — Phase 1/2 waterfall kinds use `${tool}-phase3-${slot}` (e.g. `codex-phase3-security`), which are not in `TIMING_TASK_KINDS_ALLOWED` (only `*-specialist-*` variants are). Those rows still record with warnings under #3797’s warning-only gate. Pre-existing; not introduced by this diff.
- **Suggested revision**: Address the concern above.


### OOS_3: [OUT_OF_SCOPE] risk-integration: scripts/launch-review.sh:108-116,696-704
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Codex/Cursor review launchers still swallow record-vendor-task stderr via >/dev/null 2>&1. Ledger validation or flock failures on codex/cursor review paths remain invisible to operators despite item 4 fixing the Claude subprocess path. Apply the same stderr visibility change to launch-review.sh timing hooks in a follow-up (out of this PR scope).
- **Suggested revision**: Address the concern above.


### OOS_4: [OUT_OF_SCOPE] correctness: scripts/timing-ledger.sh:192,306-307
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Malformed task-kind rejection (>64 chars) drops vendor rows; dynamic claude-phase3-dyn-* kinds from long archetype names can exceed the cap. Long archetype names produce claude-phase3-dyn-* kinds longer than 64 chars; record-vendor-task rejects them and no row is written (stderr warning now visible after item 4). Cap dynamic archetype name length or raise the ledger task-kind limit in a separate change.
- **Suggested revision**: Address the concern above.


### OOS_5: [OUT_OF_SCOPE] code-quality: scripts/test-timing-report.sh:128-150
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Terse-mode test only asserts claude=0; no fixture covers post-mark Claude vendor rows incrementing terse claude count. Regression in the new claude branch of terse counting when claude>0 would not be caught by the added tests. Add a terse fixture with a Claude vendor row whose end_s is after the latest mark and assert claude=1.
- **Suggested revision**: Address the concern above.


### OOS_6: [OUT_OF_SCOPE] risk-integration: scripts/test-launch-claude-subprocess.sh:1-441
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Plan item 4 surfaces timing-ledger stderr from launch-claude-subprocess.sh but no harness asserts warnings appear on ledger failure paths. A future revert of the stderr redirect would silently drop timing observability again with no CI failure. Add a harness case forcing a record-vendor-task warning and assert it appears on stderr while STATUS=OK remains on stdout.
- **Suggested revision**: Address the concern above.


### OOS_7: [OUT_OF_SCOPE] risk-integration: scripts/test-timing-report.sh:77-99
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Plan item 5 terse verification only checks claude=0 formatting not a post-mark Claude row incrementing the terse counter. A terse-only regression in the claude branch could slip past CI while summary tests still pass. Add a terse fixture with end_s >= last_terse_ts and expect claude=1 in the terse line.
- **Suggested revision**: Address the concern above.


### OOS_8: [OUT_OF_SCOPE] architecture
- **Reviewer**: dyn-call-site-parity-output.txt
- **Concern**: - **architecture** `scripts/lib-timing-kinds.sh` vs `scripts/dispatch-with-waterfall.sh:227` — Pre-existing naming drift: phase-1/phase-2 external rows emit `codex-phase1-*` / `cursor-phase2-*` kinds, while the allow-list documents `codex-specialist-*` / `cursor-specialist-*` instead; this branch does not address that broader contract mismatch.
- **Suggested revision**: Address the concern above.


