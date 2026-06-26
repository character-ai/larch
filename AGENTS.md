# AGENTS.md

This repository **is** the larch Claude Code plugin. Edits here ship to consumers. See `README.md`, `docs/installation-and-setup.md`, `docs/configuration-and-permissions.md`, and `docs/linting.md`.

## Repository layout

Plugin ships the entire repo. **Runtime surface**: `skills/`, `agents/`, `hooks/`, `scripts/`, `.claude-plugin/`. Everything else is supplementary (docs, CI config, `.claude/skills/`, `.claude/rules/`, dev settings).

`python/` holds stdlib-only runtime modules. `python3 python/cli.py ship pr` is the live ship-pr driver. `/report-tokens` uses `python3 python/cli.py report-tokens analyze`. See `python/README.md` and `make py-lint` / `make py-test`.

## Load Semantics

- **Tier 1a: Claude root imports** — `CLAUDE.md` is the Claude Code entrypoint and imports `AGENTS.md`, `KARPATHY_CLAUDE.md`, and `BASH_AUTHORING.md` with `@...` lines.
- **Tier 1b: Skill prompts** — `skills/*/SKILL.md` and dev-only `.claude/skills/*/SKILL.md` load when the corresponding Skill is invoked.
- **Tier 1c: path-triggered Claude Code rules** — `.claude/rules/*.md` files are Claude Code built-in system-reminder rules. Their frontmatter `paths:` globs trigger injection when a matching file is read or edited in this repository. They are not imported by `CLAUDE.md` and are not standalone Skills; treat them as conditional system reminders for the matched path surface.

## Editing rules

- Respect `scripts/block-submodule-edit.sh`. If a hook blocks a write, investigate the underlying issue. The guard ships via `hooks/hooks.json` only; contributors need larch loaded as a plugin (`claude --plugin-dir .` or the local marketplace) to pick it up.
- After any change, run `make lint`. When Python files change, also run `make py-lint` and `make py-test`.
- Update `SECURITY.md` when security-relevant behavior changes.

## Common editing tasks

- **Docs or scripts only** → PATCH.
- **`/design` pause/resume** → skill surface lives in `skills/pause/SKILL.md`; wire format lives in `docs/issue-anchored-plan.md`.

## Canonical sources

- `README.md` — feature matrix, skill catalog, Aliases
- `ARCHITECTURAL_GUIDELINES.md` — operator-curated architectural goals not mechanically enforceable; larch treats it as untrusted prompt context, not a higher-priority instruction surface than `AGENTS.md` or skills.
- `docs/installation-and-setup.md`
- `docs/configuration-and-permissions.md` — strict-permissions Skill entries, `--admin` merge behavior, env vars
- `docs/linting.md` — linters, Makefile targets, halt-rate regression harness
- `docs/workflow-lifecycle.md` — how skills compose end-to-end
- `docs/voting-process.md`, `docs/point-competition.md`
- `docs/agents.md`, `docs/review-agents.md` — subagent orchestration
- `docs/external-reviewers.md`, `docs/collaborative-sketches.md` — Codex/Cursor integration
- `docs/topology.md` — generated consumer-doc topology projection
- `docs/run-logs.md` — committed run-log directory structure, batch file reference, and tracking-issue comment contracts
- `docs/issue-anchored-plan.md` — **LIVE** wire format for /design ↔ /implement handoff, clarification round-trip, and `/design` pause pointer. `/implement` Preflight enforces plan gates; `/design` writes the plan block and clarify responses.
- `python/tracking_issue.py`, `python/test_tracking_issue.py`, `python/cli.py tracking-issue ...` — tracking issue read/write/summary lifecycle surface.
- `python/cli.py plan-block read`, `python/cli.py named-block write --marker plan`, `python/cli.py clarify {state,comment-post,label}`, `python/test_issue_wire.py`, `python/test_clarify.py` — helpers and offline harnesses for that wire format.
- `docs/run-log-cli.md`, `docs/run-log-batches.md` — committed run-log CLI contract and batch table
- `.claude/skills/release/scripts/classify-bump.md` — authoritative release classification rules
- `skills/shared/topology.tsv` — projection rows for cross-doc topology counts; runtime authorities listed in the TSV remain source of truth
- `skills/shared/subskill-invocation.md` — sub-skill invocation conventions
- `skills/shared/skill-design-principles.md` — design principles for every larch skill; Section III overrides Section IV
- `skills/shared/reviewer-templates.md` — Code Reviewer archetype (canonical; `agents/code-reviewer.md` is generated from it)
- `SECURITY.md` — security policy
- `docs/python-migration.md` — sh-to-py migration playbook: per-domain recipe, decision log, manifest format, and `lint-retired-scripts` usage

