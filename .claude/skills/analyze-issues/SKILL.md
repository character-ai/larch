---
name: analyze-issues
description: "Use when generating a backlog-and-process insight report from a repository's GitHub issues -- coverage stats, category breakdown, cumulative-growth chart, wasteful-work signatures, and reviewer/persona effectiveness."
allowed-tools: Bash, Read
---

# analyze-issues

Generate a backlog-and-process insight report from the current repository's GitHub issues, including coverage stats, category breakdown, cumulative growth, wasteful-work signatures, and reviewer/persona effectiveness.

## Usage

`/analyze-issues [--limit N] [--span-days N] [--top-K N] [--categories=auto|default] [--log-root PATH] [--repo OWNER/REPO] [--filed-issue-details-json PATH] [--lenient]`

## Run the Analysis

Call the coordinator with any forwarded flags via the Bash tool:

```bash
python3 "$PWD/python/cli.py" analyze-issues run [flags]
```

The coordinator fetches issues, analyzes the local JSON dump, and prints the assembled report to stdout. Do not parse, format, branch, or perform the analysis in the main agent.

Flags:

- `--limit N`: maximum issues to fetch. Default: `2000`.
- `--span-days N`: analysis span override. Default: auto.
- `--top-K N`: number of top items to show in ranked sections. Default: `10`.
- `--categories=auto|default`: category mode. Default: `default`.
- `--log-root PATH`: run-log root to scan for filed OOS evidence. Default: `larch-logs`.
- `--repo OWNER/REPO`: explicit GitHub repository. Default: auto-detect for live runs.
- `--filed-issue-details-json PATH`: optional offline enrichment sidecar for filed OOS issue details. Offline JSON reanalysis remains dump-only unless this is supplied.
- `--lenient`: forwarded to `analyze.py`. Suppresses the >5% non-dict or malformed-number abort in `load_issues` so a corrupted dump still produces a partial report. Per-element stderr `WARN load_issues: ...` lines are still emitted; this flag only disables the threshold check.

The raw `gh` JSON dump is saved to `${TMPDIR:-/tmp}/<sanitized-repo>-issues.json` for follow-up reanalysis. The slug converts `/` to `-` and keeps only alnum, `-`, and `_`; dumps are intentionally user-private via `umask 077` and an atomic temp+mv write. The live coordinator contract is covered by `python/analyze_issues.py` and `python/test_analyze_issues.py`.

## Fate-adjusted OOS Scoring

The report includes a diagnostic `## Fate-adjusted OOS Scoring` section after the reviewer/persona tables. It scans `larch-logs/{design,implement}/` for filed OOS evidence, joins filed issue numbers to the fetched issue dump, and reports provisional points, fate-adjusted points, docked counts, and fate buckets per reviewer. It does not mutate run logs, live voting scores, or reviewer ledgers.

Live runs may enrich only filed OOS candidates with targeted `gh issue view` calls so combined-away comments can be detected. Bulk `gh issue list` does not fetch comments; if newer optional list fields such as `stateReason` or `url` are unavailable, the fetch retries without them and marks the reduced data as degraded.

Implement-phase scoring depends on same-run joins between `oos-issues.ndjson` and nested `round-*/oos-accepted-*.md` files. Joins support namespaced and hash stable ids consistent with `oos_filer._stable_identifier`, round-qualified dedupe keys, cap-rollup expansion for explicit members and main-agent aggregate ids, fallback rollup expansion only when the unfiled candidate count exactly matches the parsed rollup count, legacy body citation fallback, and explicit filed issue references only. Arbitrary bare `#N` mentions are not filed-OOS evidence.

Design-phase scoring joins `OOS_FILE_MAP` rows to `oos-accepted-design.md` blocks when present. Combined-away detection relies on the targeted per-issue comment fetch for filed OOS issues only.

## Implementation

Logic lives in the Python runtime modules. SKILL.md is a thin coordinator.

- `python/cli.py analyze-issues run`: top-level coordinator. Parses flags, detects the repo, chains the fetch and the analyzer.
- `python/cli.py analyze-issues fetch`: wraps the single `gh issue list` shell-out.
- `python/analyze_issues.py`: main analyzer (categories, coverage, growth, patterns, waste signatures, reviewer/persona effectiveness, fate-adjusted OOS scoring, executive summary).
- `python/render_chart.py`: cumulative-growth ASCII chart helper imported by `python/analyze_issues.py`.
- `python/test_analyze_issues.py`: offline regression coverage for the coordinator, fetch, analyzer, and chart behavior.

## Anti-patterns

- Keep reviewer attribution regexes longest-first, with `codex` before `code`.
- Do not use Agent or Explore subagents for the analysis itself.
- Do not exclude `[OOS]` issues; they are workflow-driven-waste signal.
- Do not collapse duplicate titles at fetch time; duplicates are evidence.
