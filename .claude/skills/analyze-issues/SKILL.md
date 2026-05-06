---
name: analyze-issues
description: "Use when generating a backlog-and-process insight report from a repository's GitHub issues -- coverage stats, category breakdown, cumulative-growth chart, wasteful-work signatures, and reviewer/persona effectiveness."
allowed-tools: Bash, Read
---

# analyze-issues

Generate a backlog-and-process insight report from the current repository's GitHub issues, including coverage stats, category breakdown, cumulative growth, wasteful-work signatures, and reviewer/persona effectiveness.

## Usage

`/analyze-issues [--limit N] [--span-days N] [--top-K N] [--categories=auto|default]`

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

The raw `gh` JSON dump is saved to `/tmp/<repo>-issues.json` for follow-up reanalysis.

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