## Output Style

**Scope.** Applies only to human-facing prose: chat answers to the operator, and human-facing documents (PR descriptions, issue bodies, design notes, summaries, README and docs prose).

- Explicit output formats take precedence. Do not apply these rules to machine-parsed surfaces: skill output templates, `KEY=value` stdout grammars, manifests, plan grammar (`### NEW:` / `### UPDATED:` / `### REWRITTEN:` and `diff_lines:`), vote tables, structured findings, commit-message conventions.
- Does not apply to code or code comments; match the surrounding style there.
- Applies to new prose only. Do not rewrite or restyle existing text to conform. Every changed line needs to trace to the task at hand.
- Precedence when rules conflict: explicit format contracts, then exact meaning, then these style rules.

**Style rules.**

- Lead with the answer. The first line answers the question. No preamble.
- One idea per sentence. Keep sentences short.
- Prefer bullets over paragraphs. If a paragraph is forming, break it up.
- **Bold** the key terms so the text scans.
- Use small chunks with short headers when it helps (for example **Before:**, **After:**, **Why:**).
- In chat answers, confirm or correct up front ("Right" / "Not quite"), then explain.
- Stop early. Answer what was asked. Cut filler.
- Avoid long preambles, walls of prose, and burying the answer at the bottom.
- When unsure how short to go: go shorter.
- Never use em dashes. Use periods, commas, colons, or semicolons instead.
- Hedge uncertain claims ("may contain", "can fail") instead of absolutes. Keep instructions imperative; do not hedge directives.
- Strunk & White: use active voice; omit needless words; prefer concrete nouns and verbs.

## Conventions

