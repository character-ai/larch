# AGENTS.md

This repository **is** the larch Claude Code plugin. Editing here modifies what ships to consumers. See `README.md` for features and the skill catalog. See `docs/installation-and-setup.md` for installation and prerequisites, `docs/configuration-and-permissions.md` for env vars and permissions, and `docs/linting.md` for Makefile targets and linters.

## Repository layout

Plugin ships the entire repo. **Runtime surface**: `skills/`, `agents/`, `hooks/`, `scripts/`, `.claude-plugin/`. Everything else is supplementary (docs, CI config, `.claude/skills/`, `.claude/rules/`, dev settings).

`python/` holds the `ship-pr.sh` → Python rework tree. Runtime modules are stdlib-only; the live `/implement` path is wired behind `LARCH_SHIP_PR_IMPL` (default `bash`, optional `python`) while `ship-pr.sh` removal is deferred. See `python/README.md` for layout and `make py-lint` / `make py-test`.

## Load Semantics

- **Tier 1a: Claude root imports** — `CLAUDE.md` is the Claude Code entrypoint and imports `AGENTS.md`, `KARPATHY_CLAUDE.md`, and `BASH_AUTHORING.md` with `@...` lines.
- **Tier 1b: Skill prompts** — `skills/*/SKILL.md` and dev-only `.claude/skills/*/SKILL.md` load when the corresponding Skill is invoked.
- **Tier 1c: path-triggered Claude Code rules** — `.claude/rules/*.md` files are Claude Code built-in system-reminder rules. Their frontmatter `paths:` globs trigger injection when a matching file is read or edited in this repository. They are not imported by `CLAUDE.md` and are not standalone Skills; treat them as conditional system reminders for the matched path surface.

## Editing rules

- Always respect `scripts/block-submodule-edit.sh`. If a hook blocks a write, investigate and resolve the underlying issue. The guard ships via `hooks/hooks.json` only — `.claude/settings.json` no longer mirrors it, so contributors developing in this repo must load larch as a plugin (`claude --plugin-dir .` or the local marketplace) to pick up the guard.
- After any change, run `bash scripts/relevant-checks.sh` (or `make lint`, which exercises the same pre-commit hooks repo-wide).
- Update `SECURITY.md` when security-relevant behavior changes.

## Common editing tasks

- **Docs or scripts only** → classified as PATCH.
- **`/design` pause/resume** → skill surface lives in `skills/pause/SKILL.md`; wire format lives in `docs/issue-anchored-plan.md`.

## Canonical sources

- `README.md` — feature matrix, skill catalog, Aliases
- `docs/installation-and-setup.md`
- `docs/configuration-and-permissions.md` — strict-permissions Skill entries, `--admin` merge behavior, env vars
- `docs/linting.md` — linters, Makefile targets, halt-rate regression harness
- `docs/workflow-lifecycle.md` — how skills compose end-to-end
- `docs/voting-process.md`, `docs/point-competition.md`
- `docs/agents.md`, `docs/review-agents.md` — subagent orchestration
- `docs/external-reviewers.md`, `docs/collaborative-sketches.md` — Codex/Cursor integration
- `docs/topology.md` — generated consumer-doc topology projection
- `docs/run-logs.md` — committed run-log directory structure, batch file reference, and tracking-issue comment contracts
- `docs/issue-anchored-plan.md` — **LIVE** normative wire format for the /design ↔ /implement plan handoff, clarification round-trip, and `/design` pause pointer (`larch:plan` + `larch:design-pause` body markers, `larch:clarify-*` comments, label helper). `/implement` Preflight enforces plan presence/adequacy and refuse exit **3** (`--emergency` may bypass these gates with loud warnings; semantic materiality still fires); `/design` writes/updates the plan block and posts clarify responses. Landed work may still extend `Makefile`, `agent-lint.toml`, harnesses under `scripts/test-*.sh`, and (when an `/implement` run is recorded) paths under `larch-logs/implement/` per `docs/run-logs.md`.
- `scripts/plan-block-read.sh`, `scripts/plan-block-write.sh`, `scripts/clarify-comment-post.sh`, `scripts/clarify-state.sh`, `scripts/clarify-label.sh`, `scripts/test-plan-block.sh`, `scripts/test-clarify-comment.sh`, `scripts/test-clarify-state.sh` — helpers and offline harnesses for that wire format (Makefile registers the `test-*` targets).
- `scripts/lib-quiet.md` — quiet-by-default contract stream for larch scripts (FD 3, `emit`/`emit_kv` API, `LARCH_QUIET_DISABLE` escape hatch)
- `scripts/larch-log.md`, `scripts/larch-log-batches.md` — committed run-log contract and batch table
- `.claude/skills/release/scripts/classify-bump.md` — authoritative release classification rules
- `skills/shared/topology.tsv` — projection rows for cross-doc topology counts; runtime authorities listed in the TSV remain source of truth
- `skills/shared/subskill-invocation.md` — sub-skill invocation conventions (invocation patterns, `allowed-tools` narrowing, post-invocation verification, anti-halt continuation reminder, session-env handoff)
- `skills/shared/skill-design-principles.md` — design principles for every larch skill (knowledge delta, structure, mechanical rules A/B/C, writing style, anti-patterns, freedom calibration); Section III overrides Section IV for larch skills
- `skills/shared/reviewer-templates.md` — Code Reviewer archetype (canonical; `agents/code-reviewer.md` is generated from it)
- `SECURITY.md` — security policy

