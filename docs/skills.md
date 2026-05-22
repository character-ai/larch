# Skills

Reference for every slash command shipped by the larch plugin. Each section below covers one skill: invocation, arguments, behavior, and links to the canonical `SKILL.md` source.

- [`/alias`](#alias)
- [`/cleanup`](#cleanup)
- [`/compress-skill`](#compress-skill)
- [`/create-skill`](#create-skill)
- [`/design`](#design)
- [`/fix-issue`](#fix-issue)
- [`/implement`](#implement)
- [`/issue`](#issue)
- [`/report-tokens`](#report-tokens)
- [`/relevant-checks`](#relevant-checks)
- [`/research`](#research)
- [`/review`](#review)
- [`/review-and-fix`](#review-and-fix)
- [`/set-up-forked-open-source-repo`](#set-up-forked-open-source-repo)
- [`/show-skill`](#show-skill)
- [`/simplify-skill`](#simplify-skill)
- [`/skill-evolver`](#skill-evolver)
- [`/umbrella`](#umbrella)
- [`/upgrade-larch`](#upgrade-larch)

## `/alias`

**Arguments**: `[--merge] [--private] <alias-name> <target-skill> [preset-flags...]`

**Source**: [`skills/alias/SKILL.md`](../skills/alias/SKILL.md)

Create an alias for a larch skill with preset flags. Delegates to `/implement --auto` for the full pipeline (code review, version bump, PR). `--merge` also merges the PR.

**Target directory** is auto-resolved: inside a Claude plugin source repo (detected by the two-file predicate `.claude-plugin/plugin.json` AND `skills/implement/SKILL.md` at the git repo root), the alias is generated under `skills/<alias-name>/SKILL.md` (exported plugin skill, ships with the plugin); anywhere else, it's generated under `.claude/skills/<alias-name>/SKILL.md` (dev-only repo-private). `--private` forces `.claude/skills/<alias-name>/` even inside a plugin repo (escape hatch); in non-plugin repos it's a no-op.

Example (in a plugin repo): `/alias i implement --merge` creates `<repo-root>/skills/i/SKILL.md` so that `/i <feature>` is equivalent to `/implement --merge <feature>`.

Example with `--private` or in a consumer repo: `/alias i implement --merge` creates `<repo-root>/.claude/skills/i/SKILL.md` (dev-only).

## `/block-issue`

**Arguments**: `<ISSUE_A> <ISSUE_B> [--repo owner/name]`

**Source**: [`skills/block-issue/SKILL.md`](../skills/block-issue/SKILL.md)

Express a native GitHub blocked-by relationship between two issues using the `addBlockedBy` GraphQL mutation. ISSUE_A is marked as blocked by ISSUE_B. Repo is auto-detected from `gh repo view` when `--repo` is omitted. Verifies the relationship was recorded before confirming.

## `/cleanup`

**Arguments**: *(none)*

**Source**: [`skills/cleanup/SKILL.md`](../skills/cleanup/SKILL.md)

Remove leftover larch session temp directories from `~/.cache/larch/sessions/` and `/tmp`. Checks for active sessions (`.larch-keepalive`) before deleting cache dirs, and aborts entirely if more than one `claude` process is detected. Reports counts removed from each location.

## `/compress-skill`

**Arguments**: `<skill-name-or-path>`

**Source**: [`skills/compress-skill/SKILL.md`](../skills/compress-skill/SKILL.md)

Compress a skill's Markdown prose via a behavior-preserving rewrite.

## `/create-skill`

**Arguments**: `[--plugin] [--multi-step] [--merge] <skill-name> <description>`

**Source**: [`skills/create-skill/SKILL.md`](../skills/create-skill/SKILL.md)

Scaffold a new larch-style skill from a name and description.

## `/design`

**Arguments**: `[--auto] [--quick] [--full] [--subagent] [--session-env <path>] <feature description>`

**Source**: [`skills/design/SKILL.md`](../skills/design/SKILL.md) · [Diagram](../skills/design/diagram.svg)

Design an implementation plan with collaborative multi-reviewer review. The [sketch topology](topology.md#design.sketch.regular_slots) documented in [Collaborative Sketches](collaborative-sketches.md) independently proposes architectural approaches when the router assigns a non-zero sketch budget, then the dialectic debate and [judge panel](topology.md#design.dialectic.judge_panel) described in `skills/shared/dialectic-protocol.md` resolves contested decisions. The [validation panel](topology.md#design.plan_review.cursor_archetypes) documented in [Review Agents](review-agents.md) then reviews the full plan. `--auto` suppresses all interactive question checkpoints. `--quick` caps sketch fan-out at the [quick sketch topology](topology.md#design.sketch.quick_slots) and uses quick plan review; `--full` forces the full sketch fan-out.

## `/fix-issue`

**Arguments**: `[--auto] [--no-admin-fallback] [--no-logs-commit] [--coder=<value>] [--inline] [--hard] <number-or-url>` (positional issue number or URL is **required**)

**Source**: [`skills/fix-issue/SKILL.md`](../skills/fix-issue/SKILL.md)

Process one approved GitHub issue per invocation, classifying intent and delegating PR work to `/implement`.

**Umbrella support**: when `/fix-issue <umbrella#>` is invoked on an umbrella issue (detected post-#846 by title-only — title prefix `Umbrella:` / `Umbrella —` after stripping leading bracket-blocks per #819; body content is NOT consulted), `/fix-issue` dispatches to the umbrella's next eligible child instead of working on the umbrella body itself. Children are parsed from markdown task-list items (`- [ ] #N — ...`) in body order; cross-repo references (`owner/repo#N`) and prose `#N` mentions are NOT considered children. When all parsed children close, the umbrella is automatically renamed to `[DONE]`, gets a closing comment posted, and is closed (idempotent: concurrent finalize attempts won't double-comment). See `skills/fix-issue/SKILL.md` Known Limitations for the full umbrella contract.

## `/implement`

**Arguments**: `[--auto] [--forked] [--design-only] [--no-issues] [--inline] [--merge | --draft] [--no-admin-fallback] [--no-logs-commit] [--coder=claude|codex|cursor] [--session-env <path>] [--issue <N>] <feature description>`

**Source**: [`skills/implement/SKILL.md`](../skills/implement/SKILL.md) · [Diagram](../skills/implement/diagram.svg)

Full implementation workflow spanning design through PR merge. Step 5 always runs `review-and-fix.sh` with `--panel hard`: up to **5 rounds** (base cap 5, plus degraded-round inflation on argv), a **3-judge panel on round 1** (Claude opus + Codex + Cursor; Claude replacement when an external is unhealthy) and a **2-judge panel on rounds 2+** (Claude + Cursor; Codex voter omitted), and the **review panel** with **6 Cursor specialists** (plus optional dynamic archetypes). The `--design-only` flag publishes design artifacts then exits without implementation (mutually exclusive with `--merge`).

## `/issue`

**Arguments**: `[--input-file FILE] [--title-prefix P] [--label L]... [--body-file F] [--dry-run] [--no-dedup] [<issue description>]`

**Source**: [`skills/issue/SKILL.md`](../skills/issue/SKILL.md)

Create one or more GitHub issues with LLM-based semantic duplicate detection. Supports single mode (free-form description) and batch mode (`--input-file`). 2-phase dedup against open + recently-closed issues (default 90-day window). `--no-dedup` skips the entire dedup + dependency analysis pipeline and creates all items directly — useful for archival issues (e.g., `/research` reports) where each run produces genuinely different content. `/implement` Step 9a.1 calls this skill in batch mode to file OOS issues.

**Default-on inter-issue blocker-dependency analysis** (issue #546): unless `--no-dedup` is set, every invocation analyzes the new item(s) against existing OPEN issues and applies hard GitHub-native blocker dependencies via the Issue Dependencies REST API on detected pairs (merge-conflict risk or "must land first"). Hard-fail with retries (3 tries, 10s/30s sleeps); on retry exhaustion the failed item is rolled back (orphan close) — when multiple items are processed, unrelated items continue — and the run exits non-zero if any item failed, yielding a clean "create-then-close" recovery rather than a dangling issue with missing dependency wiring.

## `/report-tokens`

**Arguments**: *(none)*

**Source**: [`skills/report-tokens/SKILL.md`](../skills/report-tokens/SKILL.md)

Analyze structured token reports across closed GitHub issues in the current larch repository. The skill searches closed issues whose comments contain `token-report-begin`, fetches their bodies and comments via `gh`, writes a raw JSON cache under a temp directory, parses Claude/Codex/Cursor grand-total rows, estimates per-issue costs, classifies issues from `**Workflow path**`, generates SIMPLE and HARD cost-over-time PNGs, and prints a written analysis with top SIMPLE costs, HARD phase breakdown, cache-read dominance, and concrete cost-reduction suggestions. Dollar values are observability estimates, not billing truth; rates are printed and can be overridden with environment variables.

## `/relevant-checks`

**Arguments**: *(none)*

**Source**: [`.claude/skills/relevant-checks/SKILL.md`](../.claude/skills/relevant-checks/SKILL.md)

Run pre-commit linters (shellcheck, markdownlint, jsonlint, actionlint, gitleaks) scoped to changed files (except gitleaks, which always scans the full working tree; see the relevant-checks skill). Human-invocable for local validation. `/implement` and `/review` use the script-first helper `scripts/run-relevant-checks-captured.sh` to call the same project-local `run-checks.sh` without invoking the Skill on the green path. **Not part of the plugin surface; each consuming repo provides its own.**

## `/research`

**Arguments**: `[--no-issue] <research question or topic>`

**Source**: [`skills/research/SKILL.md`](../skills/research/SKILL.md) · [Diagram](../skills/research/diagram.svg)

Collaborative best-effort read-only research with a fixed-shape topology. The research phase always runs a planner pre-pass that decomposes `RESEARCH_QUESTION` into focused subquestions, then the [Codex-first lanes](topology.md#research.lanes) listed in the research skill (architecture / edge cases / external comparisons / security) with a per-lane Claude `Agent` fallback when Codex is unavailable. The validation phase runs the [panel](topology.md#research.validation_panel) described in [Review Agents](review-agents.md), with Claude fallbacks when an external tool is unavailable. Cursor is NOT used in research lanes (it remains a validation reviewer).

**Step 2.5 — Citation Validation (unconditional)**: between Step 2 (validation) and Step 2.6 (critique loop) the deterministic shell validator `skills/research/scripts/validate-citations.sh` extracts cited URLs / DOIs / file:line references from the synthesis, HEAD-fetches URLs under SSRF guards (HTTPS-only, `--max-redirs 0`, `--noproxy '*'`, RFC1918/IPv6 link-local/RFC6598 hostname pre-rejection, DNS resolved-IP private-range check, connection-pinning via `--resolve` to mitigate rebinding TOCTOU), validates DOIs syntactically + via `doi.org` HEAD, and spot-checks file:line ranges against the git tree (with `realpath` containment). Output is a 3-state ledger (PASS / FAIL / UNKNOWN with reason classifier) sidecar at `$RESEARCH_TMPDIR/citation-validation.md` that Step 3 splices as a `## Citation Validation` section into `research-report-final.md`. Fail-soft: per-claim failures surface as advisory warnings only; the validator always exits 0; Step 3 is never blocked.

The run produces a structured report with findings, risk assessment, difficulty estimates, and feasibility verdict.

**Token telemetry**: Step 4 always renders a `## Token Spend` section before tmpdir cleanup, summarizing per-phase Claude subagent tokens. Telemetry is observability-only — there is no budget enforcement. Claude inline (orchestrator) and external lanes (Cursor/Codex) are unmeasurable and excluded from the totals. When env var `LARCH_TOKEN_RATE_PER_M` is set (USD per million tokens), the report includes a `$` cost column. See [`scripts/token-tally.md`](../scripts/token-tally.md) for the helper contract. Tracked repo files are not modified by the Claude `Edit | Write | NotebookEdit` tool surface — scratch writes are permitted only under canonical `/tmp` (enforced mechanically by the skill-scoped `scripts/deny-edit-write.sh` PreToolUse hook). Step 3.5 auto-archives the full report as a GitHub issue on each successful run (via `/issue` single mode); `--no-issue` skips this step. `/issue` may also be invoked when the research brief calls for filing findings as issues.

## `/review`

**Arguments**: `[--diff] [--no-issues] [<description>]`

**Source**: [`skills/review/SKILL.md`](../skills/review/SKILL.md) · [Diagram](../skills/review/diagram.svg)

Code review with the specialist panel described in [Review Agents](review-agents.md). Supports `--diff`, which reviews branch changes vs main and implements accepted suggestions in a recursive loop, and positional `<description>`, which reviews existing code and files accepted findings as GitHub issues by default (`--no-issues` to suppress).

## `/review-and-fix`

**Arguments**: `--findings-file <path> --review-tmpdir <path> [--session-env <path>]`

**Source**: [`skills/review-and-fix/SKILL.md`](../skills/review-and-fix/SKILL.md)

Apply accepted review findings as code fixes. Internal sub-skill invoked by `/review` in diff mode and by `/implement` Step 5; not a standalone user entry point. It dispatches Codex, Cursor, then a Claude subagent fallback to apply voted-in suggestions directly, with pre-dispatch submodule finding scrubbing and post-dispatch submodule revert checks.

## `/set-up-forked-open-source-repo`

**Arguments**: `--upstream <owner/repo> --fork <owner/repo> [--mirror-confirmed] [--init-submodules]`

**Source**: [`skills/set-up-forked-open-source-repo/SKILL.md`](../skills/set-up-forked-open-source-repo/SKILL.md)

Configure the current checkout for upstream/fork OSS contribution. The skill verifies that the fork exists on GitHub and that its immediate parent is the declared upstream, probes both repositories' `refs/heads/main`, optionally performs a destructive fork sync of branches and tags after explicit confirmation, then rewires local remotes so `origin` points at the fork and `upstream` points at upstream. It disables upstream pushes with an invalid-scheme push URL, fetches `origin`, sets `main` to track `origin/main`, and fast-forwards only from a clean `main` checkout.

The workflow is intentionally single-clone (per-clone single-flight lock; multiple clones may run concurrently) and supports any GitHub-compatible host, with github.com as the default. It refuses dirty linked worktrees, in-progress git operations in any linked worktree, missing local `main`, non-`main` checkouts, local `main` ahead of `origin/main`, diverged local/remote `main`, ambiguous remote layouts, non-parseable / mixed-host URLs, duplicate fork remotes, multi-fetch URL remotes, and multi-push URL remotes. If the fork is missing, it prints fork-creation instructions and exits without local mutation. `--init-submodules` is opt-in; default runs ignore submodules.

## `/show-skill`

**Arguments**: `<skill-name>`

**Source**: [`skills/show-skill/SKILL.md`](../skills/show-skill/SKILL.md)

Display the contents of a skill's `SKILL.md` file. Accepts bare name (e.g., `implement`), `larch:`-prefixed form (e.g., `larch:review`), or leading-`/` form. Searches the plugin `skills/` tree first, then the consumer repo's `.claude/skills/`.

## `/simplify-skill`

**Arguments**: `<skill-name>`

**Source**: [`skills/simplify-skill/SKILL.md`](../skills/simplify-skill/SKILL.md)

Refactor a skill for stronger adherence to design principles and reduced SKILL.md footprint.

## `/skill-evolver`

**Arguments**: `<skill-name>`

**Source**: [`skills/skill-evolver/SKILL.md`](../skills/skill-evolver/SKILL.md)

Evolve an existing larch skill by researching concrete improvements and filing them as GitHub issues. Validates `<skill-name>` against `^[a-z][a-z0-9-]*$` and resolves it to `skills/<name>/SKILL.md` (plugin tree) or `.claude/skills/<name>/SKILL.md` (project-local fallback); aborts cleanly if the target does not exist. Then invokes `/research` with a templated prompt that asks the documented lane fan-out to produce concrete actionable improvements with citations — repo-local sibling-skill comparisons via `file:line` references and reputable external sources (Anthropic / OpenAI / DeepMind / ≥500-star OSS) via URLs. If the research lane surfaces ≥1 actionable improvement, distills the findings into a task description and delegates to `/umbrella`. Zero improvements → clean exit, no issues filed. The skill itself does NOT modify the target skill's files. Example: `/skill-evolver design`.

## `/umbrella`

**Arguments**: `[--label L]... [--title-prefix P] [--repo OWNER/REPO] [--closed-window-days N] [--blocked-by-issue N] [--dry-run] <task description or empty to deduce from context>`

**Source**: [`skills/umbrella/SKILL.md`](../skills/umbrella/SKILL.md)

Plan-to-issues orchestrator. Takes a task description (or deduces it from session context), classifies it as one-shot or multi-piece, and delegates GitHub issue creation to `/issue` — adding native blocked-by dependencies to form an execution DAG and back-linking children to the umbrella when multi-piece. Typically invoked transitively by `/review` (description-mode finding filing) and `/skill-evolver` (research-finding filing) rather than called directly by humans, though direct invocation is supported. The one-shot path emits a single child issue and skips umbrella creation; the multi-piece path emits an umbrella tracking issue plus one child per piece (very small items may be bundled into a single composed piece per Step 3B.1's bundling rule), with `Closes #<umbrella>` blocked-by edges wired between children and the umbrella. `--blocked-by-issue N` is a caller-supplied policy blocker; `N` is a positive integer issue number, forwarded verbatim to `/issue` on both Step 3A (one-shot) and Step 3B.2 (batch children). Only batch child creation can succeed with the policy edge — single-mode is rejected by `/issue`'s frozen batch-mode-only error, providing fail-fast on misclassified one-shot runs (no silent drop). The flag is intentionally NOT forwarded to the Step 3B.3 umbrella-create call — the policy edge is meant for children, not the umbrella itself. `--dry-run` previews the proposed batch without GitHub mutations. Example: `/umbrella refactor the auth subsystem across schema, middleware, and tests`.

## `/upgrade-larch`

**Arguments**: *(none)*

**Source**: [`skills/upgrade-larch/SKILL.md`](../skills/upgrade-larch/SKILL.md)

Upgrade the larch plugin to the latest version. Targets the standard GitHub install (`claude plugin marketplace add character-ai/larch`): the skill removes and re-adds the marketplace, then reinstalls the plugin so the newest release is picked up. Contributors using a local checkout (`claude --plugin-dir .` or `claude plugin marketplace add .`) should `git pull` instead. Delegates to `${CLAUDE_PLUGIN_ROOT}/skills/upgrade-larch/scripts/upgrade-larch.sh`; on success the user is told to restart Claude Code to apply the new version.
