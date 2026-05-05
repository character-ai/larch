# AGENTS.md

This repository **is** the larch Claude Code plugin. Editing here modifies what ships to consumers. See `README.md` for features and the skill catalog. See `docs/installation-and-setup.md` for installation and prerequisites, `docs/configuration-and-permissions.md` for env vars and permissions, and `docs/linting.md` for Makefile targets and linters.

## Repository layout

Plugin ships the entire repo. **Runtime surface**: `skills/`, `agents/`, `hooks/`, `scripts/`, `.claude-plugin/`. Everything else is supplementary (docs, CI config, `.claude/skills/`, dev settings).

## Editing rules

- Use `/bump-version` to change `.claude-plugin/plugin.json` version — it owns that commit; `Bump version to X.Y.Z` is a reserved commit message.
- Always respect `scripts/block-submodule-edit.sh`. If a hook blocks a write, investigate and resolve the underlying issue. The guard ships via `hooks/hooks.json` only — `.claude/settings.json` no longer mirrors it, so contributors developing in this repo must load larch as a plugin (`claude --plugin-dir .` or the local marketplace) to pick up the guard.
- After any change, run `/relevant-checks`.
- Public `skills/*/SKILL.md` use `${CLAUDE_PLUGIN_ROOT}/…`; dev-only `.claude/skills/*/SKILL.md` use `$PWD/…`.
- Update `SECURITY.md` when security-relevant behavior changes.
- **Per-script contracts live beside the script.** Every `.sh` / `.py` script under `scripts/` and `skills/<name>/scripts/` has a sibling `<basename>.md` next to it (e.g., `scripts/redact-secrets.md` beside `scripts/redact-secrets.sh`) documenting the script's purpose, primary callers, invariants, Makefile wiring, test harness, and edit-in-sync rules. When editing a script, read its sibling `.md` first; update it in the same PR as any behavioral change. Two co-location patterns are permitted, neither is an exemption from the file-existence rule:
  - **Primary owns the full contract.** Where a primary script has a sourced-only library (`scripts/lib-*.sh` — no shebang) and/or a regression test harness (`scripts/test-*.sh` for the primary), the primary's `.md` owns the full contract and cites the related files by path. The library and harness still get their own sibling `.md` (typically a one-paragraph stub) so every `.sh` has a sibling for discoverability and audit; the stub points readers to the primary's `.md` rather than restating the contract.
  - **Cross-tree harnesses.** A test harness may live under `scripts/test-*.sh` while its primary lives at `skills/<name>/scripts/<primary>.sh` (e.g. `scripts/test-post-scaffold-hints.sh` testing `skills/create-skill/scripts/post-scaffold-hints.sh`). The primary's `.md` (in its own tree) owns the full contract; the harness in `scripts/` still gets a sibling `.md` stub naming its primary.

  For canonical documentation files (`skills/shared/*.md`), update triggers live inside the file itself at the bottom.

## Common editing tasks

- **Changing a skill** → start at `skills/<name>/SKILL.md`, then trace every helper in `skills/<name>/scripts/`, `scripts/`, and `skills/shared/`. Behavior is split between prompt and scripts.
- **Adding/modifying the Code Reviewer archetype** → edit `skills/shared/reviewer-templates.md` (canonical; update triggers in that file), then run `bash scripts/generate-code-reviewer-agent.sh` to regenerate `agents/code-reviewer.md`. For any other reviewer archetype, follow the general rule: identify the canonical source and mirror updates to any generated outputs.
- **Changing a shared script** → edit `scripts/<name>.sh`, read its sibling `scripts/<name>.md` for the contract, then grep for callers across `skills/`, `hooks/`, `.claude/settings.json`, `.github/workflows/`, and other scripts.
- **Changing dev-only skills** → edit under `.claude/skills/bump-version/` or `.claude/skills/relevant-checks/`.
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
- `.claude/skills/bump-version/SKILL.md` — authoritative version classification rules
- `skills/shared/subskill-invocation.md` — sub-skill invocation conventions (invocation patterns, `allowed-tools` narrowing, post-invocation verification, anti-halt continuation reminder, session-env handoff)
- `skills/shared/skill-design-principles.md` — design principles for every larch skill (knowledge delta, structure, mechanical rules A/B/C, writing style, anti-patterns, freedom calibration); Section III overrides Section IV for larch skills
- `skills/shared/reviewer-templates.md` — Code Reviewer archetype (canonical; `agents/code-reviewer.md` is generated from it)
- `SECURITY.md` — security policy

## Conventions

- Shell scripts use `set -euo pipefail` by default. Comment when `-e` is intentionally omitted.
- Follow recent commit history style. `Bump version to X.Y.Z` is reserved for `/bump-version`.
- Run `gh pr create` through the skill, not manually.
- Run `gh issue create` through `/larch:issue`, not manually. Scripts under `scripts/` and `skills/*/scripts/` (e.g., hooks) may continue to call `gh issue create` directly — the rule targets interactive / assistant-driven issue creation only.
- Slack env vars are optional; skills degrade gracefully when absent.
- **Don't spawn a Monitor or a Bash `run_in_background` polling loop (`for`/`while`/`until` + `sleep`) to watch another `run_in_background` job finish — and don't reach for `ScheduleWakeup` as a third polling mechanism either.** The Bash tool already emits a `<task-notification>` with `status=completed` (or `failed`) when the original process exits — both forms of poller would just deliver the same signal twice, and a stale poller can keep the session alive long after the watched job has reported. `ScheduleWakeup` is worse than a poller in this role: a non-sentinel `prompt` re-fires on wakeup as a `/loop` input and (per the tool's "pass the same `/loop` prompt back each turn" guidance) perpetuates a `/loop`-style chain that survives past the watched step and into post-completion turns. If you genuinely need a wakeup, rely on the task notification. Use Monitor only for tailing logs, polling *external* state, or per-occurrence event streams; for one-shot "wait until done," rely on the Bash notification. (`/implement` ratchets this stricter — see `skills/implement/SKILL.md` NEVER #9, which forbids `ScheduleWakeup` anywhere in the orchestrator.)

## Answering questions about this repo

For Q&A about this repository, default to direct file reads instead of dispatching Explore, Agent, or Plan.

1. Name the files you expect to answer the question, then Read them in parallel.
2. If you cannot name the files after consulting AGENTS.md and the skill layout, run one or two targeted greps to find the relevant candidates.
3. Escalate to Explore or Agent only when direct reads are no longer the efficient path:
   - The obvious candidate files were read and did not contain the answer.
   - The answer plausibly spans more than three files that cannot be enumerated up front.
   - A targeted grep returned more than 20 hits across unfamiliar directories.

Before escalating, announce the escalation in one sentence so the user can interrupt. Treat subagents as a larger-context tool: a subagent spends roughly 15k-25k tokens of baseline overhead before doing useful work, while a direct Read costs a few hundred to a few thousand tokens.
