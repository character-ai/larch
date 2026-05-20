# Larch

Larch is a Claude Code workflow automation framework that orchestrates multi-agent design, code review, and implementation through collaborative AI-driven processes.

## Table of Contents

- **Setup**
  - [Installation and Setup](docs/installation-and-setup.md) — plugin install, local development, agent setup recipes (Claude / Codex / Cursor), [clean-main entry contract](docs/installation-and-setup.md#clean-main-entry-contract-for-implement-and-design) for `/implement` and `/design`, what the plugin provides, `/relevant-checks` consumer dependency, prerequisites
- **Reference**
  - [Features](#features)
  - [Skills](#skills)
  - [Aliases](#aliases)
  - [Review Agents](docs/review-agents.md) — the unified `code-reviewer` archetype
  - [Run Logs](docs/run-logs.md) — committed `larch-logs/` batch files, manifest, and tracking-issue comments
  - [Topology Projection](docs/topology.md) — stable anchors for cross-doc topology counts
  - [Linting](docs/linting.md) — linters, Makefile targets, halt-rate regression harness
- **Architecture and workflow**
  - [Workflow Lifecycle](docs/workflow-lifecycle.md) — how skills compose end-to-end
  - [Agent System](docs/agents.md) — parallel subagent orchestration
  - [Collaborative Sketches](docs/collaborative-sketches.md) — the diverge-then-converge design phase
  - [Voting Process](docs/voting-process.md) — the voting panel protocol
  - [Point Competition](docs/point-competition.md) — reviewer scoring system

## Features

- **[Multi-agent design planning, reviews, and adjudication](docs/collaborative-sketches.md)** — the [configured sketch topology](docs/topology.md#design.sketch.regular_slots) diverges, the [dialectic judge panel](docs/topology.md#design.dialectic.judge_panel) resolves contested decisions, and the [validation panel](docs/topology.md#design.plan_review.cursor_archetypes) reviews the final plan.
- **[Voting-based review resolution](docs/voting-process.md)** — The YES/NO/EXONERATE panel protocol adjudicates plan and code review findings.
- **[Reviewer competition scoring](docs/point-competition.md)** — Reviewers earn points based on finding quality; a scoreboard tracks accepted, neutral, exonerated, and rejected findings.
- **[Tracked runs](docs/run-logs.md)** — `/implement` writes full run artifacts to committed `larch-logs/` files and keeps the tracking issue slim with marker-keyed summary comments.

## Skills

<table>
  <thead>
    <tr><th>Name</th><th>Arguments</th></tr>
  </thead>
  <tbody>
    <tr>
      <td><a href="docs/skills.md#alias"><code>/alias</code></a></td>
      <td><code>[--merge] [--private] &lt;alias-name&gt; &lt;target-skill&gt; [preset-flags...]</code></td>
    </tr>
    <tr><td colspan="2">Create an alias for a larch skill with preset flags. Auto-routes to <code>skills/&lt;n&gt;/</code> in plugin source repos and <code>.claude/skills/&lt;n&gt;/</code> elsewhere; <code>--private</code> forces the latter.</td></tr>
    <tr><td colspan="2"><hr></td></tr>
    <tr>
      <td><a href="docs/skills.md#cleanup"><code>/cleanup</code></a></td>
      <td></td>
    </tr>
    <tr><td colspan="2">Remove leftover larch session temp directories from <code>~/.cache/larch/sessions/</code> and <code>/tmp</code>. Aborts when multiple Claude sessions are active; skips dirs with an active <code>.larch-keepalive</code> sentinel.</td></tr>
    <tr><td colspan="2"><hr></td></tr>
    <tr>
      <td><a href="docs/skills.md#block-issue"><code>/block-issue</code></a></td>
      <td><code>&lt;ISSUE_A&gt; &lt;ISSUE_B&gt;</code></td>
    </tr>
    <tr><td colspan="2">Express a native GitHub blocked-by relationship between two issues using the <code>addBlockedBy</code> GraphQL mutation.</td></tr>
    <tr><td colspan="2"><hr></td></tr>
    <tr>
      <td><a href="docs/skills.md#compress-skill"><code>/compress-skill</code></a></td>
      <td><code>&lt;skill-name-or-path&gt;</code></td>
    </tr>
    <tr><td colspan="2">Compress a skill's Markdown prose via a behavior-preserving rewrite.</td></tr>
    <tr><td colspan="2"><hr></td></tr>
    <tr>
      <td><a href="docs/skills.md#create-skill"><code>/create-skill</code></a></td>
      <td><code>[--plugin] [--multi-step] [--merge] &lt;skill-name&gt; &lt;description&gt;</code></td>
    </tr>
    <tr><td colspan="2">Scaffold a new larch-style skill from a name and description.</td></tr>
    <tr><td colspan="2"><hr></td></tr>
    <tr>
      <td><a href="docs/skills.md#design"><code>/design</code></a></td>
      <td><code>[--auto] [--quick] [--full] [--subagent] [--session-env &lt;path&gt;] &lt;feature description&gt;</code></td>
    </tr>
    <tr><td colspan="2">Design an implementation plan with the <a href="docs/topology.md#design.sketch.regular_slots">configured sketch topology</a>, dialectic adjudication, and the <a href="docs/topology.md#design.plan_review.cursor_archetypes">validation panel</a> described in the design workflow. <code>--quick</code> caps sketch fan-out and uses quick plan review; <code>--full</code> forces the full sketch fan-out.</td></tr>
    <tr><td colspan="2"><hr></td></tr>
    <tr>
      <td><a href="docs/skills.md#fix-issue"><code>/fix-issue</code></a></td>
      <td><code>[--auto] [--no-admin-fallback] [--no-logs-commit] [--coder=&lt;value&gt;] [--inline] [--hard] [&lt;number-or-url&gt;]</code></td>
    </tr>
    <tr><td colspan="2">Process one approved GitHub issue per invocation, classifying intent and delegating PR work to <code>/implement</code>.</td></tr>
    <tr><td colspan="2"><hr></td></tr>
    <tr>
      <td><a href="docs/skills.md#implement"><code>/implement</code></a></td>
      <td><code>[--quick] [--auto] [--forked] [--design-only] [--no-issues] [--inline] [--merge | --draft] [--no-admin-fallback] [--no-logs-commit] [--coder=claude|codex|cursor] [--session-env &lt;path&gt;] [--issue &lt;N&gt;] &lt;feature description&gt;</code></td>
    </tr>
    <tr><td colspan="2">End-to-end implementation workflow. In <code>--quick</code> (and SIMPLE auto-switch) paths, Step 5 runs <code>review-and-fix.sh</code> with <code>--panel simple</code>: up to <strong>5 rounds</strong>, a <strong>3-judge panel on round 1</strong> (Claude opus + Codex + Cursor; Claude replacement when an external is unhealthy) and a <strong>2-judge panel on rounds 2+</strong> (Claude + Cursor; Codex voter omitted), and the <strong>simple review panel</strong> (6 Cursor specialists including <strong>Cursor edge-cases</strong>). Use <code>--design-only</code> to publish design artifacts and stop before implementation.</td></tr>
    <tr><td colspan="2"><hr></td></tr>
    <tr>
      <td><a href="docs/skills.md#issue"><code>/issue</code></a></td>
      <td><code>[--input-file FILE] [--title-prefix P] [--label L]... [--body-file F] [--dry-run] [--go] [&lt;issue description&gt;]</code></td>
    </tr>
    <tr><td colspan="2">Create one or more GitHub issues with LLM-based semantic duplicate detection and always-on inter-issue blocker-dependency analysis.</td></tr>
    <tr><td colspan="2"><hr></td></tr>
    <tr>
      <td><a href="docs/skills.md#report-tokens"><code>/report-tokens</code></a></td>
      <td></td>
    </tr>
    <tr><td colspan="2">Analyze structured token reports across closed GitHub issues, estimate per-issue Claude/Codex/Cursor costs, plot SIMPLE and HARD cost trends, and print cost-reduction suggestions.</td></tr>
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
      <td><a href="docs/skills.md#review-and-fix"><code>/review-and-fix</code></a></td>
      <td><code>--findings-file &lt;path&gt; --review-tmpdir &lt;path&gt; [--session-env &lt;path&gt;]</code></td>
    </tr>
    <tr><td colspan="2">Apply accepted review findings as code fixes via Codex/Cursor/Claude-subagent dispatch. Internal sub-skill invoked by <code>/review</code> in diff mode and by <code>/implement</code> Step 5; not a standalone user entry point.</td></tr>
    <tr><td colspan="2"><hr></td></tr>
    <tr>
      <td><a href="docs/skills.md#set-up-forked-open-source-repo"><code>/set-up-forked-open-source-repo</code></a></td>
      <td><code>--upstream &lt;owner/repo&gt; --fork &lt;owner/repo&gt; [--mirror-confirmed] [--init-submodules]</code></td>
    </tr>
    <tr><td colspan="2">Configure the current checkout for upstream/fork OSS contribution: verify the fork, optionally sync it from upstream, rewire remotes, disable upstream pushes, and set <code>main</code> tracking.</td></tr>
    <tr><td colspan="2"><hr></td></tr>
    <tr>
      <td><a href="docs/skills.md#show-skill"><code>/show-skill</code></a></td>
      <td><code>&lt;skill-name&gt;</code></td>
    </tr>
    <tr><td colspan="2">Display the contents of any skill's <code>SKILL.md</code> file. Accepts bare name, <code>larch:</code>-prefixed, or <code>/</code>-prefixed form.</td></tr>
    <tr><td colspan="2"><hr></td></tr>
    <tr>
      <td><a href="docs/skills.md#simplify-skill"><code>/simplify-skill</code></a></td>
      <td><code>&lt;skill-name&gt;</code></td>
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
    <tr><td colspan="2"><hr></td></tr>
    <tr>
      <td><a href="docs/skills.md#upgrade-larch"><code>/upgrade-larch</code></a></td>
      <td><em>(none)</em></td>
    </tr>
    <tr><td colspan="2">Upgrade the larch plugin to the latest version by removing and re-adding the marketplace, then reinstalling the plugin.</td></tr>
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
