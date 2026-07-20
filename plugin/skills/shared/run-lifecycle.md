# Shared run lifecycle

This contract applies only to a skill whose `SKILL.md` contains
`# larch-run-lifecycle: shared-v1 skill=<name>` in its YAML frontmatter.

At invocation start, run this command before the skill performs work:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" run-log lifecycle-start --repo-root "${CLAUDE_PROJECT_DIR:-$PWD}" --skill "<name>"
```

Parse `RUN_ID`, `SKILL`, `LOG_ROOT`, `RUN_DIR`, `STORAGE_URI`, and
`LIFECYCLE_STARTED` from stdout without `eval` or `source`. Stop if the command
fails or `LIFECYCLE_STARTED` is not `true`.

After start succeeds, run exactly one matching terminal command before the
skill returns. A terminal command must succeed with `LIFECYCLE_FLUSHED=true`.
Treat a nonzero exit or any other value as a loud publication failure.

- Success: `run-log lifecycle-finalize`
- Failure: `run-log lifecycle-failure`
- Operator cancellation: `run-log lifecycle-cancel`
- Non-error early return: `run-log lifecycle-early-return`

Pass `--repo-root "${CLAUDE_PROJECT_DIR:-$PWD}" --skill "<name>" --run-id
"$RUN_ID"` to the selected terminal command. Run it before emitting terminal
user-facing prose.

For a nested child invocation, give the child the parent skill and run ID. The
child passes them to start as `--parent-skill "<parent-name>" --parent-run-id
"<parent-run-id>"`. Parent and child keep distinct `RUN_ID` values and distinct
archives.

Aliases are parent invocations, not alternate names for the target run. Start
and finish the alias under its alias name. When invoking its target through the
Skill tool, keep the alias `SKILL` and `RUN_ID` in context so the target starts
as a distinct child. Apply the same handoff to every other child Skill call.
