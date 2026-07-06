# Preparing Your Repository for Agent-Assisted Development

> **Status: SKELETON / DRAFT.** Topic list and structure are under review; sections
> below are stubs (`TODO`) to be filled in once we finalize scope. <!-- remove this banner when the doc is complete -->

Larch works best in a repository that is set up for agents. The good news: the
same setup that makes a repo work well with larch makes it work well with **any**
coding agent (Claude Code, Codex, Cursor, Gemini). This guide is that setup,
distilled from how the larch repository configures itself.

There are two ways to use it:

- **Lift the files.** Point your agent at the [larch repo](https://github.com/character-ai/larch),
  copy the files in the [Starter kit](#starter-kit), and adapt the ones marked *Adapt*.
- **Let your agent do it.** Paste the recipe in [Let your agent do it](#let-your-agent-do-it)
  and let it scaffold the equivalents for your repo.

<!-- TODO(intro): tighten the thesis; one line on "advisory context → mechanical enforcement" as the organizing spine of the doc. -->

## How to use this guide

<!-- TODO: explain the three columns used throughout —
     larch source (which file to look at), and a disposition tag:
       Copy      = take it near-verbatim
       Adapt     = keep the structure, rewrite the content for your stack
       Pattern   = don't copy; reproduce the idea in your own tooling
-->

## Let your agent do it

<!-- TODO: refine this into the canonical paste-in prompt. Draft below. -->

```text
Point yourself at the larch repository (https://github.com/character-ai/larch).
Read: CLAUDE.md, AGENTS.md, KARPATHY_CLAUDE.md, BASH_AUTHORING.md,
ARCHITECTURAL_GUIDELINES.md, .claude/rules/, hooks/hooks.json, and
.pre-commit-config.yaml.

Then scaffold the equivalents for THIS repository (stack: <fill in>):
- Copy KARPATHY_CLAUDE.md nearly verbatim.
- Write a thin CLAUDE.md that @-imports AGENTS.md (plus our behavioral/stack files).
- Draft an AGENTS.md describing THIS repo's layout, conventions, and canonical sources.
- Adapt the linters and hooks to our stack.
- Stub a `checks run-relevant` equivalent that runs our changed-file checks.

Ask me before writing anything you are unsure about.
```

---

## Part I — Instruction files (the context your agent always loads)

The always-on brief. Keep it small; everything here is paid for on every turn.

### 1. `CLAUDE.md` + `AGENTS.md`: a thin root that imports a shared file

*Larch source: `CLAUDE.md`, `GEMINI.md`, `AGENTS.md` · Disposition: **Copy** the pattern, write your own `AGENTS.md`.*

Keep one shared instruction file — `AGENTS.md` — and make every tool's native
entry file a thin shim that imports it. `AGENTS.md` is the emerging cross-vendor
convention: Claude Code, Codex, Cursor, and others look for it. Writing your
instructions there once, instead of duplicating them across `CLAUDE.md`,
`GEMINI.md`, and per-tool configs, gives you a single source of truth that can't
drift out of sync.

In larch, the shims are one line per import. `CLAUDE.md`:

```text
@AGENTS.md
@KARPATHY_CLAUDE.md
@BASH_AUTHORING.md
```

`GEMINI.md`:

```text
@./AGENTS.md
```

Claude Code inlines each `@path` into the always-loaded context, so `CLAUDE.md`
pulls in the shared repo brief plus the behavioral guardrails (§2) and
stack-authoring notes (§3); `GEMINI.md` pulls in just the brief. Keep the shim to
imports only — anything you write directly in `CLAUDE.md` is one more instruction
that can contradict `AGENTS.md` later.

**What to put in `AGENTS.md`.** Treat it as the briefing you would give a new
contributor who is capable but unfamiliar with the repo:

- **What the repo is** — a line or two orienting the agent: what it produces, who
  consumes it.
- **Repository layout** — the runtime/shipping surface versus everything
  supplementary, so edits land in the right place.
- **Editing rules** — what is off-limits, and what must be re-run after a change
  (lints, tests).
- **Conventions** — language and tooling defaults, style, commit-message norms.
- **How to answer questions about this repo** — an escalation policy (see §11).
- **Canonical sources** — a "for X, read Y" map (see §11).
- **Honesty and reporting rules** — don't fabricate, don't overstate completion,
  surface failures.

The shims are copyable as-is (swap the imported filenames for yours); `AGENTS.md`
is the one file you write from scratch — and most of this guide is about what goes
in it.

### 2. Behavioral guardrails (the `KARPATHY_CLAUDE.md` pattern)

<!-- larch source: KARPATHY_CLAUDE.md | disposition: Copy near-verbatim (stack-agnostic) -->
<!-- TODO:
     - Think before coding; simplicity first; surgical changes; goal-driven execution.
     - This file is portable as-is — the mistakes it prevents are model mistakes, not repo mistakes.
-->

### 3. Stack-specific authoring notes (the `BASH_AUTHORING.md` pattern)

<!-- larch source: BASH_AUTHORING.md | disposition: Pattern — write your own -->
<!-- TODO:
     - Capture the recurring, non-obvious pitfalls your agents hit in YOUR language/tooling
       (larch's is Bash quoting, 3.2 portability, grep-probe traps).
     - The payoff: mistakes the agent makes twice become a paragraph it reads before the third.
-->

### 4. Architectural guidelines (`ARCHITECTURAL_GUIDELINES.md`)

<!-- larch source: ARCHITECTURAL_GUIDELINES.md | disposition: Adapt -->
<!-- TODO:
     - Aspirational, coded rules (larch: G-Py-1, G-Sec-1, ...) surfaced in review, not hard-enforced.
     - Explicitly cannot override AGENTS.md / skills.
     - Meta-principle (G-Enf-1): when a rule can be mechanized, graduate it to a lint. Bridges to Part II.
-->

### 5. Keep the always-loaded context lean

<!-- larch source: `python/cli.py lint tier1a-size` | disposition: Pattern -->
<!-- TODO:
     - Why bloat hurts: every token in the root brief is spent on every turn.
     - larch caps the size of its root imports with a lint; lazy-load the rest (skills, rules, docs).
-->

---

## Part II — From judgment to machinery (enforcement)

The core move: when a judgment call recurs, promote it to a rule, hook, lint, or
test so the agent cannot get it wrong (or is reminded exactly when it matters).

### 6. Path-triggered rules (`.claude/rules/`)

<!-- larch source: .claude/rules/*.md | disposition: Copy the pattern (+ some rules verbatim) -->
<!-- TODO:
     - `paths:` frontmatter globs inject a system reminder when a matching file is read/edited.
     - Just-in-time, local guidance instead of bloating the always-on brief.
     - Examples worth copying verbatim: drift-prone-prose-in-docs, shell-strict-mode.
-->

### 7. Hooks (guardrails the agent cannot skip)

<!-- larch source: hooks/hooks.json, scripts/*hook*, scripts/block-submodule-edit.sh, scripts/sessionstart-health.sh | disposition: Adapt -->
<!-- TODO:
     - PreToolUse (block edits / guard bad patterns), PostToolUse, SessionStart (health probe), Stop (fail-close).
     - Deterministic enforcement the model can't argue with.
     - Generic wins: block edits to vendored/submodule dirs; warn on missing required tools at session start.
-->

### 8. Linters (lint what changed; encode your recurring gotchas)

<!-- larch source: .pre-commit-config.yaml, docs/linting.md, scripts/lint-*.sh | disposition: Adapt -->
<!-- TODO:
     - pre-commit as the single source of truth; run on changed files locally, full sweep in CI.
     - Custom lints turn repeated review comments into mechanical checks (this is G-Enf-1 in practice).
-->

### 9. The relevant-checks contract (one command to self-validate)

<!-- larch source: `python/cli.py checks run-relevant`, docs/skills.md "Relevant checks script", README "Non-skill entrypoints" | disposition: Implement your own -->
<!-- TODO:
     - THE key integration point: larch calls a consumer-provided entrypoint that runs the RIGHT
       checks for the changed files, and expects a fail-closed result.
     - Not part of the plugin surface — each repo ships its own executable.
     - Document the contract larch expects (invocation, exit codes, output envelope) and link to it.
     - Doubles as the "how does my agent know its change is good?" answer for any agent.
-->

---

## Part III — Environment & navigability

Reduce friction, and help the agent find its way around.

### 10. Permissions & settings (`.claude/settings.json`)

<!-- larch source: .claude/settings.json, docs/configuration-and-permissions.md | disposition: Adapt -->
<!-- TODO:
     - Allowlist common safe commands so the agent isn't constantly prompted.
     - env vars, model selection, additionalDirectories.
     - Note the /fewer-permission-prompts helper as a way to generate the allowlist from real transcripts.
-->

### 11. A canonical-sources map + a "how to answer questions" policy

<!-- larch source: AGENTS.md "Canonical sources" and "Answering questions about this repo" | disposition: Adapt -->
<!-- TODO:
     - A curated map: "for X, read Y" — so the agent reads the right file instead of guessing/grepping.
     - An escalation policy: direct reads first, then targeted grep, then subagents. Saves tokens and tangents.
-->

### 12. Anti-drift prose conventions

<!-- larch source: .claude/rules/drift-prone-prose-in-docs.md | disposition: Copy -->
<!-- TODO:
     - No hardcoded counts, no line-number refs, no machine-local absolute paths in prose.
     - Single source of truth for derived values. Keeps docs (and this instruction set) from rotting.
-->

### 13. Multi-tool support

<!-- larch source: CLAUDE.md, GEMINI.md, AGENTS.md, docs/external-reviewers.md | disposition: Pattern -->
<!-- TODO:
     - One AGENTS.md, many front doors (CLAUDE.md / GEMINI.md shims).
     - Optional: wiring external tools (Codex/Cursor) as reviewers/implementers.
-->

### 14. Keep `SECURITY.md` in sync

<!-- larch source: SECURITY.md, AGENTS.md editing rule | disposition: Pattern -->
<!-- TODO: update the security policy when security-relevant behavior changes; make that an editing rule. -->

---

## Starter kit

<!-- TODO: this table is the centerpiece — "point your agent at larch and take these." Verify/expand rows. -->

| From larch | What it gives you | Disposition |
|---|---|---|
| `KARPATHY_CLAUDE.md` | Model-mistake guardrails | **Copy** near-verbatim |
| `CLAUDE.md` / `GEMINI.md` | Thin shims importing `AGENTS.md` | **Copy** the pattern |
| `AGENTS.md` | Repo layout, conventions, canonical sources | **Adapt** |
| `BASH_AUTHORING.md` | Stack-specific authoring pitfalls | **Pattern** (write your own) |
| `ARCHITECTURAL_GUIDELINES.md` | Aspirational, coded design rules | **Adapt** |
| `.claude/rules/*.md` | Path-triggered, just-in-time reminders | **Copy** pattern (some rules verbatim) |
| `hooks/hooks.json` + hook scripts | Deterministic guardrails | **Adapt** |
| `.pre-commit-config.yaml` | Changed-file linting | **Adapt** to your stack |
| `checks run-relevant` entrypoint | One command the agent runs to validate a change | **Implement** your own |
| `.claude/settings.json` | Permission allowlists, env, model | **Adapt** |

## Suggested adoption order

<!-- TODO: prioritized checklist. Draft ordering:
     1. Minimum viable: CLAUDE.md + AGENTS.md + KARPATHY_CLAUDE.md, and a `checks run-relevant` entrypoint.
     2. Enforcement: pre-commit linting, a couple of hooks, path-triggered rules.
     3. Polish: architectural guidelines, canonical-sources map, permissions allowlist, multi-tool shims.
-->
