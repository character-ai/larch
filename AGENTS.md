# AGENTS.md

This repository **is** the larch Claude Code plugin. Editing here modifies what ships to consumers. See `README.md` for features and the skill catalog. See `docs/installation-and-setup.md` for installation and prerequisites, `docs/configuration-and-permissions.md` for env vars and permissions, and `docs/linting.md` for Makefile targets and linters.

## Repository layout

Plugin ships the entire repo. **Runtime surface**: `skills/`, `agents/`, `hooks/`, `scripts/`, `.claude-plugin/`. Everything else is supplementary (docs, CI config, `.claude/skills/`, `.claude/rules/`, dev settings).

## Editing rules

- Always respect `scripts/block-submodule-edit.sh`. If a hook blocks a write, investigate and resolve the underlying issue. The guard ships via `hooks/hooks.json` only — `.claude/settings.json` no longer mirrors it, so contributors developing in this repo must load larch as a plugin (`claude --plugin-dir .` or the local marketplace) to pick up the guard.
- After any change, run `/relevant-checks`.
- Update `SECURITY.md` when security-relevant behavior changes.
- Path-scoped editing rules for Claude Code live under `.claude/rules/`. Tools that consume only `AGENTS.md` (Codex, Cursor, Gemini) must consult any `.claude/rules/*.md` whose `paths:` frontmatter glob matches the file(s) being edited.

## Common editing tasks

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

- Follow recent commit history style.
- Single-runner invariant: Run only one `/implement` and one `/fix-issue` per repository at a time. The dirty-tree guards in `launch-cursor-review.sh` and `launch-codex-review.sh` detect mid-run pollution but do not serialize concurrent runners.
- Run `gh pr create` through the skill, not manually.
- Run `gh issue create` through `/larch:issue`, not manually. Scripts under `scripts/` and `skills/*/scripts/` (e.g., hooks) may continue to call `gh issue create` directly — the rule targets interactive / assistant-driven issue creation only.
- Slack env vars are optional; skills degrade gracefully when absent.
- **Don't spawn a Monitor or a Bash `run_in_background` polling loop (`for`/`while`/`until` + `sleep`) to watch another `run_in_background` job finish — and don't reach for `ScheduleWakeup` as a third polling mechanism either.** The Bash tool already emits a `<task-notification>` with `status=completed` (or `failed`) when the original process exits — both forms of poller would just deliver the same signal twice, and a stale poller can keep the session alive long after the watched job has reported. `ScheduleWakeup` is worse than a poller in this role: a non-sentinel `prompt` re-fires on wakeup as a `/loop` input and (per the tool's "pass the same `/loop` prompt back each turn" guidance) perpetuates a `/loop`-style chain that survives past the watched step and into post-completion turns. If you genuinely need a wakeup, rely on the task notification. Use Monitor only for tailing logs, polling *external* state, or per-occurrence event streams; for one-shot "wait until done," rely on the Bash notification. (`/implement` ratchets this stricter — see `skills/implement/SKILL.md` NEVER #9, which forbids `ScheduleWakeup` anywhere in the orchestrator.)
- **NEVER improvise ScheduleWakeup outside skill-script direction.** Single-iteration skills like `/fix-issue`, `/implement`, and `/research` end at their terminal `✅` line. After that line, the orchestrator must not call `ScheduleWakeup`, narrate "next iteration" / "loop sleeping until ..." prose, or schedule a follow-up turn unless the skill being executed contains an explicit on-script directive to do so. Recurring or looping behavior is owned exclusively by `/loop`'s `<<autonomous-loop-dynamic>>` sentinel mechanism — never by orchestrator improvisation in a child skill's terminal turn. **Why**: a one-shot `/fix-issue` run that finished Step 8 cleanup observed the orchestrator inventing a 1800 s `ScheduleWakeup` to fire another `/fix-issue` iteration plus a "Loop sleeping until ..." narration line — neither was on `/fix-issue`'s script, and the wakeup chain survived past tmpdir cleanup, landing follow-up turns in a state where the run was already done. **How to apply**: do not call `ScheduleWakeup` from any skill that does not have a numbered step directing the call. `/implement` ratchets this further with NEVER #9 (forbids `ScheduleWakeup` anywhere in the orchestrator); `/fix-issue` and `/research` carry mirroring NEVER bullets in their own anti-pattern sections.

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
