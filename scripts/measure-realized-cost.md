# measure-realized-cost.sh

Estimates realized `SKILL.md` prompt load from committed run logs and writes
`larch-logs/measure-realized-cost/<date>.tsv`.

The script scans `larch-logs/*/*/manifest.json` and matching
`timing-report.json` / `timing-report.md` files. Timing reports identify which
skills appeared in a run; manifests provide issue numbers when available for the
`issues_observed` diagnostic column. For each observed skill, the script counts
tokens in `skills/<skill>/SKILL.md` or `.claude/skills/<skill>/SKILL.md` with
`tiktoken` `cl100k_base`, then emits `realized_tokens = invocations *
tokens_per_invocation`.

The output columns are `skill`, `invocations`, `issues_observed`,
`tokens_per_invocation`, and `realized_tokens`. The script has no required
arguments and atomically replaces the dated output on each run.
