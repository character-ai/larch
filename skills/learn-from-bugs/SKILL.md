---
name: learn-from-bugs
description: "Use when mining a repo's closed bugs for recurring root causes to propose lint rules, invariants, guideline entries, and fixes for still-broken code. Defaults to [BUG]; optional verbal filter."
argument-hint: "[-n COUNT] [--state closed|open|all] [--repo OWNER/REPO] [--search QUERY] [verbal description of issues to mine]"
allowed-tools: Bash, Read, Grep, Glob, Write, Edit, AskUserQuestion, Skill
---

# Learn From Bugs

**MANDATORY: READ ENTIRE FILE before composing user-facing prose: `${CLAUDE_PLUGIN_ROOT}/skills/shared/readability-style.md`.**

Mine a repository's closed bug reports for recurring root-cause patterns, then propose preventions ranked by how mechanically enforceable they are. The workflow is **report-only by default**: it reads issues and the repo, writes one report to a scratch run directory, and makes no repository or GitHub change until the operator approves a specific follow-up.

The engine keeps this cheap. It never reads full issue bodies into context: `learn-from-bugs prepare` compresses each body to a compact root-cause digest first (dropping the appended `/design` plan, which dominates the bytes), so the synthesis reads a small fraction of the raw tokens. The prepared stats print a `DIGEST_TOKENS_EST` so the operator can size a run before spending.

**No sub-agents.** Do the clustering and synthesis inline in this session. Do not spawn `Task`/`Agent` fan-out; the digest is small enough to read directly, and fan-out is the expensive failure mode this skill exists to avoid.

**Anti-halt continuation reminder.** After any child `Skill` call (for example `/issue`) returns, IMMEDIATELY continue with this skill's next numbered step. Do not end the turn on the child's cleanup output, and do not write a handoff or status recap. → shared/subskill-invocation.md#anti-halt

## Contract

- Flags: `-n COUNT` (issues to mine, default 50), `--state` (default `closed`), `--repo OWNER/REPO`, `--search QUERY` (explicit gh search that overrides the verbal description).
- Everything else in `$ARGUMENTS` is a **verbal description** of which issues to mine. Translate it into a `gh` search expression. With no description and no `--search`, mine `[BUG] in:title`.
- Report-only by default. Every repository or GitHub mutation is gated behind an explicit operator approval in Step 5.
- File issues only through `/issue` (never `gh issue create` directly).
- Cite issues by number and refer to code by symbol, not line number. Do not paste machine-local absolute paths or hardcode counts that will drift; read live counts from the prepared stats and coverage index.

<!-- step:1 - Resolve the search -->
## Step 1 - Resolve the search

Parse `$ARGUMENTS`. Pull out `-n`, `--state`, `--repo`, and `--search` if present. Treat the remaining prose as the verbal description.

Decide the gh search query:

- If `--search QUERY` was given, use it verbatim.
- Else if a verbal description was given, translate it to a gh search expression. Prefer `in:title` for prefix-style descriptions and `in:title,body` for topical ones. Example: "stall bugs in implement" becomes `[BUG] stall implement in:title,body`.
- Else use the default `[BUG] in:title`.

State the resolved query and count back to the operator in one line before proceeding.

<!-- step:2 - Prepare the digest and coverage index -->
## Step 2 - Prepare the digest and coverage index

Create a scratch run directory and run the prepare verb. Pass the plugin's `cli.py` via `${CLAUDE_PLUGIN_ROOT}`, and scan the **target** repository (the current working directory) for its existing enforcement surface.

```bash
RUN_DIR=$(mktemp -d "${TMPDIR:-/tmp}/learn-from-bugs.XXXXXX")
python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" learn-from-bugs prepare \
  --search "$RESOLVED_SEARCH" \
  --state "$STATE" \
  --limit "$COUNT" \
  --out "$RUN_DIR" \
  --root "$PWD"
```

Parse only whole-line `KEY=value` records from stdout: `DIGEST_PATH`, `COVERAGE_INDEX_PATH`, `REPO`, `ISSUES_SELECTED`, `STRUCTURED`, `FREEFORM_OR_TITLE_ONLY`, `DIGEST_TOKENS_EST`, and the `*_INDEXED` counts. Abort if `DIGEST_PATH` is missing.

