---
name: analyze-issues
description: "Use when generating a GitHub-issue backlog report: coverage, categories, growth chart, waste signatures, reviewer/persona, and voter diagnostics."
allowed-tools: Bash, Read
---

# analyze-issues

**MANDATORY — READ ENTIRE FILE before composing user-facing prose: `$PWD/skills/shared/readability-style.md`.**

Generate a backlog-and-process insight report from the current repository's GitHub issues, including coverage stats, category breakdown, cumulative growth, wasteful-work signatures, reviewer/persona effectiveness, fate-adjusted OOS scoring, and ground-truth voter calibration.

## Usage

`/analyze-issues [--limit N] [--span-days N] [--top-K N] [--categories=auto|default] [--log-root PATH] [--repo OWNER/REPO] [--lenient] [--ground-truth-verdict] [--since-date DATE] [--min-runs N] [--min-larch-version VERSION]`

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
- `--lenient`: forwarded to `analyze.py`. Suppresses the >5% non-dict or malformed-number abort in `load_issues` so a corrupted dump still produces a partial report. Per-element stderr `WARN load_issues: ...` lines are still emitted; this flag only disables the threshold check.
- `--ground-truth-verdict`: print only the ground-truth verdict report and return its gate exit code.
- `--since-date DATE`: verdict corpus start date. Default: `2026-06-26`.
- `--min-runs N`: required unique verdict `run_dir` count. Default: `150`.
- `--min-larch-version VERSION`: verdict manifest version floor. Default: `52.1.0`.

Offline reanalysis with an explicit issue dump and optional filed-issue sidecar:

```bash
python3 "$PWD/python/cli.py" analyze-issues analyze --json /path/to/issues.json [--log-root PATH] [--repo OWNER/REPO] [--filed-issue-details-json PATH] [--lenient] [--ground-truth-verdict] [--since-date DATE] [--min-runs N] [--min-larch-version VERSION]
```

`--filed-issue-details-json PATH` is only accepted on the offline `analyze` subcommand. It loads a JSON object `{ "<issue_number>": { ...view fields... } }` to enrich fate scoring without live `gh` calls. By default, offline `analyze --json` performs no `gh issue view` calls; enrichment requires `--filed-issue-details-json` or a live `run` path.

The raw `gh` JSON dump is saved to `${TMPDIR:-/tmp}/<sanitized-repo>-issues.json` for follow-up reanalysis. The slug converts `/` to `-` and keeps only alnum, `-`, and `_`; dumps are intentionally user-private via `umask 077` and an atomic temp+mv write. The live coordinator contract is covered by `python/analyze_issues.py` and `python/test_analyze_issues.py`.

## Fate-adjusted OOS Scoring

The report includes a diagnostic `## High-risk OOS Backlog` section before fate-adjusted OOS scoring. It lists open `[OOS]` issues carrying `oos-correctness`, including correctness- and regression-tagged deferrals, sorted oldest first. It is read-only and does not mutate issues.

The report includes a diagnostic `## Fate-adjusted OOS Scoring` section after the reviewer/persona tables. It scans `larch-logs/{design,implement}/` for filed OOS evidence, joins filed issue numbers to the fetched issue dump, and reports provisional points, fate-adjusted points, docked counts, and fate buckets per reviewer. It does not mutate run logs, live voting scores, or reviewer ledgers.

Live runs may enrich only filed OOS candidates with targeted `gh issue view` calls so combined-away comments can be detected. Bulk `gh issue list` does not fetch comments; if newer optional list fields such as `stateReason` or `url` are unavailable, the fetch retries without them and marks the reduced data as degraded.

Implement-phase scoring depends on same-run joins between `oos-issues.ndjson` and nested `round-*/oos-accepted-*.md` files. Joins support namespaced and hash stable ids consistent with `oos_filer._stable_identifier`, round-qualified dedupe keys, cap-rollup expansion for explicit members and main-agent aggregate ids, fallback rollup expansion only when the unfiled candidate count exactly matches the parsed rollup count, legacy body citation fallback, and explicit filed issue references only. Arbitrary bare `#N` mentions are not filed-OOS evidence.

Design-phase scoring joins `OOS_FILE_MAP` rows to `oos-accepted-design.md` blocks when present. Combined-away detection relies on the targeted per-issue comment fetch for filed OOS issues only.

## Ground-truth Voter Calibration

