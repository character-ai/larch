# Larch

Larch is a Claude Code workflow automation framework that orchestrates multi-agent design, code review, and implementation through collaborative AI-driven processes.

> **New to larch?** First [prepare your repository](docs/preparing-your-repo.md) for agent-assisted development, then follow the flow below.

## Primary Flow

1. Create issue  describing the task/problem with `/issue` or `/bug` or manually
2. Design it with `/design` (detailed reviewed design gets stored in tracking issue)
3. Implement it with `/implement`

## Support Skills

- Manage issues and their dependencies: `/issue`, `/bug`, `/combine-issues`, `/block-issue`, `/deps`
- Various analysis tools: `/report-tokens`, `/fluff-analysis`, `/difficulty-calibration`, `/rejected-analysis`, `/analyze-issues`, `/audit-runs`
- `larch` management: `/status`, `/upgrade-larch`, `/larch-size`

## Table of Contents

- **Setup**
  - [Installation and Setup](docs/installation-and-setup.md) — prerequisites, auth (API keys or web login) for Claude / Codex / Cursor, plugin install and permissions, `/status` validation, `/upgrade-larch`
  - [Preparing Your Repository](docs/preparing-your-repo.md). Ready your repo for larch and agent-assisted development: instruction files (`CLAUDE.md`/`AGENTS.md`), guardrails (guidelines, hooks, linters), and the `checks run-relevant` contract
  - [Contributing](docs/contributing.md) — local dev plugin install, plugin cache vs. working-tree version, Mermaid CLI setup
  - [Clean-Main Entry Contract](docs/clean-main-contract.md) — the `/implement` and `/design` clean `main` entry preconditions, plus `/implement` feature-branch continuation
  - [Fork CI Dry-Runs](docs/forked.md) — remote setup for `/implement --forked`
  - [macOS Keychain Interactions](docs/macos-keychain-interactions.md) — Cursor `CURSOR_API_KEY` and keychain auth troubleshooting
  - [Optional Helpers](docs/optional-helpers.md) — installing optional tools like ast-grep
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
  - [Design Flow](docs/collaborative-sketches.md) — direct plan drafting and plan review
  - [Voting Process](docs/voting-process.md) — the voting panel protocol
  - [Point Competition](docs/point-competition.md) — reviewer scoring system

## Features

