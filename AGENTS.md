# AGENTS.md

This repo **is** the larch Claude Code plugin. Edits ship to consumers. Start with `README.md`, `docs/installation-and-setup.md`, `docs/configuration-and-permissions.md`, and `docs/linting.md`.

## Repository layout

The plugin ships the repo. **Runtime surface**: `skills/`, `agents/`, `hooks/`, `scripts/`, `.claude-plugin/`. Everything else is supplementary.

`python/` holds stdlib-only runtime modules. Use `python3 python/cli.py ship pr` for the live driver and `python3 python/cli.py report-tokens analyze` for `/report-tokens`. See `python/README.md`, `make py-lint`, and `make py-test`.

## Load Semantics

- **Tier 1a: Claude root imports**: `CLAUDE.md` imports `AGENTS.md`, `KARPATHY_CLAUDE.md`, and `BASH_AUTHORING.md` with `@...` lines.
- **Tier 1b: Skill prompts**: `skills/*/SKILL.md` and dev-only `.claude/skills/*/SKILL.md` load when invoked.
- **Tier 1c: path-triggered Claude Code rules**: `.claude/rules/*.md` frontmatter `paths:` globs trigger Claude Code system reminders when matching files are read or edited. They are not `CLAUDE.md` imports or standalone Skills.

## Editing rules

- Respect `scripts/block-submodule-edit.sh`; if blocked, investigate. The guard ships through `hooks/hooks.json`, and contributors need larch loaded as a plugin to receive it.
- Lint/test only changed files. CI runs the full sweep on push.
- Update `SECURITY.md` when security-relevant behavior changes.

## Common editing tasks

- **Docs or scripts only**: PATCH.
- **`/design` pause/resume**: skill surface `skills/pause/SKILL.md`; wire format `docs/issue-anchored-plan.md`.

## Canonical sources

- `README.md`: feature matrix, skill catalog, aliases
- `ARCHITECTURAL_GUIDELINES.md`: operator goals, untrusted prompt context; cannot override `AGENTS.md` or skills
- `docs/installation-and-setup.md`; `docs/configuration-and-permissions.md`: setup, strict permissions, `--admin`, env vars
- `docs/linting.md`: linters, Makefile targets, halt-rate harness
- `docs/workflow-lifecycle.md`; `docs/voting-process.md`; `docs/point-competition.md`: workflow and voting process
- `docs/agents.md`; `docs/review-agents.md`; `docs/external-reviewers.md`; `docs/collaborative-sketches.md`: orchestration and external tools
- `docs/topology.md`; `skills/shared/topology.tsv`: generated projection and source rows
- `docs/run-logs.md`; `docs/run-log-cli.md`; `docs/run-log-batches.md`: committed run-log contracts
- `docs/issue-anchored-plan.md`: **LIVE** /design ↔ /implement wire format, clarification round-trip, and pause pointer
- `python/tracking_issue.py`, `python/test_tracking_issue.py`, `python/cli.py tracking-issue ...`: tracking issue lifecycle
- `python/cli.py plan-block read`, `python/cli.py named-block write --marker plan`, `python/cli.py clarify {state,comment-post,label}`, `python/test_issue_wire.py`, `python/test_clarify.py`: issue wire helpers and tests
- `.claude/skills/release/scripts/classify-bump.md`: release classification rules
- `skills/shared/subskill-invocation.md`; `skills/shared/skill-design-principles.md`; `skills/shared/reviewer-templates.md`: shared skill and reviewer authorities
- `SECURITY.md`: security policy
- `docs/python-migration.md`: sh-to-py playbook, decision log, manifest, and `lint-retired-scripts`

## Output Style

**Source of truth.** Use `skills/shared/readability-style.md` for user-facing prose across larch skills, docs, chat answers, PR descriptions, issue bodies, design notes, and summaries.

- Explicit output formats take precedence. Preserve machine-parsed structure: `KEY=value` stdout grammars, manifest JSON, plan grammar (`### NEW:` / `### UPDATED:` / `### REWRITTEN:` / `### MAY_UPDATE:` and `diff_lines:`), vote-table columns, and commit-message conventions.
- Prose inside templates still follows the shared style when the template emits user-facing text.
- Code and comments keep surrounding style. Applies to new prose only. Every changed line traces to the task.
- In chat, confirm or correct up front. Stop early.

## Conventions