## Conventions

- Follow recent commit history style.
- Single-runner invariant: Run only one `/implement` per repository at a time. The dirty-tree guards in `launch-review.sh --tool cursor` and `launch-review.sh --tool codex` detect mid-run pollution but do not serialize concurrent runners.
- Single-`/design` invariant: One `/design` per repo at a time (workflow/`gh` hygiene, mirroring `/implement` single-runner) — **not** because PID-keyed symlinks would collide across clones; isolation is per–Claude PID, not per-repo serialization.
- Session rehydration refreshes `~/.cache/larch/sessions/current-design-env-$PPID.sh` via `scripts/write-design-current-env.sh --claude-pid "$PPID"` in Step 0 so distinct Claude processes do not share one global `current-design-env.sh` name.
- Run `gh pr create` through the skill, not manually.
- Run `gh issue create` through `/larch:issue`, not manually. Scripts under `scripts/` and `skills/*/scripts/` (e.g., hooks) may continue to call `gh issue create` directly — the rule targets interactive / assistant-driven issue creation only.
- **Don't spawn a Monitor or a Bash `run_in_background` polling loop (`for`/`while`/`until` + `sleep`) to watch another `run_in_background` job finish — and don't reach for `ScheduleWakeup` as a third polling mechanism either.** For long-running helper scripts (`ship-pr.sh`, `ci-wait.sh`, `run-step5-review.sh`, etc.), rely on Bash `<task-notification>` for one-shot completion (the harness auto-backgrounds an overrunning foreground call). Use Monitor only for logs, external polling, or event streams. See `skills/implement/SKILL.md` NEVER #9 for incident-level rationale.
- **Do not poll the task output file once per turn while a `run_in_background` task runs.** Reading the task output file each turn to check progress is polling by another name — each read costs a full LLM turn (the #3175 incident burned ~80 turns this way, via repeated Bash reads of the task output file). The polling-loop bullet above already routes completion through `<task-notification>`; this names the manual per-turn-read shape that bullet does not. Read the task output once, after completion — never re-read it across turns. See `skills/shared/orchestrator-never.md` for the incident-level rationale.
- **`/review --subagent` requires `SendMessage`.** Standalone `/review --diff --subagent` runs the review loop (Steps 1-3: gather context, launch reviewers, collect/vote/fix) in an isolated Agent-tool subagent (see `skills/review/references/heavy-worker.md`). If `SendMessage` is unavailable, omit `--subagent`. `/implement` Step 5 no longer invokes `/review`; it calls `skills/review-and-fix/scripts/review-and-fix.sh` directly.
- **`/design` is inline-only** in the invoking agent — follow `skills/design/SKILL.md` for the step script and `skills/design/references/flags.md` for flag-level detail (there is no separate `SendMessage`-isolated `/design` mode).
- **NEVER improvise ScheduleWakeup outside skill-script direction.** After a one-shot skill's terminal `✅`, do not call `ScheduleWakeup`, narrate loop-sleep prose, or schedule another turn unless that skill's script explicitly directs it; looping belongs to `/loop`'s `<<autonomous-loop-dynamic>>` sentinel only. See `skills/implement/SKILL.md` NEVER #9, `skills/shared/orchestrator-never.md` (canonical incident-level "Why" / "How to apply" narrative), and `skills/research/SKILL.md` (entry pointer / policy context).
- **NEVER write `$IMPLEMENT_TMPDIR/session-env.sh` from prompt-side orchestrator code.** Treat it read-only like `finalize-state.sh`; use only `scripts/write-session-env.sh`, `scripts/session-setup.sh`, and `scripts/persist-post-plan-keys.sh` after Preflight. If plan materialization drops keys, fix the upstream writer — never append via prompt-side `printf`. See `skills/implement/SKILL.md` NEVER #14 for the #2326 incident rationale.

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