- **[Direct design planning and plan reviews](docs/collaborative-sketches.md)** — Step 2b drafts the plan directly, then the [validation panel](docs/topology.md#design.plan_review.cursor_archetypes) reviews it.
- **[Voting-based review resolution](docs/voting-process.md)** — The YES/NO panel protocol adjudicates plan and code review findings.
- **[Reviewer competition scoring](docs/point-competition.md)** — Reviewers earn points based on finding quality; a scoreboard tracks accepted, neutral, and rejected findings.
- **[Tracked runs](docs/run-logs.md)** — `/implement` writes full run artifacts to committed `larch-logs/` files and keeps the tracking issue slim with marker-keyed summary comments.
- **[Progress statusline](docs/progress-reporting.md)** — clone-local breadcrumbs show live larch progress without adding report text to model context.
- **Tiered architectural knowledge** — Optional `ARCHITECTURAL_INVARIANTS.md` and `ARCHITECTURAL_GUIDELINES.md` files are supplied to coders and reviewers as untrusted, scope-bound evidence.

## Skills

larch ships **public skills** with the plugin (`skills/`); **private** skills live under `.claude/skills/` and are dev-only (not exported). Both are listed below; shortcut **aliases** are in the [Aliases](#aliases) section. See [docs/skills.md](docs/skills.md) for full per-skill detail.

### Public skills

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
      <td><a href="docs/skills.md#block-issue"><code>/block-issue</code></a></td>
      <td><code>&lt;ISSUE_A&gt; &lt;ISSUE_B&gt; [--repo owner/name]</code></td>
    </tr>
    <tr><td colspan="2">Express a native GitHub blocked-by relationship between two issues using the <code>addBlockedBy</code> GraphQL mutation. Repo auto-detected when <code>--repo</code> is omitted.</td></tr>
    <tr><td colspan="2"><hr></td></tr>
    <tr>
      <td><a href="docs/skills.md#bug"><code>/bug</code></a></td>
      <td><code>[--urgent] &lt;bug description&gt;</code></td>
    </tr>
    <tr><td colspan="2">Investigate a user-described bug read-only, compose a detailed issue body, then file it via <code>/issue</code> with dedup enabled. <code>--urgent</code> changes the title prefix. Aborts to <code>SECURITY.md</code> disclosure if the report looks security-sensitive; never edits the repo.</td></tr>
    <tr><td colspan="2"><hr></td></tr>
    <tr>
      <td><a href="docs/skills.md#cleanup"><code>/cleanup</code></a></td>
      <td><code>[--run-id &lt;ID&gt;]</code></td>
    </tr>
    <tr><td colspan="2">Remove stale larch session temp directories from <code>~/.cache/larch/sessions/</code>, <code>/tmp</code>, and the OS temp root <code>$TMPDIR</code> resolves to (a per-user path distinct from <code>/tmp</code> on macOS) by bounded nested-activity scan (<code>LARCH_CLEANUP_RETENTION_DAYS</code>, default 7): a directory is deleted only when the <code>find -maxdepth 5</code> nested scan finds no file newer than the cutoff, so a directory with fresh deep activity is retained even when its top-level mtime is stale. Reaps dangling <code>current-design-env-*.sh</code> symlinks. Always runnable regardless of concurrent Claude sessions.</td></tr>
    <tr><td colspan="2"><hr></td></tr>
    <tr>
      <td><a href="docs/skills.md#deps"><code>/deps</code></a></td>
      <td><code>[--repo owner/name] [--pair-cap N]</code></td>
    </tr>
    <tr><td colspan="2">Audit open issues by in-flight title prefix, conservatively refresh mutable REGULAR bodies, propose stale REGULAR closes, and infer dependencies with an explicit-ref scan plus latent semantic pass. Mutates only after <code>AskUserQuestion</code> approval. Dependency writes use <code>/block-issue</code>. <code>--pair-cap</code> is explicit partial-audit mode.</td></tr>
    <tr><td colspan="2"><hr></td></tr>
    <tr>
      <td><a href="docs/skills.md#design"><code>/design</code></a></td>
      <td><code>[-p|--partition] [--brainstorm] [--per-round-approval] [--skip-approve|-s] [--no-dedup] [--run-id &lt;ID&gt;] [--difficulty &lt;TRIVIAL|MODERATE|HARD&gt;] &lt;issue-N | feature description&gt;</code></td>
    </tr>
    <tr><td colspan="2">Author or refresh an issue-anchored implementation plan in GitHub (plan markers in the issue body). <code>-p</code>/<code>--partition</code> routes Step 2b.5 directly to the decomposition panel when no plan-size threshold trips; size triggers show the <code>Override</code>/<code>Cancel</code> prompt. Optional <code>--brainstorm</code> runs Step 1d.5 ideation before the Step 1d.7 outline-approval gate (Gate A re-entry only post-plan) (see <a href="docs/skills.md#design">docs/skills.md</a>). Gate B auto-applies accepted findings by default; <code>--per-round-approval</code> restores the explicit per-round apply prompt. <code>--skip-approve</code>/<code>-s</code> auto-approves the Step 1d.7 outline and Gate C final plan without an <code>AskUserQuestion</code> (no other prompts are skipped). The old <code>--approve</code> and <code>--hard</code> flags are rejected; use <code>--per-round-approval</code> for explicit Gate B prompts. Finalize runs upstream <code>/larch:issue</code> batch filing for accepted non-security OOS (Step <strong>5b</strong>) before writing and publishing the <code>larch:plan</code> block (<strong>5c</strong>); tmpdir cleanup is Step <strong>6</strong>.</td></tr>
    <tr><td colspan="2"><hr></td></tr>
    <tr>
      <td><a href="docs/skills.md#difficulty-calibration"><code>/difficulty-calibration</code></a></td>
      <td><code>[--log-root DIR] [--out FILE]</code></td>
    </tr>
    <tr><td colspan="2">Compare predicted and realized difficulty tiers from committed run logs. Diagnostic only; changes no thresholds, panels, tokens, routing, or reviewer points.</td></tr>
    <tr><td colspan="2"><hr></td></tr>
    <tr>
      <td><a href="docs/skills.md#fluff-analysis"><code>/fluff-analysis</code></a></td>
      <td><code>[--include-in-progress] [--cutoff ISO8601] [--since-version X.Y.Z] [--min-group N] [--log-root DIR] [--out FILE]</code></td>
    </tr>
    <tr><td colspan="2">Characterize review <strong>fluff</strong> from committed larch run logs — which <code>/design</code> and <code>/implement</code> review suggestions get rejected, deferred to OOS, or accepted-but-low-value — by acceptance baselines, low-acceptance semantic groups, severity cuts, and reviewer-lane splits, then print data-driven recommendations for tightening the reviewer self-filter and judge (voter) instructions.</td></tr>
    <tr><td colspan="2"><hr></td></tr>
    <tr>
      <td><a href="docs/skills.md#gc-run-logs"><code>/gc-run-logs</code></a></td>
      <td><code>[--older-than DAYS] [--delete] [--dry-run]</code></td>
    </tr>
    <tr><td colspan="2">Age-based retention policy for committed <code>larch-logs/</code> run directories. Slims qualifying dirs (default: older than 90 days) to the consumer-core keep set (token/timing reports, findings, manifest); <code>--delete</code> fully removes them. Creates a log-only PR for operator merge. Operator-invoked only — never runs implicitly.</td></tr>
    <tr><td colspan="2"><hr></td></tr>
    <tr>
      <td><a href="docs/skills.md#implement"><code>/implement</code></a></td>
      <td><code>[--merge] [--forked] [--draft] [--no-admin-fallback] [--no-logs-commit] [--coder &lt;claude|codex|cursor&gt;] [--run-id &lt;ID&gt;] [--force|-f] [--self-review] [--self-implement] [--difficulty &lt;TRIVIAL|MODERATE|HARD&gt;] &lt;issue-N&gt;</code></td>
    </tr>
    <tr><td colspan="2">End-to-end implementation from the <strong>positional</strong> GitHub <code>&lt;issue-N&gt;</code> after <code>/design</code> has written <code>larch:plan</code> into that issue's body. Step 5 always runs <code>review-and-fix CLI</code> with the internal review panel (no public <code>--panel</code> argv): hard ceiling of <strong>2</strong> for every tier, TRIVIAL singles, MODERATE pairs, HARD pairs with the Codex default role, pruning on round-1 productivity for round 2, <strong>specialists per vendor</strong> plus at most one dynamic archetype pair, and an additive Cursor/<code>auto</code> plan-fidelity reviewer on every tier. Reviewer dispatch uses <code>--no-fallback</code>, so missing vendors drop rows instead of cross-vendor or Claude reviewer backfill. <code>--merge</code> enables CI+merge; <code>--forked</code> is mutually exclusive with <code>--merge</code>. Use <code>--force</code> (or <code>-f</code>) to skip the item 4 plan-adequacy audit and downgrade only the documented force Preflight gates to warn-and-proceed (default off; does not affect coder selection). <code>--self-review</code> skips the external panel for a thorough inline self-review at Step 5. <code>--self-implement</code> forces <code>coder=claude</code>, independent of <code>--force</code> (default off). Preflight audit refusal exits <strong>3</strong> (distinct from flag/plan hard errors exit <strong>2</strong>).</td></tr>
    <tr><td colspan="2"><hr></td></tr>
    <tr>
      <td><a href="docs/skills.md#issue"><code>/issue</code></a></td>
      <td><code>[--input-file FILE] [--intra-batch-deps-file FILE] [--blocked-by-issue N] [--title-prefix PREFIX] [--label LABEL]... [--body-file FILE] [--dry-run] [--no-dedup] [--no-dep-llm] [--sentinel-file PATH] [&lt;issue description or title&gt;]</code></td>
    </tr>
    <tr><td colspan="2">Create one or more GitHub issues with LLM-based semantic duplicate detection and always-on inter-issue blocker-dependency analysis. <code>--no-dedup</code> skips both passes; <code>--no-dep-llm</code> keeps dedup but skips the LLM dependency pass. Batch/wiring flags (<code>--input-file</code>, <code>--body-file</code>, <code>--blocked-by-issue</code>, <code>--intra-batch-deps-file</code>, <code>--sentinel-file</code>) are used mainly by calling skills.</td></tr>
    <tr><td colspan="2"><hr></td></tr>
    <tr>
      <td><a href="docs/skills.md#learn-from-bugs"><code>/learn-from-bugs</code></a></td>
      <td><code>[-n COUNT] [--state closed|open|all] [--repo OWNER/REPO] [--search QUERY] [verbal description]</code></td>
    </tr>
    <tr><td colspan="2">Mine a repository's closed bug reports for recurring root-cause patterns, then propose preventions ranked by mechanical enforceability: lint rules, architectural invariants, guideline entries, and issues to file for still-broken code. Report-only by default: it compresses each body to a compact root-cause digest, maps every recurring principle to the repo's existing coverage (guidelines, invariants, hooks, and lints) before proposing the residual gap, and runs the synthesis inline with no sub-agent fan-out. Repository and GitHub changes are gated behind explicit approval; filing goes through <code>/issue</code>.</td></tr>
    <tr><td colspan="2"><hr></td></tr>
    <tr>
      <td><a href="docs/skills.md#pause"><code>/pause</code></a></td>
      <td></td>
    </tr>
    <tr><td colspan="2">Pause a running <code>/design</code>; saves state to GitHub for cross-session resume. Source: <a href="skills/pause/SKILL.md"><code>skills/pause/SKILL.md</code></a>.</td></tr>
    <tr><td colspan="2"><hr></td></tr>
    <tr>
      <td><a href="docs/skills.md#rejected-analysis"><code>/rejected-analysis</code></a></td>
      <td><code>--n DAYS</code></td>
    </tr>
    <tr><td colspan="2">Recover verified real rejected code-review findings from committed run logs and file issues by default. Security-sensitive findings are not public-filed, OOS-deferred findings are excluded, and the stable <code>finding_hash</code> uses file plus concern only, excluding run metadata and filesystem state.</td></tr>
    <tr><td colspan="2"><hr></td></tr>
    <tr>
      <td><a href="docs/skills.md#report-tokens"><code>/report-tokens</code></a></td>
      <td><code>--skill &lt;design|implement&gt; [--no-issue] [--no-plot] [--run-id &lt;ID&gt;]</code></td>
    </tr>
    <tr><td colspan="2">Analyze structured token reports from committed larch run logs, price Claude/Codex/Cursor runs through `python/larch/report/report_tokens_cost.py`, plot skill-aware trends, and print cost-reduction suggestions.</td></tr>
    <tr><td colspan="2"><hr></td></tr>
    <tr>
      <td><a href="docs/skills.md#research"><code>/research</code></a></td>
      <td><code>[--no-issue] &lt;research question or topic&gt;</code></td>
    </tr>
    <tr><td colspan="2">Collaborative best-effort read-only research with the fixed-shape topology documented in the research skill — planner pre-pass, <a href="docs/topology.md#research.lanes">Codex-first research lanes</a> by angle, and the <a href="docs/topology.md#research.validation_panel">validation panel</a>. Every run includes unconditional citation validation (HEAD-fetches cited URLs under SSRF guards, validates DOIs, spot-checks file:line refs) emitted as a fail-soft PASS / FAIL / UNKNOWN ledger spliced into the final report.</td></tr>
    <tr><td colspan="2"><hr></td></tr>
    <tr>
      <td><a href="docs/skills.md#review"><code>/review</code></a></td>
      <td><code>[--diff] [--subagent] [--dynamic-archetypes &lt;N&gt;] [--session-env &lt;path&gt;] [--step-prefix &lt;prefix&gt;] [--difficulty &lt;TRIVIAL|MODERATE|HARD&gt;] [&lt;description&gt;]</code></td>
    </tr>
    <tr><td colspan="2">Code review with the specialist panel described in <code>docs/review-agents.md</code>. <code>--diff</code>: review branch changes and implement fixes. <code>&lt;description&gt;</code>: review existing code; description mode records voting outcomes and OOS artifacts locally — file follow-up issues with <code>/issue</code> when you want GitHub tracking. <code>--subagent</code>, <code>--dynamic-archetypes</code>, <code>--difficulty</code>, <code>--session-env</code>, and <code>--step-prefix</code> are used mainly by <code>/implement</code> Step 5.</td></tr>
    <tr><td colspan="2"><hr></td></tr>
    <tr>
      <td><a href="docs/skills.md#review-and-fix"><code>/review-and-fix</code></a></td>
      <td><code>--findings-file &lt;path&gt; [--session-env &lt;path&gt;] [--review-tmpdir &lt;path&gt;]</code></td>
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
      <td><a href="docs/skills.md#status"><code>/status</code></a></td>
      <td><em>(none)</em></td>
    </tr>
    <tr><td colspan="2">Print the current larch version and health status of external vendor tools (Codex and Cursor), using the same probe machinery as <code>/implement</code>.</td></tr>
    <tr><td colspan="2"><hr></td></tr>
    <tr>
      <td><a href="docs/skills.md#upgrade-larch"><code>/upgrade-larch</code></a></td>
      <td><code>[--run-id &lt;ID&gt;]</code></td>
    </tr>
    <tr><td colspan="2">Upgrade the larch plugin to the latest version by refreshing the sparse marketplace checkout in place when possible, repairing legacy clones when needed, then reinstalling the plugin.</td></tr>
    <tr><td colspan="2"><hr></td></tr>
    <tr>
      <td><a href="docs/skills.md#voter-calibration"><code>/voter-calibration</code></a></td>
      <td><code>[--log-root DIR] [--min-votes N] [--outlier-threshold R] [--high-severity-threshold R] [--out FILE]</code></td>
    </tr>
    <tr><td colspan="2">Measure voter agreement and chronic outlier voters from committed larch run logs. Diagnostic only; does not affect spawning, thresholds, tokens, or reviewer points.</td></tr>
  </tbody>
</table>

### Private skills

Dev-only: not shipped with the plugin; runnable only inside the larch source tree.

<table>
  <thead>
    <tr><th>Name</th><th>Arguments</th></tr>
  </thead>
  <tbody>
    <tr>
      <td><a href="docs/skills.md#agnix-fix"><code>/agnix-fix</code></a></td>
      <td><code>&lt;upstream-issue-number&gt; [extra-flags...]</code></td>
    </tr>
    <tr><td colspan="2">Fix an open <code>agent-sh/agnix</code> issue end-to-end via fork-CI dry-run: fetch the upstream issue body, provision the <code>skip-changelog</code> label on the fork, then forward to <code>/implement --forked</code> with the positional upstream issue number.</td></tr>
    <tr><td colspan="2"><hr></td></tr>
    <tr>
      <td><a href="docs/skills.md#analyze-bugs"><code>/analyze-bugs</code></a></td>
      <td><code>[-n COUNT] [--deep-max M] [--deep-model sonnet|opus|fable] [--refresh] [--sample K] [--repo owner/name]</code></td>
    </tr>
    <tr><td colspan="2">Dev-only cached audit for recent <code>[BUG]</code> issues. Defaults to <code>-n 200</code>, stores its local ledger under <code>~/.cache/larch/analyze-bugs/</code>, prints a report by default, and offers one combined follow-up issue only after approval.</td></tr>
    <tr><td colspan="2"><hr></td></tr>
    <tr>
      <td><a href="docs/skills.md#analyze-issues"><code>/analyze-issues</code></a></td>
      <td><code>[--limit N] [--span-days N] [--top-K N] [--categories=auto|default] [--log-root PATH] [--repo OWNER/REPO] [--lenient] [--ground-truth-verdict] [--since-date DATE] [--min-runs N] [--min-larch-version VERSION]</code></td>
    </tr>
    <tr><td colspan="2">Generate a backlog-and-process insight report from a repo's GitHub issues. Verdict mode skips the full backlog report, emits a filtered corpus block with explicit gate PASS/FAIL, and gates token allocation on a post-<code>52.1.0</code>, post-<code>2026-06-26</code>, incentivized-era realized-outcome corpus with strict <code>started_at</code> eligibility and a mechanical #5461 shipped check: closed with <code>closedByPullRequestsReferences</code>, not <code>NOT_PLANNED</code>.</td></tr>
    <tr><td colspan="2"><hr></td></tr>
    <tr>
      <td><a href="docs/skills.md#audit-runs"><code>/audit-runs</code></a></td>
      <td><code>--skill &lt;design|implement&gt; [&lt;verbal-description&gt;] [--repo owner/name] [--allow-concurrent]</code></td>
    </tr>
    <tr><td colspan="2">Audit recently-merged larch run logs for anomalies, file the chain-of-history audit-report issue, and propose bug-issue follow-ups that require explicit user direction before any filing.</td></tr>
    <tr><td colspan="2"><hr></td></tr>
    <tr>
      <td><a href="docs/skills.md#combine-issues"><code>/combine-issues</code></a></td>
      <td><code>[--oos]</code></td>
    </tr>
    <tr><td colspan="2">Combine related open issues into fewer broader ones (closing the sources) to reduce token spend. <code>--oos</code> operates only on <code>[OOS]</code>-prefixed issues, discards stale items, and proposes an aggressive combination scheme.</td></tr>
    <tr><td colspan="2"><hr></td></tr>
    <tr>
      <td><a href="docs/skills.md#larch-size"><code>/larch-size</code></a></td>
      <td><em>(none)</em></td>
    </tr>
    <tr><td colspan="2">Report larch repository line counts (Bash, Python, Markdown) and <code>larch-logs</code> size breakdowns. Takes no flags.</td></tr>
    <tr><td colspan="2"><hr></td></tr>
    <tr>
      <td><a href="docs/skills.md#rebalance-tests"><code>/rebalance-tests</code></a></td>
      <td><code>[--kind {harness,python,all}] [--repo owner/name] [--n-runs N] [--branch-prefix PREFIX] [--n-python-shards N]</code></td>
    </tr>
    <tr><td colspan="2">Rebalance CI test harness shards, Python unit-test shards, or both from recent CI timings; create one PR and trigger verification CI. Harness verification is warning-only; Python timing verification fails closed.</td></tr>
    <tr><td colspan="2"><hr></td></tr>
    <tr>
      <td><a href="docs/skills.md#release"><code>/release</code></a></td>
      <td><code>[--dry-run] [--skip-approve|-s] [--bump major|minor|patch] [--repo OWNER/REPO]</code></td>
    </tr>
    <tr><td colspan="2">Operator-run release cut (model cannot auto-invoke): gather merged PRs since the last Latest release, generate notes, decide the semver bump, open and merge the <code>plugin.json</code> bump PR, tag and create the GitHub Release, promote to Latest, then run <code>/upgrade-larch</code>.</td></tr>
  </tbody>
</table>

### Non-skill entrypoints

<table>
  <thead>
    <tr><th>Name</th><th>Arguments</th></tr>
  </thead>
  <tbody>
    <tr>
      <td><a href="docs/skills.md#relevant-checks-script"><code>python/cli.py checks run-relevant</code></a></td>
      <td><code>--site &lt;site&gt; [--tmpdir DIR] [--repo-root DIR] [--allow-skip]</code></td>
    </tr>
    <tr><td colspan="2">Consumer-provided validation entrypoint (not a SlashCommand skill). Orchestrators call it through <code>python/cli.py checks run-relevant --site &lt;site&gt; --tmpdir &lt;tmpdir&gt;</code>. <strong>Not part of the plugin surface; each consuming repo provides its own executable script.</strong></td></tr>
  </tbody>
</table>

See [docs/skills.md](docs/skills.md) for full details on each skill.

## Aliases

Shortcut skills shipped with the plugin. Each alias forwards to an existing skill with preset flags.

| Alias | Equivalent |
|---|---|
| [`/im`](docs/skills.md#im) | `/implement --merge` (same public flags as `/implement`; requires positional `<issue-N>`) |
