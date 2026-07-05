### OOS_1: REPO_ROOT is absent from design rehydration allowlists
- **Description**: REPO_ROOT is absent from design rehydration allowlists. Scenario: _SESSION_ENV_ALLOWLIST and SOURCE_ENV_ALLOW omit REPO_ROOT, so Python wrapper rehydration drops it even when source-env.sh exports it; lower risk while Gate C stays prompt-side, but pause/resume wrapper paths may lose the root
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/larch/design/design_session.py:109-122
- **Phase**: design



### OOS_2: Step 0a source-env key list still omits REPO_ROOT
- **Description**: Step 0a source-env key list still omits REPO_ROOT. Scenario: After the fix, operators reading the SKILL bash-prelude contract will not see REPO_ROOT as a persisted session key, increasing odds of ad-hoc cwd resolution
- **Reviewer**: Cursor-Arch
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: skills/design/SKILL.md:47
- **Phase**: design



### OOS_3: REPO_ROOT omitted from design rehydration allowlists
- **Description**: REPO_ROOT omitted from design rehydration allowlists. Scenario: `SOURCE_ENV_ALLOW` and `_SESSION_ENV_ALLOWLIST` omit `REPO_ROOT`, so Python wrappers that rehydrate `source-env.sh` never export it into `os.environ`. Prompt-side sourcing fixes Gate C; allowlist gaps still block any future wrapper-owned guideline call that expects ambient `REPO_ROOT`.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: python/larch/design/design_step0_env.py:36-47
- **Phase**: design



### OOS_4: Step 2b `read_guidelines()` still omits explicit repo root
- **Description**: Step 2b `read_guidelines()` still omits explicit repo root. Scenario: Step 2b calls `architectural_guidelines.read_guidelines()` without `--repo-root`. On plugin-cache cwd this can mis-resolve guidelines during drafting, separate from Gate C persistence.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: correctness
- **Location**: python/larch/design/design_step2b.py:462
- **Phase**: design



### OOS_5: Step 5c `write-design-env` refresh still omits `--repo-root`
- **Description**: Step 5c `write-design-env` refresh still omits `--repo-root`. Scenario: `_refresh_design_source_env` calls `write-design-env` without `--repo-root`. Writer-side recovery should preserve the Step 0 value, but an explicit pass would match the plan’s “call sites that own the flow” rule and reduce reliance on recovery alone.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: python/larch/design/design_publish.py:448-468
- **Phase**: design



### OOS_6: REPO_ROOT omitted from Python rehydration allowlists
- **Description**: REPO_ROOT omitted from Python rehydration allowlists. Scenario: SOURCE_ENV_ALLOW and _SESSION_ENV_ALLOWLIST omit REPO_ROOT, so Python wrapper rehydration drops it even after source-env.sh exports it. Gate C is orchestrator-side today, but any future Python-owned guideline call would reload without the captured root.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: correctness
- **Location**: python/larch/design/design_step0_env.py:36-47
- **Phase**: design



### OOS_7: [OUT_OF_SCOPE] Run-summary version fallback is outside acceptance criteria
- **Description**: [OUT_OF_SCOPE] Run-summary version fallback is outside acceptance criteria. Scenario: The issue cites "Larch version: unknown" only as corroborating evidence. Acceptance criteria require architectural-guideline-assessment.md persistence and fail-closed Gate C warnings, not final-summary version strings.
- **Reviewer**: Cursor-Requirements
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: python/larch/git/pr_body.py:457-464
- **Phase**: design



### OOS_8: [OUT_OF_SCOPE] Stall-report version fallback is outside acceptance criteria
- **Description**: [OUT_OF_SCOPE] Stall-report version fallback is outside acceptance criteria. Scenario: _report._read_larch_version feeds stall/failure reports, not the Gate C assessment path. Fixing it does not restore assessment persistence or the contracted Gate C warning behavior.
- **Reviewer**: Cursor-Requirements
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: python/larch/state/_report.py:154-166
- **Phase**: design



