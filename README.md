# Larch

Larch is a Claude Code workflow automation framework that orchestrates multi-agent design, code review, and implementation through collaborative AI-driven processes.

## Table of Contents

- **Setup**
  - [Installation and Setup](docs/installation-and-setup.md) — plugin install, local development, agent setup recipes (Claude / Codex / Cursor), [clean-main entry contract](docs/installation-and-setup.md#clean-main-entry-contract-for-implement-and-design) for `/implement` and `/design`, what the plugin provides, the `scripts/relevant-checks.sh` consumer contract, prerequisites
- **Reference**
  - [Features](#features)
  - [Skills](#skills)
  - [Aliases](#aliases)
  - [Review Agents](docs/review-agents.md) — the unified `code-reviewer` archetype
  - [Run Logs](docs/run-logs.md) — committed `larch-logs/` batch files, manifest, and tracking-issue comments
  - [Topology Projection](docs/topology.md) — stable anchors for cross-doc topology counts
  - [Linting](docs/linting.md) — linters, Makefile targets, halt-rate regression harness
  - [Issue-Anchored Plan](docs/issue-anchored-plan.md) — **live** wire format for the /design ↔ /implement plan handoff and clarification round-trip
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
      <td><a href="docs/skills.md#design"><code>/design</code></a></td>
      <td><code>[--trivial|--simple|--hard] [-p|--partition] [--no-dedup] [--run-id &lt;ID&gt;] &lt;issue-N | feature description&gt;</code></td>
    </tr>
    <tr><td colspan="2">Author or refresh an issue-anchored implementation plan in GitHub (plan markers in the issue body). Tier flags select sketch and plan-review depth (<code>--trivial</code> is the quick-budget tier; <code>--simple</code> / <code>--hard</code> use larger sketch fan-outs per <a href="docs/topology.md#design.sketch.regular_slots">topology</a>). <code>-p</code>/<code>--partition</code> is mutually exclusive with <code>--trivial</code> and forces the Step 2b.5 partition prompt path when no hard plan-size threshold trips (see <a href="docs/skills.md#design">docs/skills.md</a>). Finalize runs upstream <code>/larch:issue</code> batch filing for accepted non-security OOS (Step <strong>5b</strong>) before writing and publishing the <code>larch:plan</code> block (<strong>5c</strong>); tmpdir cleanup is Step <strong>6</strong>.</td></tr>
    <tr><td colspan="2"><hr></td></tr>
    <tr>
      <td><a href="docs/skills.md#implement"><code>/implement</code></a></td>
      <td><code>[--merge] [--forked] [--draft] [--no-admin-fallback] [--no-logs-commit] [--coder &lt;claude|codex|cursor&gt;] [--run-id &lt;ID&gt;] &lt;issue-N&gt;</code></td>
    </tr>
    <tr><td colspan="2">End-to-end implementation from the <strong>positional</strong> GitHub <code>&lt;issue-N&gt;</code> after <code>/design</code> has written <code>larch:plan</code> into that issue's body. Step 5 always runs <code>review-and-fix.sh</code> with the unified internal hard panel (no public <code>--panel</code> argv): up to <strong>5 rounds</strong> (base cap 5, plus degraded-round inflation on argv), a <strong>3-judge panel on every round</strong> (Claude opus + Codex + Cursor; Claude replacement when an external is unhealthy), and the <strong>review panel</strong> with <strong>6 Cursor specialists</strong> (plus optional dynamic archetypes). <code>--merge</code> enables CI+merge; <code>--forked</code> is mutually exclusive with <code>--merge</code>. Preflight audit refusal exits <strong>3</strong> (distinct from flag/plan hard errors exit <strong>2</strong>).</td></tr>
    <tr><td colspan="2"><hr></td></tr>
    <tr>
      <td><a href="docs/skills.md#issue"><code>/issue</code></a></td>
      <td><code>[--input-file FILE] [--title-prefix P] [--label L]... [--body-file F] [--dry-run] [&lt;issue description&gt;]</code></td>
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
      <td><a href="docs/skills.md#relevant-checks-script"><code>scripts/relevant-checks.sh</code></a></td>
      <td><em>(none)</em></td>
    </tr>
    <tr><td colspan="2">Consumer-provided validation entrypoint (not a SlashCommand skill). Orchestrators call it through <code>scripts/run-relevant-checks-captured.sh</code>. <strong>Not part of the plugin surface; each consuming repo provides its own executable script.</strong></td></tr>
    <tr><td colspan="2"><hr></td></tr>
    <tr>
      <td><a href="docs/skills.md#research"><code>/research</code></a></td>
      <td><code>[--no-issue] &lt;research question or topic&gt;</code></td>
    </tr>
    <tr><td colspan="2">Collaborative best-effort read-only research with the fixed-shape topology documented in the research skill — planner pre-pass, <a href="docs/topology.md#research.lanes">Codex-first research lanes</a> by angle, and the <a href="docs/topology.md#research.validation_panel">validation panel</a>. Every run includes unconditional citation validation (HEAD-fetches cited URLs under SSRF guards, validates DOIs, spot-checks file:line refs) emitted as a fail-soft PASS / FAIL / UNKNOWN ledger spliced into the final report.</td></tr>
    <tr><td colspan="2"><hr></td></tr>
    <tr>
      <td><a href="docs/skills.md#review"><code>/review</code></a></td>
      <td><code>[--diff] [&lt;description&gt;]</code></td>
    </tr>
    <tr><td colspan="2">Code review with the specialist panel described in <code>docs/review-agents.md</code>. <code>--diff</code>: review branch changes and implement fixes. <code>&lt;description&gt;</code>: review existing code; description mode records voting outcomes and OOS artifacts locally — file follow-up issues with <code>/issue</code> when you want GitHub tracking.</td></tr>
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
| [`/im`](skills/im/SKILL.md) | `/implement --merge` (same public flags as `/implement`; requires positional `<issue-N>`) |