The report appends `## Ground-truth Voter Calibration` after fate-adjusted OOS scoring. This diagnostic scans committed `larch-logs`, pins `panel_kind` per discovered classification TSV, and ingests rows through `classification_row_panel_inputs`, not `voter_agreement_rows_from_tsv`. Row prep retains raw TSV fields, compact flags, normalized voter votes, reviewer attribution, and the post-selection parsed header so OOS routing uses `(row, header)`.

The diagnostic excludes ineligible rows before realized-outcome work: neutral verdicts, main-agent-vote placeholders, and rows with fewer than two parseable voter cells. In-scope rows bind `panel_verdict` from authoritative prose. Design rows consult round-local `plan-review/round-N` accepted/rejected markdown first, fall back to run-root markdown only when round-local files are absent, and mark round-local/run-root disagreement weak.

OOS rows bind `oos_panel_verdict` from TSV or tally results. Implement JSONL `outcome=out_of_scope` is not accepted/rejected evidence. Only accepted OOS rows can receive decisive OOS fate buckets, and only docked fates count as realized contradiction. Rejected OOS panel rows, provisional OOS fates, ambiguous joins, and enrichment-degraded rows stay non-decisive.

Realized-outcome matching is conservative. It uses cleaned diagnostic path extraction, distinctive title tokens, run `manifest.json` `started_at` for cross-run ordering, and `round_num` for same-run ordering. Accepted findings become decisive only when a later matching issue or finding carries revert or regression language. Rejected findings become decisive only when a later issue or accepted finding strongly resurfaces the same concern.

Per-voter alignment is separate from panel self-agreement. It uses only `voter`, `vote`, and `missing` from `voter_agreement_row_from_panel`; it ignores `agree` and `disagree`. `realized_alignment_rate` is `aligned / (aligned + misaligned)` over decisive realized ballots only. Missing votes, `JUDGE_ERROR`, weak rows, timestamp-degraded matches, provisional OOS fates, and enrichment-degraded rows stay out of the denominator. The section is diagnostic only.

## Ground-truth Verdict Mode

`--ground-truth-verdict` is the capstone mode for token-allocation evidence. Defaults are `--since-date 2026-06-26` at midnight UTC, `--min-runs 150`, and `--min-larch-version 52.1.0`. `--since-date`, `--min-runs`, and `--min-larch-version` are ignored unless `--ground-truth-verdict` is set.

Verdict mode prints only the filtered ground-truth verdict report. It suppresses the legacy diagnostic `Corpus:` subsection, emits an explicit gate PASS/FAIL line aligned with the exit code, and exits non-zero when the corpus gate is unmet, enrichment is degraded, targeted OOS issue fetches fail, or calibration-incentive #5461 is not demonstrably shipped.

Qualifying runs are unique log-root-relative `run_dir` values with strict manifest `started_at`, not `updated_at`. Filed-OOS joins and accepted-evidence matching use log-root-relative `run_dir_key` values such as `implement/run-1` and `design/run-1`, not classifier `panel_kind` or basename `run_id` alone.

Calibration-incentive #5461 shipped detection consults bulk-loaded issues before live `gh issue view`. It requires a non-empty `closedByPullRequestsReferences` list and rejects bare `CLOSED` or `NOT_PLANNED`.

Do not ship token allocation until calibration-incentive #5461 is shipped and `docs/ground-truth-verdict.md` records a GO decision over an eligible post-`52.1.0` incentivized-era corpus.

## Implementation

Logic lives in the Python runtime modules. SKILL.md is a thin coordinator.

- `python/cli.py analyze-issues run`: top-level coordinator. Parses flags, detects the repo, chains the fetch and the analyzer.
- `python/cli.py analyze-issues fetch`: wraps the single `gh issue list` shell-out.
- `python/analyze_issues.py`: main analyzer (categories, coverage, growth, patterns, waste signatures, reviewer/persona effectiveness, fate-adjusted OOS scoring, ground-truth voter calibration, executive summary).
- `python/render_chart.py`: cumulative-growth ASCII chart helper imported by `python/analyze_issues.py`.
- `python/test_analyze_issues.py`: offline regression coverage for the coordinator, fetch, analyzer, and chart behavior.

## Anti-patterns

- Keep reviewer attribution regexes longest-first, with `codex` before `code`.
- Do not use Agent or Explore subagents for the analysis itself.
- Do not exclude `[OOS]` issues; they are workflow-driven-waste signal.
- Do not collapse duplicate titles at fetch time; duplicates are evidence.
