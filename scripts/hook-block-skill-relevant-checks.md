# hook-block-skill-relevant-checks.sh

Purpose: PreToolUse hook backstop that denies `/relevant-checks` Skill invocation while an active `/implement` or `/review` session is bound to the same Claude hook `cwd` and `session_id`.

Primary registration: `hooks/hooks.json` under `PreToolUse` with matcher `Skill`.

Input: Claude Code hook JSON on stdin. The hook reads `tool_name`, `tool_input.skill`, `tool_input.skill_name`, `cwd`, and `session_id`. Both `relevant-checks` and `larch:relevant-checks` are blocked; all other skills are allowed.

Fail-open contract: if `jq` is missing, JSON parsing fails, the tool is not `Skill`, the skill is not `/relevant-checks`, or `scripts/lib-resolve-active-larch-session.sh` finds no matching active session, the hook exits 0 with empty stdout. This preserves ad-hoc human `/relevant-checks` use outside orchestrators.

Deny contract: on active-session match, stdout is a Claude Code `hookSpecificOutput` envelope with `hookEventName=PreToolUse`, `permissionDecision=deny`, and the fixed reason telling callers to use `scripts/run-relevant-checks-captured.sh`.

Harness: `scripts/test-hook-block-skill-relevant-checks.sh`.

Edit in sync: update this file, the resolver contract, the hook harness, and `hooks/hooks.json` when changing payload keys, skill-name matching, fail-open behavior, or the deny reason.
