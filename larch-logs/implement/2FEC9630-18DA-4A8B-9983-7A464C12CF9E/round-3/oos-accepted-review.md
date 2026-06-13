### OOS_1: [OUT_OF_SCOPE] `auto_fix_plan_commands_main` weak default repo root
- **Reviewer(s)**: dyn-plan-cli-contracts-output.txt
- **Severity**: latent
- **Concern**: `auto_fix_plan_commands_main` defaults repo to `_repo_root_from(Path.cwd())` without the retired bash `PLUGIN_ROOT` fallback when `--repo-root` is omitted. `design-step-validator-autofix.sh` always passes `--repo-root`, so regression is latent on the live path only.
- **Suggested revisions (informational for voters; coder decides)**:


### OOS_2: [OUT_OF_SCOPE] Stale docs cite deleted `check-plan-size.md`
- **Reviewer(s)**: dyn-plan-cli-contracts-output.txt
- **Severity**: nit
- **Concern**: Docs still cite deleted `skills/design/scripts/check-plan-size.md` in places (`skills/design/references/flags.md`, `skills/design/scripts/design-postplan-emit.md`). Runtime behavior is fine; normative doc pointers are stale.
- **Suggested revisions (informational for voters; coder decides)**:


