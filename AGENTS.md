# AGENTS.md

This repository **is** the larch Claude Code plugin. Editing here modifies what ships to consumers. See `README.md` for features and the skill catalog. See `docs/installation-and-setup.md` for installation and prerequisites, `docs/configuration-and-permissions.md` for env vars and permissions, and `docs/linting.md` for Makefile targets and linters.

## Repository layout

Plugin ships the entire repo. **Runtime surface**: `skills/`, `agents/`, `hooks/`, `scripts/`, `.claude-plugin/`. Everything else is supplementary (docs, CI config, `.claude/skills/`, `.claude/rules/`, dev settings).

## Editing rules

- Always respect `scripts/block-submodule-edit.sh`. If a hook blocks a write, investigate and resolve the underlying issue. The guard ships via `hooks/hooks.json` only — `.claude/settings.json` no longer mirrors it, so contributors developing in this repo must load larch as a plugin (`claude --plugin-dir .` or the local marketplace) to pick up the guard.
- After any change, run `/relevant-checks`.
- Public `skills/*/SKILL.md` use `${CLAUDE_PLUGIN_ROOT}/…`; dev-only `.claude/skills/*/SKILL.md` use `$PWD/…`.
- Update `SECURITY.md` when security-relevant behavior changes.
- Path-scoped editing rules for Claude Code live under `.claude/rules/`. Tools that consume only `AGENTS.md` (Codex, Cursor, Gemini) must consult `.claude/rules/script-md-siblings.md`, `.claude/rules/skill-editing-trace.md`, and `.claude/rules/version-bump-reserved-message.md` when editing scripts, `SKILL.md` files, or `.claude-plugin/plugin.json`.

## Common editing tasks

- **Adding/modifying the Code Reviewer archetype** → edit `skills/shared/reviewer-templates.md` (canonical; update triggers in that file), then run `bash scripts/generate-code-reviewer-agent.sh` to regenerate `agents/code-reviewer.md`; CI's `agent-sync` job runs the registry walker (`scripts/check-generators.sh`) to enforce drift across all registered generators. For any other reviewer archetype, follow the general rule: identify the canonical source and mirror updates to any generated outputs.
- **Changing a shared script** → edit `scripts/<name>.sh`, read its sibling `scripts/<name>.md` for the contract, then grep for callers across `skills/`, `hooks/`, `.claude/settings.json`, `.github/workflows/`, and other scripts.
- **Changing dev-only skills** → edit under `.claude/skills/bump-version/` or `.claude/skills/relevant-checks/`.
- **Adding/changing a topology count** → first ensure the runtime authority for that count is updated; then edit `skills/shared/topology.tsv`; then run `bash scripts/generate-topology-docs.sh` to regenerate `docs/topology.md`. Consumer docs that link to `docs/topology.md` need no edit unless a new row anchor is being introduced.
- **Docs or scripts only** → classified as PATCH.

## Canonical sources

- `README.md` — feature matrix, skill catalog, Aliases
- `docs/installation-and-setup.md` — installation, setup recipes, prerequisites
- `docs/configuration-and-permissions.md` — strict-permissions Skill entries, `--admin` merge behavior, env vars
- `docs/linting.md` — linters, Makefile targets, halt-rate regression harness
- `docs/workflow-lifecycle.md` — how skills compose end-to-end
- `docs/voting-process.md`, `docs/point-competition.md` — review mechanics
- `docs/agents.md`, `docs/review-agents.md` — subagent orchestration
- `docs/external-reviewers.md`, `docs/collaborative-sketches.md` — Codex/Cursor integration
- `docs/topology.md` — generated consumer-doc topology projection
- `.claude/skills/bump-version/SKILL.md` — authoritative version classification rules
- `skills/shared/topology.tsv` — projection rows for cross-doc topology counts; runtime authorities listed in the TSV remain source of truth
- `skills/shared/subskill-invocation.md` — sub-skill invocation conventions (invocation patterns, `allowed-tools` narrowing, post-invocation verification, anti-halt continuation reminder, session-env handoff)
- `skills/shared/skill-design-principles.md` — design principles for every larch skill (knowledge delta, structure, mechanical rules A/B/C, writing style, anti-patterns, freedom calibration); Section III overrides Section IV for larch skills
- `skills/shared/reviewer-templates.md` — Code Reviewer archetype (canonical; `agents/code-reviewer.md` is generated from it)
- `SECURITY.md` — security policy

## Conventions

- Shell scripts use `set -euo pipefail` by default. Comment when `-e` is intentionally omitted.
- Follow recent commit history style.
- Run `gh pr create` through the skill, not manually.
- Run `gh issue create` through `/larch:issue`, not manually. Scripts under `scripts/` and `skills/*/scripts/` (e.g., hooks) may continue to call `gh issue create` directly — the rule targets interactive / assistant-driven issue creation only.
- Slack env vars are optional; skills degrade gracefully when absent.
- **Don't spawn a Monitor or a Bash `run_in_background` polling loop (`for`/`while`/`until` + `sleep`) to watch another `run_in_background` job finish — and don't reach for `ScheduleWakeup` as a third polling mechanism either.** The Bash tool already emits a `<task-notification>` with `status=completed` (or `failed`) when the original process exits — both forms of poller would just deliver the same signal twice, and a stale poller can keep the session alive long after the watched job has reported. `ScheduleWakeup` is worse than a poller in this role: a non-sentinel `prompt` re-fires on wakeup as a `/loop` input and (per the tool's "pass the same `/loop` prompt back each turn" guidance) perpetuates a `/loop`-style chain that survives past the watched step and into post-completion turns. If you genuinely need a wakeup, rely on the task notification. Use Monitor only for tailing logs, polling *external* state, or per-occurrence event streams; for one-shot "wait until done," rely on the Bash notification. (`/implement` ratchets this stricter — see `skills/implement/SKILL.md` NEVER #9, which forbids `ScheduleWakeup` anywhere in the orchestrator.)

## Honesty

- **Don't fabricate.** If you do not know a file path, function name, line number, command output, or test result, say so.
- **Don't overstate completion.** Report what you actually did, not what you intended; "done" means verified done.
- **Don't paper over failures.** Surface failed commands, failed tests, and unexpected results directly.
- **Trust but verify your own claims.** Before reporting a tool-call result, confirm the tool actually returned it, and do not claim results from tools you did not run.
- **Distinguish observation from inference.** Mark guesses, assumptions, and likely explanations as such.
- **Value honesty over agreeableness.** Push back on wrong premises or flawed plans, following `KARPATHY_CLAUDE.md` §1 "Think Before Coding" rather than duplicating that guidance here.

## Answering questions about this repo

For Q&A about this repository, default to direct file reads instead of dispatching Explore, Agent, or Plan.

1. Name the files you expect to answer the question, then Read them in parallel.
2. If you cannot name the files after consulting AGENTS.md and the skill layout, run one or two targeted greps to find the relevant candidates.
3. Escalate to Explore or Agent only when direct reads are no longer the efficient path:
   - The obvious candidate files were read and did not contain the answer.
   - The answer plausibly spans more than three files that cannot be enumerated up front.
   - A targeted grep returned more than 20 hits across unfamiliar directories.

Before escalating, announce the escalation in one sentence so the user can interrupt. Treat subagents as a larger-context tool: a subagent spends roughly 15k-25k tokens of baseline overhead before doing useful work, while a direct Read costs a few hundred to a few thousand tokens.
