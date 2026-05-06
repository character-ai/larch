---
name: analyze-issues
description: "Use when generating a backlog-and-process insight report from a repository's GitHub issues -- coverage stats, category breakdown, cumulative-growth chart, wasteful-work signatures, and reviewer/persona effectiveness."
argument-hint: ""
allowed-tools: Bash, Read
---

# analyze-issues

Generate a backlog-and-process insight report from the current repository's GitHub issues, including coverage stats, category breakdown, cumulative growth, wasteful-work signatures, and reviewer/persona effectiveness.

## Usage

`/analyze-issues [--limit N] [--span-days N] [--top-K N] [--categories=auto|default]`

## Run the Analysis

Call `$PWD/.claude/skills/analyze-issues/scripts/run-analysis.sh` with any forwarded flags via the Bash tool. The script fetches issues, analyzes the local JSON dump, and prints the assembled report to stdout. Do not parse, format, branch, or perform the analysis in the main agent.

Flags:

- `--limit N`: maximum issues to fetch. Default: `2000`.
- `--span-days N`: analysis span override. Default: auto.
- `--top-K N`: number of top items to show in ranked sections. Default: `10`.
- `--categories=auto|default`: category mode. Default: `default`.

The raw `gh` JSON dump is saved to `/tmp/<repo>-issues.json` for follow-up reanalysis.

## Anti-patterns

- Keep reviewer attribution regexes longest-first, with `codex` before `code`.
- Do not use Agent or Explore subagents for the analysis itself.
- Do not exclude `[OOS]` issues; they are workflow-driven-waste signal.
- Do not collapse duplicate titles at fetch time; duplicates are evidence.