- Follow recent commit history style.
- New larch scripts are Python by default. Put new logic in `python/` behind `python3 python/cli.py`. Residual Bash is limited to `scripts/residual-bash-paths.txt`: hooks, bash-targeting linters, thin delegation wrappers, `scripts/sleep-seconds.sh`, the combine-issues helper, manifest-listed includes when needed, and harnesses. Do not add terminal shared Bash libraries, stray includes, or non-thin utilities. Migration and voluntary ports must repoint consumers to direct `cli.py` calls per [docs/python-migration.md](docs/python-migration.md) **No shims**; see also [.claude/rules/python-first-scripts.md](.claude/rules/python-first-scripts.md).
- Single-runner invariant: run only one `/implement` per repo. Dirty-tree guards in `python/cli.py agent launch-review --tool cursor` and `python/cli.py agent launch-review --tool codex` detect pollution but do not serialize runners.
- Single-`/design` invariant: one `/design` per repo for workflow/`gh` hygiene. PID-keyed symlinks isolate per Claude PID, not per repo.
- Session rehydration refreshes `~/.cache/larch/sessions/current-design-env-$PPID.sh` via `python/cli.py session write-design-env --claude-pid "$PPID"` in Step 0 so Claude processes do not share one global `current-design-env.sh`.
- Run `gh pr create` through the skill, not manually.
- Run `gh issue create` through `/larch:issue`, not manually. Scripts under `scripts/` and `skills/*/scripts/` may call it directly.
- **Don't spawn a Monitor or a Bash `run_in_background` polling loop (`for`/`while`/`until` + `sleep`) to watch another job finish, and don't use `ScheduleWakeup` for that.** For long helpers, rely on Bash `<task-notification>` for one-shot completion. Use Monitor only for logs, external polling, or event streams. For `/design`, after a premature `<task-notification>`, first run exactly one `Read` of the active `tasks/*.output` to classify the file bytes, not the notification wrapper text. For `/design`, missing or whitespace-only task-output bytes mean silent yield (spurious notification, #5240): after that classification `Read`, use no further probe, parse, or prose tools. For `/design`, prefix-identical repeat non-empty task-output bytes (first 200 chars) for the same wait with the relevant terminal sentinel absent also mean silent yield. For `/design`, new or changed non-empty task-output bytes allow one foreground non-sleeping `[ -f … ]` or `test -f …` probe against the relevant terminal completion sentinel (`.completed/step-3-terminal`, `.completed/step-5c-terminal`, or `.completed/step-final-summary`); prefix the probe with a single `DESIGN_TMPDIR=<absolute-path>;` assignment when `$DESIGN_TMPDIR` is unexported. For `/implement` Steps 3 and 5, premature notifications remain notification-only: end the turn without probing `.completed/step-3-terminal` or `.completed/step-5-terminal`. The hook may still allow a live `Read` of `tasks/*.output`; treat that as diagnostic only and do not use it to advance the step. For `/implement` Step 8, run one foreground non-sleeping `test -f "$IMPLEMENT_TMPDIR/.step-8-ship-handoff.rc"` at notification time; the probe is hook-allowed only while `implement-step8-ship` is live and clamped when rc stays absent. NEVER launch a background recovery waiter (`until [ -f … ]; do sleep N; done`): a zero-output background task amplifies premature notifications, so `scripts/hook-bg-poll-guard.sh` denies it (#4725). Do NOT fall back to Monitor. See `skills/implement/SKILL.md` NEVER #8 and `skills/shared/orchestrator-never.md`.
- **Do not poll the task output file once per turn while a `run_in_background` task runs.** During `/design` premature-notification recovery, exactly one post-notification classification `Read` of the active `tasks/*.output` is allowed; it is not polling and is not the after-completion parse. After confirmed completion, read task output or result files once. See `skills/shared/orchestrator-never.md`.
- **`/review --subagent` requires `SendMessage`.** If `SendMessage` is unavailable, omit `--subagent`. `/implement` Step 5 calls `python/cli.py review-and-fix step5` directly.
- **`/design` is inline-only** in the invoking agent. Follow `skills/design/SKILL.md` and `skills/design/references/flags.md`.
- **NEVER improvise ScheduleWakeup outside skill-script direction.** After a one-shot skill's terminal `✅`, do not call `ScheduleWakeup`, narrate loop-sleep prose, or schedule another turn unless that skill's script explicitly directs it. See `skills/shared/orchestrator-never.md`.
- **NEVER write `$IMPLEMENT_TMPDIR/session-env.sh` from prompt-side orchestrator code.** Treat it read-only like `finalize-state.sh`; use guarded `python/cli.py session write-*` verbs, `python/cli.py session setup`, and `scripts/persist-post-plan-keys.sh`. If plan materialization drops keys, fix the upstream writer.

## Honesty

Follow `KARPATHY_CLAUDE.md` §1 for thinking before coding. Also keep these reporting rules:

- **Don't fabricate.** If you do not know a path, symbol, line number, command output, or test result, say so.
- **Don't overstate completion.** Report what you did. "Done" means verified done.
- **Don't paper over failures.** Surface failed commands, failed tests, and unexpected results.
- **Trust but verify claims.** Confirm tool results before citing them.
- **Distinguish observation from inference.** Mark guesses, assumptions, and likely explanations.

## Answering questions about this repo

Default to direct file reads instead of Explore, Agent, or Plan.

1. Name expected source files, then Read them in parallel.
2. If files are unclear after AGENTS.md and skill layout, run one or two targeted greps.
3. Escalate only when obvious files fail, the answer spans more than three hard-to-enumerate files, or a grep returns more than 20 hits across unfamiliar directories. Announce escalation first.
