# Larch

Larch is a Claude Code workflow automation framework that orchestrates multi-agent design, code review, and implementation through collaborative AI-driven processes.

## Table of Contents

- **Setup**
  - [Installation and Setup](docs/installation-and-setup.md) — plugin install, local development, agent setup recipes (Claude / Codex / Cursor), [clean-main entry contract](docs/installation-and-setup.md#clean-main-entry-contract-for-implement-and-design) for `/implement` and `/design`, what the plugin provides, `/relevant-checks` consumer dependency, prerequisites
  - [Configuration and Permissions](docs/configuration-and-permissions.md) — [Strict-permissions consumers](docs/configuration-and-permissions.md#strict-permissions-consumers--skill-permission-entries), [`--admin` merge behavior](docs/configuration-and-permissions.md#--admin-merge-behavior), [Environment Variables](docs/configuration-and-permissions.md#environment-variables) (`LARCH_SLACK_*`, `LARCH_CURSOR_MODEL`, `LARCH_CODEX_MODEL`, `LARCH_CODEX_EFFORT`, `LARCH_BUMP_FILES`)
- **Reference**
  - [Features](#features)
  - [Skills](#skills)
  - [Aliases](#aliases)
  - [Review Agents](docs/review-agents.md) — the unified `code-reviewer` archetype
  - [Topology Projection](docs/topology.md) — stable anchors for cross-doc topology counts
  - [Linting](docs/linting.md) — linters, Makefile targets, halt-rate regression harness
- **Architecture and workflow**
  - [Workflow Lifecycle](docs/workflow-lifecycle.md) — how skills compose end-to-end
  - [Agent System](docs/agents.md) — parallel subagent orchestration
  - [Collaborative Sketches](docs/collaborative-sketches.md) — the diverge-then-converge design phase
  - [External Reviewers](docs/external-reviewers.md) — Codex and Cursor integration (Gemini machinery retained but not actively invoked)
  - [Voting Process](docs/voting-process.md) — the voting panel protocol
  - [Point Competition](docs/point-competition.md) — reviewer scoring system

## Features

- **[Multi-agent design planning, reviews, and adjudication](docs/collaborative-sketches.md)** — the [configured sketch topology](docs/topology.md#design.sketch.regular_slots) diverges, the [dialectic judge panel](docs/topology.md#design.dialectic.judge_panel) resolves contested decisions, and the [validation panel](docs/topology.md#design.plan_review.cursor_archetypes) reviews the final plan.
- **[Voting-based review resolution](docs/voting-process.md)** — The YES/NO/EXONERATE panel protocol adjudicates plan and code review findings.
- **[Reviewer competition scoring](docs/point-competition.md)** — Reviewers earn points based on finding quality; a scoreboard tracks accepted, neutral, exonerated, and rejected findings.
- **[End-to-end automation](docs/workflow-lifecycle.md)** — From feature design through PR creation and initial CI wait in one command; `--merge` adds the CI+rebase+merge loop, local cleanup, and main verification. Each run also posts a single Slack status message about its tracking issue near the end (✅ closed / 📝 PR opened / 🧭 design complete / ❌ blocked / ❓ user input needed) when Slack is configured — opt out with `--no-slack`. `--draft` creates a draft PR and keeps the branch for further iteration; `--design-only` publishes the design artifacts to the tracking issue and stops before implementation.
- **[External reviewer integration](docs/external-reviewers.md)** — Codex and Cursor participate alongside Claude subagents as sketch agents, debaters, judges, reviewers, and voters. Gemini reviewer call sites have been removed from `/review` and `/implement --quick` review rounds; the launcher (`scripts/launch-gemini-review.sh`), policy file, regression harness, and agent prompt remain as machinery, and Gemini can still be selected explicitly for implementation with `/implement --coder=gemini`.
- **[Tracked runs](skills/implement/SKILL.md)** — `/implement` PRs link to a tracking issue whose anchor comment is the single source of truth for full report content (voting tallies, rejected findings, version-bump reasoning, diagrams, OOS links, execution issues, run statistics).

## Skills

<table>
  <thead>
    <tr><th>Name</th><th>Arguments</th></tr>
  </thead>
  <tbody>
    <tr>
      <td><a href="docs/skills.md#alias"><code>/alias</code></a></td>
      <td><code>[--merge] [--no-slack] [--private] &lt;alias-name&gt; &lt;target-skill&gt; [preset-flags...]</code></td>
    </tr>
    <tr><td colspan="2">Create an alias for a larch skill with preset flags. Auto-routes to <code>skills/&lt;n&gt;/</code> in plugin source repos and <code>.claude/skills/&lt;n&gt;/</code> elsewhere; <code>--private</code> forces the latter.</td></tr>
    <tr><td colspan="2"><hr></td></tr>
    <tr>
      <td><a href="docs/skills.md#compress-skill"><code>/compress-skill</code></a></td>
      <td><code>[--no-slack] &lt;skill-name-or-path&gt;</code></td>
    </tr>
    <tr><td colspan="2">Compress a skill's Markdown prose via a behavior-preserving rewrite.</td></tr>
    <tr><td colspan="2"><hr></td></tr>
    <tr>
      <td><a href="docs/skills.md#create-skill"><code>/create-skill</code></a></td>
      <td><code>[--plugin] [--multi-step] [--merge] [--no-slack] &lt;skill-name&gt; &lt;description&gt;</code></td>
    </tr>
    <tr><td colspan="2">Scaffold a new larch-style skill from a name and description.</td></tr>
    <tr><td colspan="2"><hr></td></tr>
    <tr>
      <td><a href="docs/skills.md#design"><code>/design</code></a></td>
      <td><code>[--auto] [--quick] [--subagent] [--session-env &lt;path&gt;] &lt;feature description&gt;</code></td>
    </tr>
    <tr><td colspan="2">Design an implementation plan with the <a href="docs/topology.md#design.sketch.regular_slots">configured sketch topology</a>, dialectic adjudication, and the <a href="docs/topology.md#design.plan_review.cursor_archetypes">validation panel</a> described in the design workflow.</td></tr>
    <tr><td colspan="2"><hr></td></tr>
    <tr>
      <td><a href="docs/skills.md#fix-issue"><code>/fix-issue</code></a></td>
      <td><code>[--auto] [--no-slack] [--no-admin-fallback] [--coder=&lt;value&gt;] [--inline] [&lt;number-or-url&gt;]</code></td>
    </tr>
    <tr><td colspan="2">Process one approved GitHub issue per invocation, classifying intent and delegating PR work to <code>/implement</code>.</td></tr>
    <tr><td colspan="2"><hr></td></tr>
    <tr>
      <td><a href="docs/skills.md#implement"><code>/implement</code></a></td>
      <td><code>[--quick] [--auto] [--design-only] [--inline] [--merge | --draft] [--no-slack] [--no-admin-fallback] [--coder=claude|codex|cursor|gemini] [--session-env &lt;path&gt;] [--issue &lt;N&gt;] &lt;feature description&gt;</code></td>
    </tr>
    <tr><td colspan="2">Full end-to-end feature workflow — design, implement, PR. <code>--design-only</code> publishes plan/review/diagram/OOS artifacts to the tracking issue and stops before implementation. <code>--quick</code> skips <code>/design</code> and runs a code-review loop of up to 7 rounds (no voting panel): rounds 1-3 launch 5 Cursor specialists in parallel plus a generic Codex reviewer; rounds 4-7 use a single generic reviewer per round with a Cursor → Codex → Claude fallback chain. <code>--coder</code> selects the Step 2 implementer (default <code>codex</code> — spawns the Codex implementer; pass <code>claude</code> to run in the main agent / Claude context, <code>cursor</code> for the Cursor implementer, or <code>gemini</code> for the Gemini implementer; <code>cursor</code> and <code>gemini</code> fall back to the main-agent path when unhealthy or unavailable). <code>LARCH_CURSOR_MODEL</code> drives the Cursor implementer when <code>--coder=cursor</code>; <code>LARCH_GEMINI_MODEL</code> drives Gemini when <code>--coder=gemini</code>.</td></tr>
    <tr><td colspan="2"><hr></td></tr>
    <tr>
      <td><a href="docs/skills.md#issue"><code>/issue</code></a></td>
      <td><code>[--input-file FILE] [--title-prefix P] [--label L]... [--body-file F] [--dry-run] [--go] [&lt;issue description&gt;]</code></td>
    </tr>
    <tr><td colspan="2">Create one or more GitHub issues with LLM-based semantic duplicate detection and always-on inter-issue blocker-dependency analysis.</td></tr>
    <tr><td colspan="2"><hr></td></tr>
    <tr>
      <td><a href="docs/skills.md#relevant-checks"><code>/relevant-checks</code></a></td>
      <td><em>(none)</em></td>
    </tr>
    <tr><td colspan="2">Run pre-commit linters scoped to changed files. <strong>Not part of the plugin surface; each consuming repo provides its own.</strong></td></tr>
    <tr><td colspan="2"><hr></td></tr>
    <tr>
      <td><a href="docs/skills.md#research"><code>/research</code></a></td>
      <td><code>[--no-issue] &lt;research question or topic&gt;</code></td>
    </tr>
    <tr><td colspan="2">Collaborative best-effort read-only research with the fixed-shape topology documented in the research skill — planner pre-pass, <a href="docs/topology.md#research.lanes">Codex-first research lanes</a> by angle, and the <a href="docs/topology.md#research.validation_panel">validation panel</a>. Every run includes unconditional citation validation (HEAD-fetches cited URLs under SSRF guards, validates DOIs, spot-checks file:line refs) emitted as a fail-soft PASS / FAIL / UNKNOWN ledger spliced into the final report.</td></tr>
    <tr><td colspan="2"><hr></td></tr>
    <tr>
      <td><a href="docs/skills.md#review"><code>/review</code></a></td>
      <td><code>[--diff] [--no-issues] [&lt;description&gt;]</code></td>
    </tr>
    <tr><td colspan="2">Code review with the specialist panel described in <code>docs/review-agents.md</code>. <code>--diff</code>: review branch changes and implement fixes. <code>&lt;description&gt;</code>: review existing code and file accepted findings as GitHub issues (default; <code>--no-issues</code> to suppress).</td></tr>
    <tr><td colspan="2"><hr></td></tr>
    <tr>
      <td><a href="docs/skills.md#simplify-skill"><code>/simplify-skill</code></a></td>
      <td><code>[--no-slack] &lt;skill-name&gt;</code></td>
    </tr>
    <tr><td colspan="2">Refactor a skill for stronger adherence to design principles and reduced SKILL.md footprint.</td></tr>
    <tr><td colspan="2"><hr></td></tr>
    <tr>
      <td><a href="docs/skills.md#skill-evolver"><code>/skill-evolver</code></a></td>
      <td><code>&lt;skill-name&gt;</code></td>
    </tr>
    <tr><td colspan="2">Evolve an existing larch skill by running <code>/research</code> against repo-local sibling skills and reputable external sources, then delegating any actionable findings to <code>/umbrella</code> (research-and-file-issues only — does not modify the target skill's files).</td></tr>
    <tr><td colspan="2"><hr></td></tr>
    <tr>
      <td><a href="docs/skills.md#umbrella"><code>/umbrella</code></a></td>
      <td><code>[--label L]... [--title-prefix P] [--repo OWNER/REPO] [--closed-window-days N] [--blocked-by-issue N] [--dry-run] [--go] &lt;task description or empty to deduce from context&gt;</code></td>
    </tr>
    <tr><td colspan="2">Plan-to-issues orchestrator: classifies a task description as one-shot or multi-piece, delegates GitHub issue creation to <code>/issue</code> (batch mode plus an umbrella tracking issue when multi-piece), and wires native blocked-by edges plus child→umbrella back-links. <code>--blocked-by-issue N</code> is forwarded to <code>/issue</code> on both Step 3A (one-shot) and Step 3B.2 (batch children); only batch child creation can succeed with the policy edge — single-mode is rejected by <code>/issue</code>'s canonical batch-mode-only error. Typically invoked transitively by <code>/review</code> (description-mode finding filing) and <code>/skill-evolver</code>.</td></tr>
  </tbody>
</table>

See [docs/skills.md](docs/skills.md) for full details on each skill.

## Aliases

Shortcut skills shipped with the plugin. Each alias forwards to an existing skill with preset flags.

| Alias | Equivalent |
|---|---|
| [`/im`](skills/im/SKILL.md) | `/implement --merge` |
| [`/imaq`](skills/imaq/SKILL.md) | `/implement --merge --auto --quick` |
| [`/imq`](skills/imq/SKILL.md) | `/implement --merge --quick` |
