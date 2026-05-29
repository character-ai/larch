# Skills

Reference for every slash command shipped by the larch plugin. Each section below covers one skill: invocation, arguments, behavior, and links to the canonical `SKILL.md` source.

- [`/alias`](#alias)
- [`/cleanup`](#cleanup)
- [`/design`](#design)
- [`/implement`](#implement)
- [`/issue`](#issue)
- [`/pause`](#pause)
- [`/report-tokens`](#report-tokens)
- [`scripts/relevant-checks.sh`](#relevant-checks-script)
- [`/research`](#research)
- [`/review`](#review)
- [`/review-and-fix`](#review-and-fix)
- [`/set-up-forked-open-source-repo`](#set-up-forked-open-source-repo)
- [`/upgrade-larch`](#upgrade-larch)

## `/alias`

**Arguments**: `[--merge] [--private] <alias-name> <target-skill> [preset-flags...]`

**Source**: [`skills/alias/SKILL.md`](../skills/alias/SKILL.md)

Create an alias for a larch skill with preset flags. Delegates to `/implement` for the full pipeline per `skills/alias/SKILL.md` (code review, version bump, PR). `--merge` also merges the PR.

**Target directory** is auto-resolved: inside a Claude plugin source repo (detected by the two-file predicate `.claude-plugin/plugin.json` AND `skills/implement/SKILL.md` at the git repo root), the alias is generated under `skills/<alias-name>/SKILL.md` (exported plugin skill, ships with the plugin); anywhere else, it's generated under `.claude/skills/<alias-name>/SKILL.md` (dev-only repo-private). `--private` forces `.claude/skills/<alias-name>/` even inside a plugin repo (escape hatch); in non-plugin repos it's a no-op.

Example (in a plugin repo): `/alias i implement --merge` creates `<repo-root>/skills/i/SKILL.md` so that `/i <issue-N>` forwards to `/implement --merge <issue-N>` with any additional preset flags captured in the alias body.

Example with `--private` or in a consumer repo: `/alias i implement --merge` creates `<repo-root>/.claude/skills/i/SKILL.md` (dev-only).

## `/block-issue`

**Arguments**: `<ISSUE_A> <ISSUE_B> [--repo owner/name]`

**Source**: [`skills/block-issue/SKILL.md`](../skills/block-issue/SKILL.md)

Express a native GitHub blocked-by relationship between two issues using the `addBlockedBy` GraphQL mutation. ISSUE_A is marked as blocked by ISSUE_B. Repo is auto-detected from `gh repo view` when `--repo` is omitted. Verifies the relationship was recorded before confirming.

## `/cleanup`

**Arguments**: *(none)*

**Source**: [`skills/cleanup/SKILL.md`](../skills/cleanup/SKILL.md)

Remove stale larch session temp directories from `~/.cache/larch/sessions/` and `/tmp` by age (`LARCH_CLEANUP_RETENTION_DAYS`, default 7). Activity is measured through depth 5 under each entry. Reaps dangling `current-design-env-*.sh` symlinks. Always runnable — reports `SESSION_COUNT` for visibility but does not abort when multiple Claude sessions are active.

## `/design`

**Arguments**: `[--hard] [-p|--partition] [--brainstorm] [--manual|-m] [--no-dedup] [--run-id <ID>] <issue-N | feature description>`

**Source**: [`skills/design/SKILL.md`](../skills/design/SKILL.md) · [Diagram](../skills/design/diagram.svg)

Design an implementation plan with collaborative multi-reviewer review. The [sketch topology](topology.md#design.sketch.regular_slots) documented in [Collaborative Sketches](collaborative-sketches.md) independently proposes architectural approaches when the router assigns a non-zero sketch budget, then the dialectic debate and [judge panel](topology.md#design.dialectic.judge_panel) described in `skills/shared/dialectic-protocol.md` resolves contested decisions. The [validation panel](topology.md#design.plan_review.cursor_archetypes) documented in [Review Agents](review-agents.md) then reviews the full plan. The default tier is SIMPLE; `--hard` selects HARD (sketch + plan-review depth); `-p` / `--partition` requests the Step 2b.5 partition / break-up flow when no hard plan-size threshold trips; optional `--brainstorm` runs Step 1d.5 ideation before the Step 1d.7 outline-approval gate (Gate A re-entry only post-plan); `--manual` / `-m` restores per-iteration Gate B prompts, while the default auto-applies accepted findings — see `skills/design/references/flags.md`. Internal-only flags also live there. After final approval, **Step 5b** may file accepted non-security OOS items via `/larch:issue` (`[OOS]` prefix) before **Step 5c** writes the `larch:plan` block to the issue; **Step 6** removes the design tmpdir.

## `/pause`

**Arguments**: *(none)*

**Source**: [`skills/pause/SKILL.md`](../skills/pause/SKILL.md)

Pause a live `/design` session on the current Claude PID. The skill sources the
current design session env, publishes the tmpdir with
`design-log-publish.sh --reason pause`, writes a `larch:design-pause` marker in
the issue body, and exits. Re-running `/design <issue>` detects that marker in
Step 0b, restores the tmpdir, deletes the marker, and resumes at the first
incomplete step. If no live `/design` env is present, it reports that there is
nothing to pause and exits successfully.

## `/implement`

**Arguments**: `[--merge] [--forked] [--draft] [--no-admin-fallback] [--no-logs-commit] [--coder <claude|codex|cursor>] [--run-id <ID>] <issue-N>`

**Source**: [`skills/implement/SKILL.md`](../skills/implement/SKILL.md) · [Diagram](../skills/implement/diagram.svg)

Full implementation workflow spanning design through PR merge. Preflight consumes the **positional** GitHub `<issue-N>` after `/design` has written `larch:plan` into that issue's body. Step 5 invokes `run-step5-review.sh`, which derives `effective_round_cap` from base cap **5** plus degraded-round inflation, does **not** forward `--panel` on the public argv, and applies the panel only inside `review-and-fix.sh` → `review-core.sh`: a **3-judge panel on every round** (Claude opus + Codex + Cursor; Claude replacement when an external is unhealthy), with the **review panel** and **6 Cursor specialists** (plus optional dynamic archetypes). `--merge` enables CI+merge; `--forked` is mutually exclusive with `--merge`. `--emergency` bypasses plan-block presence / plan-adequacy audit / clarify-state pending gates with loud warnings; default is off.

## `/issue`

**Arguments**: `[--input-file FILE] [--title-prefix P] [--label L]... [--body-file F] [--dry-run] [--no-dedup] [<issue description>]`

**Source**: [`skills/issue/SKILL.md`](../skills/issue/SKILL.md)

Create one or more GitHub issues with LLM-based semantic duplicate detection. Supports single mode (free-form description) and batch mode (`--input-file`). 2-phase dedup against open + recently-closed issues (default 90-day window). `--no-dedup` skips the entire dedup + dependency analysis pipeline and creates all items directly — useful for archival issues (e.g., `/research` reports) where each run produces genuinely different content. `/design` Step 5b and `/implement` Step 9a.1 call this skill in batch mode to file OOS issues.

**Default-on inter-issue blocker-dependency analysis** (issue #546): unless `--no-dedup` is set, every invocation analyzes the new item(s) against existing OPEN issues and applies hard GitHub-native blocker dependencies via the Issue Dependencies REST API on detected pairs (merge-conflict risk or "must land first"). Hard-fail with retries (3 tries, 10s/30s sleeps); on retry exhaustion the failed item is rolled back (orphan close) — when multiple items are processed, unrelated items continue — and the run exits non-zero if any item failed, yielding a clean "create-then-close" recovery rather than a dangling issue with missing dependency wiring.

## `/report-tokens`

**Arguments**: *(none)*

**Source**: [`skills/report-tokens/SKILL.md`](../skills/report-tokens/SKILL.md)

Analyze structured token reports across closed GitHub issues in the current larch repository. The skill searches closed issues whose comments contain `token-report-begin`, fetches their bodies and comments via `gh`, writes a raw JSON cache under a temp directory, parses Claude/Codex/Cursor grand-total rows, estimates per-issue costs, classifies issues from `**Workflow path**`, generates SIMPLE and HARD cost-over-time PNGs, and prints a written analysis with top SIMPLE costs, HARD phase breakdown, cache-read dominance, and concrete cost-reduction suggestions. Dollar values are observability estimates, not billing truth; rates are printed and can be overridden with environment variables.

## Relevant checks script

**Path**: `scripts/relevant-checks.sh`

**Arguments**: *(none — invoked as a Bash script, not a SlashCommand skill)*

**Source**: consumer repo file at `scripts/relevant-checks.sh` (larch ships a reference implementation in-tree for this repository).

Run pre-commit linters (shellcheck, markdownlint, jsonlint, actionlint, gitleaks) scoped to changed files (except gitleaks, which always scans the full working tree; see `.pre-commit-config.yaml` `pass_filenames: false` hooks). Human operators run it directly with `bash scripts/relevant-checks.sh`. `/implement` and `/review` use `scripts/run-relevant-checks-captured.sh` to call the same project-local script without spending Skill-tool tokens on the green path; when the script is absent, the helper emits `RELEVANT_CHECKS_SKIPPED=true` (exit 0) so the skip is machine-observable. **Not part of the plugin SlashCommand surface; each consuming repo provides its own copy.**

## `/research`

**Arguments**: `[--no-issue] <research question or topic>`

**Source**: [`skills/research/SKILL.md`](../skills/research/SKILL.md) · [Diagram](../skills/research/diagram.svg)

Collaborative best-effort read-only research with a fixed-shape topology. The research phase always runs a planner pre-pass that decomposes `RESEARCH_QUESTION` into focused subquestions, then the [Codex-first lanes](topology.md#research.lanes) listed in the research skill (architecture / edge cases / external comparisons / security) with a per-lane Claude `Agent` fallback when Codex is unavailable. The validation phase runs the [panel](topology.md#research.validation_panel) described in [Review Agents](review-agents.md), with Claude fallbacks when an external tool is unavailable. Cursor is NOT used in research lanes (it remains a validation reviewer).

**Step 2.5 — Citation Validation (unconditional)**: between Step 2 (validation) and Step 2.6 (critique loop) the deterministic shell validator `skills/research/scripts/validate-citations.sh` extracts cited URLs / DOIs / `file:line` references from the synthesis, HEAD-fetches URLs under SSRF guards (HTTPS-only, `--max-redirs 0`, `--noproxy '*'`, RFC1918/IPv6 link-local/RFC6598 hostname pre-rejection, DNS resolved-IP private-range check, connection-pinning via `--resolve` to mitigate rebinding TOCTOU), validates DOIs syntactically + via `doi.org` HEAD, and spot-checks `file:line` ranges against the git tree (with `realpath` containment). Output is a 3-state ledger (PASS / FAIL / UNKNOWN with reason classifier) sidecar at `$RESEARCH_TMPDIR/citation-validation.md` that Step 3 splices as a `## Citation Validation` section into `research-report-final.md`. Fail-soft: per-claim failures surface as advisory warnings only; the validator always exits 0; Step 3 is never blocked.

The run produces a structured report with findings, risk assessment, difficulty estimates, and feasibility verdict.

**Token telemetry**: Step 4 always renders a `## Token Spend` section before tmpdir cleanup, summarizing per-phase Claude subagent tokens. Telemetry is observability-only — there is no budget enforcement. Claude inline (orchestrator) and external lanes (Cursor/Codex) are unmeasurable and excluded from the totals. When env var `LARCH_TOKEN_RATE_PER_M` is set (USD per million tokens), the report includes a `$` cost column. See [`scripts/token-tally.md`](../scripts/token-tally.md) for the helper contract. Tracked repo files are not modified by the Claude `Edit | Write | NotebookEdit` tool surface — scratch writes are permitted only under canonical `/tmp` (enforced mechanically by the skill-scoped `scripts/deny-edit-write.sh` PreToolUse hook). Step 3.5 auto-archives the full report as a GitHub issue on each successful run (via `/issue` single mode); `--no-issue` skips this step. `/issue` may also be invoked when the research brief calls for filing findings as issues.

## `/review`

**Arguments**: `[--diff] [<description>]`

**Source**: [`skills/review/SKILL.md`](../skills/review/SKILL.md) · [Diagram](../skills/review/diagram.svg)

Code review with the specialist panel described in [Review Agents](review-agents.md). Supports `--diff`, which reviews branch changes vs main and implements accepted suggestions in a recursive loop, and positional `<description>`, which reviews existing code. Description mode records voting outcomes and OOS artifacts locally; file follow-up GitHub issues with `/issue` when you want tracking.

## `/review-and-fix`

**Arguments**: `--findings-file <path> --review-tmpdir <path> [--session-env <path>]`

**Source**: [`skills/review-and-fix/SKILL.md`](../skills/review-and-fix/SKILL.md)

Apply accepted review findings as code fixes. Internal sub-skill invoked by `/review` in diff mode and by `/implement` Step 5; not a standalone user entry point. It dispatches Codex, Cursor, then a Claude subagent fallback to apply voted-in suggestions directly, with pre-dispatch submodule finding scrubbing and post-dispatch submodule revert checks.

## `/set-up-forked-open-source-repo`

**Arguments**: `--upstream <owner/repo> --fork <owner/repo> [--mirror-confirmed] [--init-submodules]`

**Source**: [`skills/set-up-forked-open-source-repo/SKILL.md`](../skills/set-up-forked-open-source-repo/SKILL.md)

Configure the current checkout for upstream/fork OSS contribution. The skill verifies that the fork exists on GitHub and that its immediate parent is the declared upstream, probes both repositories' `refs/heads/main`, optionally performs a destructive fork sync of branches and tags after explicit confirmation, then rewires local remotes so `origin` points at the fork and `upstream` points at upstream. It disables upstream pushes with an invalid-scheme push URL, fetches `origin`, sets `main` to track `origin/main`, and fast-forwards only from a clean `main` checkout.

The workflow is intentionally single-clone (per-clone single-flight lock; multiple clones may run concurrently) and supports any GitHub-compatible host, with github.com as the default. It refuses dirty linked worktrees, in-progress git operations in any linked worktree, missing local `main`, non-`main` checkouts, local `main` ahead of `origin/main`, diverged local/remote `main`, ambiguous remote layouts, non-parseable / mixed-host URLs, duplicate fork remotes, multi-fetch URL remotes, and multi-push URL remotes. If the fork is missing, it prints fork-creation instructions and exits without local mutation. `--init-submodules` is opt-in; default runs ignore submodules.

## `/upgrade-larch`

**Arguments**: *(none)*

**Source**: [`skills/upgrade-larch/SKILL.md`](../skills/upgrade-larch/SKILL.md)

Upgrade the larch plugin to the latest version. Targets the standard GitHub install (`claude plugin marketplace add character-ai/larch`): the skill removes and re-adds the marketplace, then reinstalls the plugin so the newest release is picked up. Contributors using a local checkout (`claude --plugin-dir .` or `claude plugin marketplace add .`) should `git pull` instead. Delegates to `${CLAUDE_PLUGIN_ROOT}/skills/upgrade-larch/scripts/upgrade-larch.sh`; on success the user is told to restart Claude Code to apply the new version.
