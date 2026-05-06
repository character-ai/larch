---
name: analyze-issues
description: "Use when generating a backlog-and-process insight report from a repository's GitHub issues -- coverage stats, category breakdown, cumulative-growth chart, wasteful-work signatures, and reviewer/persona effectiveness."
allowed-tools: Bash, Read
---

# analyze-issues

Generate a backlog-and-process insight report from the current repository's GitHub issues, including coverage stats, category breakdown, cumulative growth, wasteful-work signatures, and reviewer/persona effectiveness.

## Usage

`/analyze-issues [--limit N] [--span-days N] [--top-K N] [--categories=auto|default] [--lenient]`

## Run the Analysis

Call the coordinator with any forwarded flags via the Bash tool:

```bash
$PWD/.claude/skills/analyze-issues/scripts/run-analysis.sh [flags]
```

The coordinator fetches issues, analyzes the local JSON dump, and prints the assembled report to stdout. Do not parse, format, branch, or perform the analysis in the main agent.

Flags:

- `--limit N`: maximum issues to fetch. Default: `2000`.
- `--span-days N`: analysis span override. Default: auto.
- `--top-K N`: number of top items to show in ranked sections. Default: `10`.
- `--categories=auto|default`: category mode. Default: `default`.
- `--lenient`: forwarded to `analyze.py`. Suppresses the >5% non-dict or malformed-number abort in `load_issues` so a corrupted dump still produces a partial report. Per-element stderr `WARN load_issues: ...` lines are still emitted; this flag only disables the threshold check.

The raw `gh` JSON dump is saved to `${TMPDIR:-/tmp}/<sanitized-repo>-issues.json` for follow-up reanalysis. The slug converts `/` to `-` and keeps only alnum, `-`, and `_`; dumps are intentionally user-private via `umask 077` and an atomic temp+mv write. See `scripts/run-analysis.md` for the full contract.

## Implementation

Logic lives in `scripts/`. SKILL.md is a thin coordinator. Per-script contracts are documented beside each file:

- `scripts/run-analysis.sh` (contract: `scripts/run-analysis.md`) — top-level coordinator. Parses flags, detects the repo, chains the fetch and the analyzer.
- `scripts/fetch-issues.sh` (contract: `scripts/fetch-issues.md`) — wraps the single `gh issue list` shell-out.
- `scripts/analyze.py` (contract: `scripts/analyze.md`) — main analyzer (categories, coverage, growth, patterns, waste signatures, reviewer/persona effectiveness, executive summary).
- `scripts/render-chart.py` (contract: `scripts/render-chart.md`) — cumulative-growth ASCII chart helper imported by `analyze.py`.

## Anti-patterns

- Keep reviewer attribution regexes longest-first, with `codex` before `code`.
- Do not use Agent or Explore subagents for the analysis itself.
- Do not exclude `[OOS]` issues; they are workflow-driven-waste signal.
- Do not collapse duplicate titles at fetch time; duplicates are evidence.
