### FINDING_1: **Important** `code-quality` — `scripts/test-dispatch-code-voters.sh:208`: the new round-2 test expects `DEGRADED_PANEL_WARNING=...1/2...`, but the scenario at `scripts/test-dispatch-code-voters.sh:200` should produce 2 effective judges. With `--round-num 2 --cursor-available false`, `scripts/dispatch-code-voters.sh:371-376` writes only the Cursor slot and disables Codex fallback; then `scripts/dispatch-with-waterfall.sh:281-303` correctly falls through to Claude phase 3, so Voter 1 plus Voter 3 fallback both produce output and no degraded warning is emitted. Update the assertion to require no degraded warning, or make the Claude fallback fail if the test is meant to exercise degradation.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `code-quality` — `scripts/test-dispatch-code-voters.sh:208`: the new round-2 test expects `DEGRADED_PANEL_WARNING=...1/2...`, but the scenario at `scripts/test-dispatch-code-voters.sh:200` should produce 2 effective judges. With `--round-num 2 --cursor-available false`, `scripts/dispatch-code-voters.sh:371-376` writes only the Cursor slot and disables Codex fallback; then `scripts/dispatch-with-waterfall.sh:281-303` correctly falls through to Claude phase 3, so Voter 1 plus Voter 3 fallback both produce output and no degraded warning is emitted. Update the assertion to require no degraded warning, or make the Claude fallback fail if the test is meant to exercise degradation.
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


### FINDING_22: risk-integration: skills/review/scripts/dispatch-panel.sh:406-408 scripts/dispatch-code-voters.sh:375-379
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Round 2+ forces `--codex-present false` for the whole waterfall, not only omitted Codex-primary slots. Cursor-primary slots (e.g. dynamic scout) lose Codex phase-2 fallback on later rounds, changing failure recovery vs “omit Codex reviewers” wording alone. Document the stricter behavior or narrow `codex_present` so only intended slots lose Codex alternation.
- **Suggested revision**: Address the concern above.


### FINDING_3: **Nit** `code-quality` — `cursor:1`: the branch adds a repo-root file containing only `FINDING_1: YES`. This looks like captured reviewer/voter output and is unrelated to the plugin runtime or docs. Remove the file from the branch.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 3. **Nit** `code-quality` — `cursor:1`: the branch adds a repo-root file containing only `FINDING_1: YES`. This looks like captured reviewer/voter output and is unrelated to the plugin runtime or docs. Remove the file from the branch. I attempted to run `bash scripts/test-dispatch-code-voters.sh --section happy`, but the read-only sandbox blocked its temp directory creation with `Operation not permitted`.
- **Suggested revision**: Address the concern above.


### FINDING_6: code-quality: cursor:1
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Repo-root file `cursor` containing a single vote line ships with the plugin. Consumers get an unexplained top-level `cursor` artifact; name collides conceptually with Cursor tooling and suggests accidental ballot output committed by mistake. Remove the file from the branch before merge.
- **Suggested revision**: Address the concern above.


### FINDING_9: code-quality: skills/implement/SKILL.md:562
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] `--dynamic-archetypes` docs still claim 7 static slots unconditionally while round 2+ panels are 6-slot static. Operators may misunderstand total reviewer fan-out across rounds and mis-calibrate cost or expectations vs actual `dispatch-panel` behavior. Update the bullet to describe round-aware static bases or point to the dispatch-panel contract for authoritative counts.
- **Suggested revision**: Address the concern above.


