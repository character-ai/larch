### OOS_1: Plugin version lookup still needs a stable root
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: latent
- **Concern**: The version resolver still depends on an underspecified plugin-root base, so when the manifest is absent or looked up from the wrong directory the final-summary can keep rendering `Larch version: unknown`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Resolve plugin root from CLAUDE_PLUGIN_ROOT with Path(__file__).resolve().parents[3] fallback, then read root / config.PLUGIN_JSON_PATH (same pattern as run_log_manifest._plugin_version)


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected (latent-rerouted)

### OOS_2: Keep REPO_ROOT in rehydration allowlists
- **Reviewer(s)**: Codex-dyn-Root Contract Reviewer
- **Severity**: blocking
- **Concern**: Even if Step 0 writes `REPO_ROOT`, later design-session rehydration layers can still strip it from the sourced env, so Gate C and Step 1d.7 may reload without the authoritative root and fall back to cwd or `CLAUDE_PROJECT_DIR`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-Root Contract Reviewer: Add REPO_ROOT to SOURCE_ENV_ALLOW, _SESSION_ENV_ALLOWLIST, and any default design env maps that must preserve the key across rehydration


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### OOS_3:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/larch/design/design_step0.py
- **Concern**: [SCOPE-REDUCTION] Step 0-only repo-root helper blocks init reuse. Scenario: The plan adds a resolver helper only in design_step0.py while init_runparams in design_router.py must pass the same root on refresh. A Step-0-local helper invites duplicate resolution logic or a missed import at the second write-design-env site.
- **Proposed resolution**: Extend larch/git/repo_roots.py (consumer_repo_root plus the planned cwd fallback) or extract a shared design repo-root helper, use it from Step 0 and init_runparams, and thread the result into both write-design-env calls.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (latent-rerouted)

### OOS_4: Refresh write-design-env at Step 5c also omits --repo-root
- **Description**: Refresh write-design-env at Step 5c also omits --repo-root. Scenario: After Gate C, _refresh_design_source_env can strip REPO_ROOT from source-env.sh before log publish. It does not explain the missing Gate C assessment but can break later consumers of source-env.sh.
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: python/larch/design/design_publish.py:448-470
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

### OOS_5: [SCOPE-REDUCTION] Stall-report version helper is outside the design final-summary path
- **Description**: [SCOPE-REDUCTION] Stall-report version helper is outside the design final-summary path. Scenario: _report._read_larch_version does not feed design render-final-summary; pr_body._plugin_version_local owns the observed unknown Larch version symptom
- **Reviewer**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: architecture
- **Location**: python/larch/state/_report.py:154-166
- **Phase**: design




Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral

### OOS_6: [OUT_OF_SCOPE] The Larch-version fallback edits are a separate symptom cleanup, not required to restore the assessment persistence contract
- **Description**: [OUT_OF_SCOPE] The Larch-version fallback edits are a separate symptom cleanup, not required to restore the assessment persistence contract. Scenario: The feature is complete once Gate C always uses the explicit root and fails closed on persistence errors; the version-summary polish can ship later without affecting that contract
- **Reviewer**: Codex-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/larch/git/pr_body.py:457-464; python/larch/state/_report.py:154-160
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

### OOS_7: _report.py plugin.json fallback is outside acceptance criteria
- **Description**: _report.py plugin.json fallback is outside acceptance criteria. Scenario: The issue acceptance criteria target Gate C assessment persistence and final-summary version via render run-summary. _read_larch_version only feeds stall-recovery reports, not the missing assessment artifact or the cited final-summary line fixed in pr_body.py.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/larch/state/_report.py
- **Phase**: design




Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral

### OOS_8: [OUT_OF_SCOPE] The Larch-version fallback cleanup is a separate reporting fix, not required to close the Gate C assessment-persistence bug.
- **Description**: [OUT_OF_SCOPE] The Larch-version fallback cleanup is a separate reporting fix, not required to close the Gate C assessment-persistence bug.. Scenario: The main design fix still works without it. This only changes version labels in run-summary and stall/failure reports, so it adds unrelated scope and test churn.
- **Reviewer**: Codex-Pragmatic
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/larch/git/pr_body.py:457-482; python/larch/state/_report.py:154-167
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

### OOS_9: [OUT_OF_SCOPE] Add unrelated version-fallback cleanup to the PR summary and stall-report paths.
- **Description**: [OUT_OF_SCOPE] Add unrelated version-fallback cleanup to the PR summary and stall-report paths.. Scenario: The assessment persistence fix already works once repo-root is threaded. These fallback edits widen the patch and test surface, but they are not needed for the stated bug fix.
- **Reviewer**: Codex-Requirements
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/larch/git/pr_body.py:457-465; python/larch/state/_report.py:154-162; python/tests/git/test_pr_body.py:1579-1597
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

