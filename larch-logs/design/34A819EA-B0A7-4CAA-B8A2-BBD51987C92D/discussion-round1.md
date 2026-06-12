## Decision 1: Pre- vs post-Step-0a fence scope
- **Question**: Which fences keep current shape vs collapse to launcher form?
- **Resolution**: Only `design-step0-session.sh` (Step 0a) keeps current shape. All 37+ other fences (including Step 0b series, Step 0c, and all later steps) collapse.
- **Source**: codebase — issue says "Pre-Step-0a fences (parse/session) keep their current shape"; only one fence creates the session

## Decision 2: Launcher write location
- **Question**: Where is `design-run-$PPID.sh` written?
- **Resolution**: Add `_write_design_run_sh()` to `session_env.py`, called from `write_design_env_main` (analogous to `_write_larch_run_sh` in `bootstrap.py`). The function writes `~/.cache/larch/sessions/design-run-$PPID.sh`.
- **Source**: codebase — implement analogy; issue says "design-step0-session.sh writes it" (which calls write-design-env)

## Decision 3: Launcher script behavior
- **Question**: What does the launcher do?
- **Resolution**: Takes a basename (e.g., `design-step3-entry.sh`), prepends baked-in `--session-env-path` and `--claude-pid`, execs `$BAKED_PLUGIN_ROOT/skills/design/scripts/$script "$@"`.
- **Source**: issue proposal + implement larch-run.sh analogy

## Decision 4: test-design-structure.sh update scope
- **Question**: Which structural checks need updating?
- **Resolution**: (1) `assert_design_skill_bash_fences_are_wrappers` — new regex for launcher shape; (2) `assert_direct_wrappers_are_executable_and_documented` — extract basenames from launcher calls; (3) `contains_near` anchors — update from `CLAUDE_PLUGIN_ROOT/…/design-step3-review.sh` to launcher basename form.
- **Source**: codebase — `scripts/test-design-structure.sh` existing checks

## Decision 5: Reference prose updates
- **Question**: Do `approval-gates.md` and `discussion-rounds.md` inline code examples update too?
- **Resolution**: Yes. Both files have 1 inline code mention of the old fence pattern; update to show launcher form. SKILL.md Bash block prelude prose also updates.
- **Source**: issue — "references collapse"; consistent documentation
