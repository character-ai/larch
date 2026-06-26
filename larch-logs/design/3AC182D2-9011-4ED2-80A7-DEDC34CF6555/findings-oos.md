### OOS_1: Plugin strict-permissions allowlist omits `rejected-analysis`
- **Description**: Plugin strict-permissions allowlist omits `rejected-analysis`. Scenario: The plan updates the copy-paste snippet in `docs/configuration-and-permissions.md` but does not add `Skill(rejected-analysis)`, `Skill(larch:rejected-analysis)`, or `Bash($PWD/skills/rejected-analysis/scripts/)` to the canonical `.claude/settings.json` reference that strict-permissions operators copy. Larch dev runs without `bypassPermissions` will deny the new skill even though docs claim it is supported.
- **Reviewer**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: .claude/settings.json:145-174
- **Phase**: design



### OOS_2: Issue-mandated shared verify component with #5468 remains inline-only
- **Description**: Issue-mandated shared verify component with #5468 remains inline-only. Scenario: The binding issue asks to share the per-finding verify component with #5468 auto-OOS work. The plan inlines verify prompts, JSON schema, and ingest logic only under `rejected-analysis`, so #5468 will likely duplicate the same contract and drift.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/shared/rejected-finding-verify.md
- **Phase**: design



### OOS_3: Cursor verification lacks mechanical write isolation beyond dirty-tree post-check
- **Description**: Cursor verification lacks mechanical write isolation beyond dirty-tree post-check. Scenario: Read-only enforcement for Cursor is prompt plus `cursor agent --mode ask` plus post-hoc `${OUTPUT}.dirty-tree` rejection. A verifier can mutate the live repo before the sidecar is read, so a `confirmed` verdict can reflect self-edited files and leave the workspace polluted. This matches the accepted `/research` residual-risk posture but is not mechanically closed for a mutating auto-filer.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: security
- **Location**: skills/rejected-analysis/SKILL.md:108-121
- **Phase**: design



### OOS_4: No degraded-tools / both-down fail-closed gate before verification
- **Description**: No degraded-tools / both-down fail-closed gate before verification. Scenario: When Codex and Cursor are both missing, `prepare` can still emit `VERIFY_COUNT>0` and the orchestrator fires up to 100 fast `launch-review` failures instead of aborting once with a clear operator message.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: skills/rejected-analysis/SKILL.md:108-118
- **Phase**: design



### OOS_5: Strict-permissions docs snippet adds `Skill(rejected-analysis)` but the plan does not update canonical `.claude/settings.json` or document the Bash wrapper allowlist
- **Description**: Strict-permissions docs snippet adds `Skill(rejected-analysis)` but the plan does not update canonical `.claude/settings.json` or document the Bash wrapper allowlist. Scenario: Consumers who copy only the doc snippet may authorize the skill but block `skills/rejected-analysis/scripts/rejected-analysis.sh`; larch's referenced settings file will drift from the new docs.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: architecture
- **Location**: docs/configuration-and-permissions.md:542-549
- **Phase**: design



### OOS_6: Plugin dev strict-permissions allowlist omits the new skill
- **Description**: Plugin dev strict-permissions allowlist omits the new skill. Scenario: The plan updates `docs/configuration-and-permissions.md` but not `.claude/settings.json`, which is the canonical strict-permissions reference for this repo. Without `Skill(rejected-analysis)`, `Skill(larch:rejected-analysis)`, and `Bash($PWD/skills/rejected-analysis/scripts/)`, strict-permissions runs in the larch source tree cannot invoke the skill even after docs are updated.
- **Reviewer**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: architecture
- **Location**: docs/configuration-and-permissions.md:542-549
- **Phase**: design



### OOS_7: Issue-mandated shared verify component with #5468 remains inline-only
- **Description**: Issue-mandated shared verify component with #5468 remains inline-only. Scenario: Issue scope pairs this skill with #5468 and asks to share the verify component. The plan inlines verification prompts and `ingest-verdict` postprocessing in `python/rejected_analysis.py` instead of extracting a shared helper both skills can call, increasing drift risk when launcher postprocess rules change.
- **Reviewer**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/shared/rejected-finding-verify.md
- **Phase**: design



### OOS_8: In-scope/OOS filtering reimplements `voting.classification_row_is_oos` instead of calling it
- **Description**: In-scope/OOS filtering reimplements `voting.classification_row_is_oos` instead of calling it. Scenario: Hand-rolled `scope=oos` / `out_of_scope` / `OOS_*` checks can drift from `voting.classification_row_is_oos` header-aware behavior (e.g. future `scope` column semantics), letting deferred OOS rows into verification despite the v1 exclusion requirement.
- **Reviewer**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: correctness
- **Location**: python/rejected_analysis.py:262-267
- **Phase**: design



