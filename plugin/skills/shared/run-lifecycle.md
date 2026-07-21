# Shared run lifecycle

This contract applies only to a skill whose `SKILL.md` contains
`# larch-run-lifecycle: shared-v1 skill=<name>` in its YAML frontmatter.
The machine-checked ownership registry is
`skills/shared/run-lifecycle-ownership.tsv`. A specialized row replaces the
generic start and terminal commands below. Do not run a second lifecycle path
for a specialized skill.

At invocation start, run this command before the skill performs work:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" run-log lifecycle-start --repo-root "${CLAUDE_PROJECT_DIR:-$PWD}" --skill "<name>"
```

A nested child may lead with
`--lifecycle-parent-context <absolute-context-path>`. Consume one pair, bind
`LIFECYCLE_PARENT_CONTEXT`, and remove it before public parsing. Root,
duplicate, missing, or later flags fail. When set, pass
`--lifecycle-parent-context "$LIFECYCLE_PARENT_CONTEXT"` to the start command.
The lifecycle CLI validates it and derives the immutable parent; no other parent
IDs or environment variables are allowed.

Parse `RUN_ID`, `SKILL`, `LOG_ROOT`, `RUN_DIR`, `CONTEXT_FILE`, `STORAGE_URI`, and
`LIFECYCLE_STARTED` from stdout without `eval` or `source`. Stop if the command
fails or `LIFECYCLE_STARTED` is not `true`.

Callers that already own a run ID pass `--run-id "<id>"`. Specialized owners
also pass their absolute `--log-root` and `--adopt-existing` when rich artifact
setup created the manifest first. The context file persists the validated
identity, staging root, and storage URI so later subprocesses rehydrate them
without shell state.

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
Skill tool, pass the parsed `CONTEXT_FILE` as the target's leading internal
`--lifecycle-parent-context` argument before all target arguments, so the target
starts with a distinct child ID and immutable parent metadata. Apply the same
handoff to every other child Skill call.