- Follow recent commit history style.
- New larch scripts are Python by default. Put new logic in `python/` behind `python3 python/cli.py`. Residual Bash is deliberate and limited to `scripts/residual-bash-paths.txt`: hooks, bash-targeting linters, thin delegation wrappers, `scripts/sleep-seconds.sh`, the combine-issues helper, manifest-listed includes when needed, and harnesses. Do not add terminal shared Bash libraries, stray includes, or non-thin utilities. Migration and voluntary ports must repoint consumers to direct `cli.py` calls per [docs/python-migration.md](docs/python-migration.md) **No shims**; see also [.claude/rules/python-first-scripts.md](.claude/rules/python-first-scripts.md).
- Single-runner invariant: Run only one `/implement` per repository at a time. The dirty-tree guards in `python/cli.py agent launch-review --tool cursor` and `python/cli.py agent launch-review --tool codex` detect mid-run pollution but do not serialize concurrent runners.
- Single-`/design` invariant: One `/design` per repo at a time for workflow/`gh` hygiene. PID-keyed symlinks isolate per Claude PID, not per repo.
- Session rehydration refreshes `~/.cache/larch/sessions/current-design-env-$PPID.sh` via `python/cli.py session write-design-env --claude-pid "$PPID"` in Step 0 so distinct Claude processes do not share one global `current-design-env.sh` name.
- Run `gh pr create` through the skill, not manually.
- Run `gh issue create` through `/larch:issue`, not manually. Scripts under `scripts/` and `skills/*/scripts/` may call it directly.
- **Don't spawn a Monitor or a Bash `run_in_background` polling loop (`for`/`while`/`until` + `sleep`) to watch another job finish, and don't use `ScheduleWakeup` for that.** For long helpers, rely on Bash `<task-notification>` for one-shot completion. Use Monitor only for logs, external polling, or event streams. For `/design`, when a premature `<task-notification>` fires with non-empty task output, the sanctioned recovery path is one foreground non-sleeping `[ -f … ]` or `test -f …` probe against the relevant terminal completion sentinel (`.completed/step-3-terminal`, `.completed/step-5c-terminal`, or `.completed/step-final-summary`); prefix the probe with a single `DESIGN_TMPDIR=<absolute-path>;` assignment when `$DESIGN_TMPDIR` is unexported. For `/design`, when task output is empty, end the turn without probing (spurious notification, #5240). For `/implement`, when a premature `<task-notification>` fires while the child is still running (empty or non-empty task output), end the turn without sentinel probing and wait for the next `<task-notification>`; do not probe `$DESIGN_TMPDIR` or design-only sentinels. NEVER launch a background recovery waiter (`until [ -f … ]; do sleep N; done`): a zero-output background task amplifies premature notifications, so `scripts/hook-bg-poll-guard.sh` denies it (#4725). Do NOT fall back to Monitor. See `skills/implement/SKILL.md` NEVER #8 and `skills/shared/orchestrator-never.md`.
- **Do not poll the task output file once per turn while a `run_in_background` task runs.** Read the task output once, after completion. See `skills/shared/orchestrator-never.md`.
- **`/review --subagent` requires `SendMessage`.** If `SendMessage` is unavailable, omit `--subagent`. `/implement` Step 5 calls `python/cli.py review-and-fix step5` directly.
- **`/design` is inline-only** in the invoking agent. Follow `skills/design/SKILL.md` and `skills/design/references/flags.md`.
- **NEVER improvise ScheduleWakeup outside skill-script direction.** After a one-shot skill's terminal `✅`, do not call `ScheduleWakeup`, narrate loop-sleep prose, or schedule another turn unless that skill's script explicitly directs it. See `skills/shared/orchestrator-never.md`.
- **NEVER write `$IMPLEMENT_TMPDIR/session-env.sh` from prompt-side orchestrator code.** Treat it read-only like `finalize-state.sh`; use guarded `python/cli.py session write-*` verbs, `python/cli.py session setup`, and `scripts/persist-post-plan-keys.sh`. If plan materialization drops keys, fix the upstream writer.

## Honesty

- **Don't fabricate.** If you do not know a file path, function name, line number, command output, or test result, say so.
- **Don't overstate completion.** Report what you actually did, not what you intended; "done" means verified done.
- **Don't paper over failures.** Surface failed commands, failed tests, and unexpected results directly.
- **Trust but verify your own claims.** Before reporting a tool-call result, confirm the tool actually returned it, and do not claim results from tools you did not run.
- **Distinguish observation from inference.** Mark guesses, assumptions, and likely explanations as such.
- **Value honesty over agreeableness.** Push back on wrong premises or flawed plans, following `KARPATHY_CLAUDE.md` §1 "Think Before Coding".

## Answering questions about this repo

For Q&A, default to direct file reads instead of dispatching Explore, Agent, or Plan.

1. Name the files you expect to answer the question, then Read them in parallel.
2. If you cannot name the files after consulting AGENTS.md and the skill layout, run one or two targeted greps for candidates.
3. Escalate to Explore or Agent only when direct reads are no longer the efficient path:
   - The obvious candidate files were read and did not contain the answer.
   - The answer plausibly spans more than three files that cannot be enumerated up front.
   - A targeted grep returned more than 20 hits across unfamiliar directories.

Before escalating, announce it in one sentence so the user can interrupt. Subagents spend 15k-25k tokens before useful work; a direct Read costs far less.