### OOS_10: Step 2b architectural-guidelines read is not threaded with --repo-root
- **Description**: Step 2b architectural-guidelines read is not threaded with --repo-root. Scenario: Plan updates Gate C and Step 1d.7 only; Step 2b read without explicit root can still resolve guidelines absent from plugin-cache cwd during drafting
- **Reviewer**: Cursor-dyn-Root Contract Reviewer
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:313
- **Phase**: design

Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral

### OOS_11: Parse quoted `REPO_ROOT` exports correctly
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: REPO_ROOT recovery must parse shlex-quoted exports, not mirror the bool regex. Scenario: _export_line writes export REPO_ROOT via shlex.quote; a bool-style ^export REPO_ROOT=...$ regex will not recover quoted paths, so init_runparams refresh can still drop REPO_ROOT and re-open the clobber path
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Implement _recover_prior_path using parse_allowlisted_env_line (or equivalent shlex split) and wire it into write-design-env when --repo-root is absent


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### OOS_12: REPO_ROOT is absent from design rehydration allowlists
- **Description**: REPO_ROOT is absent from design rehydration allowlists. Scenario: _SESSION_ENV_ALLOWLIST and SOURCE_ENV_ALLOW omit REPO_ROOT, so Python wrapper rehydration drops it even when source-env.sh exports it; lower risk while Gate C stays prompt-side, but pause/resume wrapper paths may lose the root
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/larch/design/design_session.py:109-122
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

### OOS_13: Step 0a source-env key list still omits REPO_ROOT
- **Description**: Step 0a source-env key list still omits REPO_ROOT. Scenario: After the fix, operators reading the SKILL bash-prelude contract will not see REPO_ROOT as a persisted session key, increasing odds of ad-hoc cwd resolution
- **Reviewer**: Cursor-Arch
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: skills/design/SKILL.md:47
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

### OOS_14: REPO_ROOT omitted from design rehydration allowlists
- **Description**: REPO_ROOT omitted from design rehydration allowlists. Scenario: `SOURCE_ENV_ALLOW` and `_SESSION_ENV_ALLOWLIST` omit `REPO_ROOT`, so Python wrappers that rehydrate `source-env.sh` never export it into `os.environ`. Prompt-side sourcing fixes Gate C; allowlist gaps still block any future wrapper-owned guideline call that expects ambient `REPO_ROOT`.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: python/larch/design/design_step0_env.py:36-47
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

### OOS_15: Step 2b `read_guidelines()` still omits explicit repo root
- **Description**: Step 2b `read_guidelines()` still omits explicit repo root. Scenario: Step 2b calls `architectural_guidelines.read_guidelines()` without `--repo-root`. On plugin-cache cwd this can mis-resolve guidelines during drafting, separate from Gate C persistence.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: correctness
- **Location**: python/larch/design/design_step2b.py:462
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

### OOS_16: Step 5c `write-design-env` refresh still omits `--repo-root`
- **Description**: Step 5c `write-design-env` refresh still omits `--repo-root`. Scenario: `_refresh_design_source_env` calls `write-design-env` without `--repo-root`. Writer-side recovery should preserve the Step 0 value, but an explicit pass would match the plan’s “call sites that own the flow” rule and reduce reliance on recovery alone.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: python/larch/design/design_publish.py:448-468
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

### OOS_17: REPO_ROOT omitted from Python rehydration allowlists
- **Description**: REPO_ROOT omitted from Python rehydration allowlists. Scenario: SOURCE_ENV_ALLOW and _SESSION_ENV_ALLOWLIST omit REPO_ROOT, so Python wrapper rehydration drops it even after source-env.sh exports it. Gate C is orchestrator-side today, but any future Python-owned guideline call would reload without the captured root.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: correctness
- **Location**: python/larch/design/design_step0_env.py:36-47
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

### OOS_18: [OUT_OF_SCOPE] Run-summary version fallback is outside acceptance criteria
- **Description**: [OUT_OF_SCOPE] Run-summary version fallback is outside acceptance criteria. Scenario: The issue cites "Larch version: unknown" only as corroborating evidence. Acceptance criteria require architectural-guideline-assessment.md persistence and fail-closed Gate C warnings, not final-summary version strings.
- **Reviewer**: Cursor-Requirements
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: python/larch/git/pr_body.py:457-464
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

### OOS_19: [OUT_OF_SCOPE] Stall-report version fallback is outside acceptance criteria
- **Description**: [OUT_OF_SCOPE] Stall-report version fallback is outside acceptance criteria. Scenario: _report._read_larch_version feeds stall/failure reports, not the Gate C assessment path. Fixing it does not restore assessment persistence or the contracted Gate C warning behavior.
- **Reviewer**: Cursor-Requirements
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: python/larch/state/_report.py:154-166
- **Phase**: design

Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected
