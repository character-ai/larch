### FINDING_1: **Important** `code-quality` — `scripts/test-dispatch-code-voters.sh:208`: the new round-2 test expects `DEGRADED_PANEL_WARNING=...1/2...`, but the scenario at `scripts/test-dispatch-code-voters.sh:200` should produce 2 effective judges. With `--round-num 2 --cursor-available false`, `scripts/dispatch-code-voters.sh:371-376` writes only the Cursor slot and disables Codex fallback; then `scripts/dispatch-with-waterfall.sh:281-303` correctly falls through to Claude phase 3, so Voter 1 plus Voter 3 fallback both produce output and no degraded warning is emitted. Update the assertion to require no degraded warning, or make the Claude fallback fail if the test is meant to exercise degradation.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `code-quality` — `scripts/test-dispatch-code-voters.sh:208`: the new round-2 test expects `DEGRADED_PANEL_WARNING=...1/2...`, but the scenario at `scripts/test-dispatch-code-voters.sh:200` should produce 2 effective judges. With `--round-num 2 --cursor-available false`, `scripts/dispatch-code-voters.sh:371-376` writes only the Cursor slot and disables Codex fallback; then `scripts/dispatch-with-waterfall.sh:281-303` correctly falls through to Claude phase 3, so Voter 1 plus Voter 3 fallback both produce output and no degraded warning is emitted. Update the assertion to require no degraded warning, or make the Claude fallback fail if the test is meant to exercise degradation.
- **Suggested revision**: Address the concern above.

### FINDING_2: **Important** `risk-integration` — `skills/shared/voting-protocol.md:66-69`: shared prompt/docs contracts still say code review launches all three voters every round, while the implementation now omits Codex after round 1. The stale contract also appears in `README.md:84`, `docs/workflow-lifecycle.md:154`, `docs/skills.md:95`, `docs/collaborative-sketches.md:55`, `skills/shared/topology.tsv:13`, `docs/topology.md:23`, and the guard in `scripts/test-quick-mode-docs-sync.sh:86-92`, so consumers and future edits will be pushed back toward the old Codex-every-round policy. Update those surfaces and regenerate topology docs where applicable.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 2. **Important** `risk-integration` — `skills/shared/voting-protocol.md:66-69`: shared prompt/docs contracts still say code review launches all three voters every round, while the implementation now omits Codex after round 1. The stale contract also appears in `README.md:84`, `docs/workflow-lifecycle.md:154`, `docs/skills.md:95`, `docs/collaborative-sketches.md:55`, `skills/shared/topology.tsv:13`, `docs/topology.md:23`, and the guard in `scripts/test-quick-mode-docs-sync.sh:86-92`, so consumers and future edits will be pushed back toward the old Codex-every-round policy. Update those surfaces and regenerate topology docs where applicable.
- **Suggested revision**: Address the concern above.

### FINDING_3: **Nit** `code-quality` — `cursor:1`: the branch adds a repo-root file containing only `FINDING_1: YES`. This looks like captured reviewer/voter output and is unrelated to the plugin runtime or docs. Remove the file from the branch.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 3. **Nit** `code-quality` — `cursor:1`: the branch adds a repo-root file containing only `FINDING_1: YES`. This looks like captured reviewer/voter output and is unrelated to the plugin runtime or docs. Remove the file from the branch. I attempted to run `bash scripts/test-dispatch-code-voters.sh --section happy`, but the read-only sandbox blocked its temp directory creation with `Operation not permitted`.
- **Suggested revision**: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] correctness: docs/topology.md (not in branch diff)
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Possible remaining topology wording for implement conflict review vs new round-aware Codex omission. Stale cross-doc link target if topology still describes an always-three-external panel. Align topology prose with round policy in a follow-up doc pass.
- **Suggested revision**: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] risk-integration: skills/review-and-fix/scripts/review-and-fix.md
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Orchestrator doc not updated in this diff; may still describe an always-3-judge implement review. Doc/runtime drift for nested implement review operators. Follow-up documentation alignment (no code change required in this PR).
- **Suggested revision**: Address the concern above.

### FINDING_6: code-quality: cursor:1
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Repo-root file `cursor` containing a single vote line ships with the plugin. Consumers get an unexplained top-level `cursor` artifact; name collides conceptually with Cursor tooling and suggests accidental ballot output committed by mistake. Remove the file from the branch before merge.
- **Suggested revision**: Address the concern above.

### FINDING_7: code-quality: scripts/dispatch-code-voters.sh (codex prompt path)
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Round 2+ still materializes `codex-vote-prompt.txt` via `make_voter_prompt_file codex` despite skipped Codex voter. Extra tmp artifact suggests an active Codex voter during triage. Guard Codex prompt generation on `ROUND_NUM==1`.
- **Suggested revision**: Address the concern above.

### FINDING_8: code-quality: scripts/dispatch-code-voters.sh:360-361
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] `make_voter_prompt_file codex` runs on round 2+ even though Codex voter is omitted. Writes unused `codex-vote-prompt.txt` each round. Guard the call so Codex prompts are only created when the Codex slot is dispatched.
- **Suggested revision**: Address the concern above.

### FINDING_9: code-quality: skills/implement/SKILL.md:562
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] `--dynamic-archetypes` docs still claim 7 static slots unconditionally while round 2+ panels are 6-slot static. Operators may misunderstand total reviewer fan-out across rounds and mis-calibrate cost or expectations vs actual `dispatch-panel` behavior. Update the bullet to describe round-aware static bases or point to the dispatch-panel contract for authoritative counts.
- **Suggested revision**: Address the concern above.

### FINDING_10: code-quality: skills/review/scripts/review-core.sh:1083-1085
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Voter file list omits failed voters but does not explicitly exclude `skipped` status. If a later change ever populated a path while keeping `skipped`, tally could ingest an unintended voter artifact. Add `!= "skipped"` to the voter file inclusion conditions.
- **Suggested revision**: Address the concern above.

### FINDING_11: correctness: cursor:1
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Committed stray repo-root file `cursor` containing `FINDING_1: YES` unrelated to Codex round gating. Confusing artifact and potential tooling/human mistakes; pollutes the plugin tree. Delete from branch and prevent recurrence (session cleanup or hook).
- **Suggested revision**: Address the concern above.

### FINDING_12: correctness: docs/review-agents.md:93-97
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] `/implement` Phase 3 table row remains a flat Claude+Codex+Cursor summary after Note A was specialized for quick mode rounds. Readers scanning the table can believe Codex participates every review round for Phase 3, conflicting with Note A and the new voter/panel behavior. Add a brief round-1-only Codex qualifier to the row or defer to updated topology text.
- **Suggested revision**: Address the concern above.

### FINDING_13: correctness: skills/implement/SKILL.md:~155
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] `--dynamic-archetypes` bullet still claims exactly 7 static slots for all rounds. Misconfigures operator expectations for HARD (12 static on round 1) and for round 2+ (6 static); contradicts updated `--no-dynamic-archetypes` wording in the same skill. Reword to round-aware static slot counts or reference `dispatch-panel.md` / runtime behavior explicitly.
- **Suggested revision**: Address the concern above.

### FINDING_14: correctness: skills/review/scripts/review-core.sh:505-507
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Voter file list relies on empty path for skipped Codex voter instead of an explicit skipped status check. Regression risk if a future edit pairs non-empty paths with skipped status. Add explicit `!= skipped` (and keep `-s` checks) before appending voter paths.
- **Suggested revision**: Address the concern above.

### FINDING_15: correctness: skills/review/scripts/review-core.sh:505-507
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] voter_files selection checks `!= failed` and non-empty path but not `skipped`. If `skipped` ever pairs with a stale non-empty path, tally could ingest an unintended extra voter file. Explicitly exclude `skipped` statuses when appending to `voter_files`.
- **Suggested revision**: Address the concern above.

### FINDING_16: correctness: skills/review/scripts/test-check-reviewer-failure-threshold.sh
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] No `both_down` / zero-launched style assertion for `--round-num 2`. Round 2+ intended-slot math for total static failure could regress without a test mirroring the round-1 harness. Add a `both_down`-style case with `--round-num 2` and assert FAILED_SLOTS and THRESHOLD_OK against the 6-slot denominator.
- **Suggested revision**: Address the concern above.

### FINDING_17: risk-integration: cursor (repo root, new file in diff)
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Unplanned tracked file containing FINDING_1: YES ships with the plugin and is unrelated to the Codex round-gating feature. Operators and CI see an unexplained top-level file; risks mistaken identity with real voter output and unnecessary merge noise. Remove the file from the branch before merge; do not ship stray artifacts.
- **Suggested revision**: Address the concern above.

### FINDING_18: risk-integration: cursor:1
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] Stray committed root file named cursor with ballot text FINDING_1: YES unrelated to the feature Plugin root ships an unexplained artifact that collides with Cursor-related naming and can confuse packaging or manual audits Delete the file from the branch before merge
- **Suggested revision**: Address the concern above.

### FINDING_19: risk-integration: cursor:1
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Accidental new tracked repo-root file `cursor` containing vote text ships with the plugin and is unrelated to the feature. Consumers and CI see unexplained root content; possible confusion with Cursor CLI or root globbers. Remove the file from the branch; optionally add automation to prevent similar stray root commits.
- **Suggested revision**: Address the concern above.

### FINDING_20: risk-integration: docs/review-agents.md:97
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Usage table still lists `/implement` Phase 3 conflict review as unconditional Claude+Codex+Cursor while Note A documents round-1-only Codex and 2-judge rounds 2+. Operators read the table only and mis-plan cost/coverage for later review rounds. Align the table row (and topology link) with round-aware reviewer+voter semantics.
- **Suggested revision**: Address the concern above.

### FINDING_21: risk-integration: skills/fix-issue/SKILL.md
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] No doc update for round-1-only Codex despite feature text naming /fix-issue. Readers of fix-issue only may misunderstand voting panel shape; runtime is already correct via shared scripts. Mirror the round-aware voting note from implement/review skills.
- **Suggested revision**: Address the concern above.

### FINDING_22: risk-integration: skills/review/scripts/dispatch-panel.sh:406-408 scripts/dispatch-code-voters.sh:375-379
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Round 2+ forces `--codex-present false` for the whole waterfall, not only omitted Codex-primary slots. Cursor-primary slots (e.g. dynamic scout) lose Codex phase-2 fallback on later rounds, changing failure recovery vs “omit Codex reviewers” wording alone. Document the stricter behavior or narrow `codex_present` so only intended slots lose Codex alternation.
- **Suggested revision**: Address the concern above.

### FINDING_23: risk-integration: skills/review/scripts/review-core.sh:505-507
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] voter_files assembly omits failed voters but does not explicitly skip skipped slots. Future change could append a path if skipped ever paired with a non-empty path, misfeeding tally. Add an explicit skipped status guard alongside failed when pushing voter paths.
- **Suggested revision**: Address the concern above.