If `DIGEST_TOKENS_EST` is large relative to the budget the operator signalled, say so and offer to lower `-n` before reading.

<!-- step:3 - Read and cluster -->
## Step 3 - Read and cluster

Read `DIGEST_PATH` (one JSON record per line: `number`, `title`, `sections` with `summary` / `root cause analysis` / `suggested fix(es)`, or a `_freeform` / `_title_only` fallback). Read `COVERAGE_INDEX_PATH` (the target repo's `guidelines`, `invariants`, `rules`, `python_lints`, `script_lints`).

Cluster the root causes into recurring patterns. For each cluster, note the member issue numbers and a one-line mechanism. A pattern that appears once is an anecdote; a pattern across several issues is a candidate for prevention.

<!-- step:4 - Write the report -->
## Step 4 - Write the report

Write `${RUN_DIR}/report.md` with these sections, in order. The dedup section is mandatory and comes before any proposal, so proposals are always the residual, never a duplicate of existing coverage.

For proposal wording in sections 4 through 6, exactness and pasteability take precedence over brevity. Make proposal text complete, append-ready, and usable without operator expansion; keep the rest of the report brief.

1. **Scope and cost.** Resolved search, `REPO`, `ISSUES_SELECTED`, structured-vs-fallback split, and the token cost actually spent reading the digest.
2. **Root-cause clusters.** Each recurring pattern, its member issues, and its mechanism, ordered by frequency.
3. **Already covered (dedup).** For every principle the clusters imply, map it to existing coverage from the coverage index: the guideline id, the `.claude/rules/` file, and the lint that already enforces it. This is the filter that keeps the proposals below honest.
4. **Proposed mechanical lint rules.** Residual gaps only, ranked by precision times frequency. For each, state exactly what it flags, which surface it scans, the backing issues, false-positive risk, suppression policy, and baseline policy. The baseline policy must say whether existing violations need a shrinking reason-bearing baseline rather than a hard ban.
5. **Proposed architectural invariants.** Never-violate candidates. For each, include a full normative statement, the boundary where it applies, what must always or never happen, the evidence or check that proves it, and a **best-home classification**: `lint` if it is mechanizable, `rule` if it is path-scoped and best delivered as a `.claude/rules/` reminder when the relevant file is touched, `invariants-file` if it is never-violate but neither mechanizable nor cleanly path-scoped, or `guideline` if it is really aspirational. For `rule`, include complete draft `.claude/rules/*.md` file text with frontmatter `paths:` globs and body. For `invariants-file`, include a complete proposed entry formatted for the target repo's invariants file, with a heading using the target repo's invariant-ID pattern and a full body statement without a Deviate-when clause. Make each draft append-ready.
6. **Proposed guideline entries.** Aspirational residuals. Match the target repo's numbering and section style if it has one; if it does not, use clear complete sentences with stable issue citations. Never compress below complete sentences. Each entry must include a full imperative statement, a full Why sentence citing the backing issues, and a full Deviate-when sentence. Do not use fragments, abbreviations, or shorthand the reader must expand.
7. **Issues to file.** Concrete still-broken code the mining surfaced, for example a fix that was scoped to one call site while identical sites remain, phrased as a fileable problem statement with evidence.

Print the report to the operator and the `RUN_DIR` path.

<!-- step:5 - Follow-up gates -->
## Step 5 - Follow-up gates

Stop here by default. Then offer follow-ups, each behind its own explicit approval. Never bundle them.

- **File issues.** For the Step 4 "Issues to file" items the operator approves, invoke `/issue` via the Skill tool once with the drafted bodies. Do not call `gh issue create` directly.
- **Append guideline entries.** On approval, `Edit` the target repo's guideline file to append the approved entries, matching its existing numbering and style.
- **Create or extend the invariants file.** Only if the operator confirms an `ARCHITECTURAL_INVARIANTS.md` should exist, create or append it with the approved never-violate entries. If the operator instead prefers rules, draft the `.claude/rules/*.md` files instead.
- **Scaffold a lint.** On approval, scaffold a proposed lint and its test under the repo's lint conventions, then hand the real implementation to `/design` and `/implement`. Do not wire it into CI in this skill.

If the operator approves nothing, end after the report.
