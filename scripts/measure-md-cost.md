# measure-md-cost.sh

Measures tracked markdown files and writes
`larch-logs/measure-md-cost/<date>.tsv`.

The TSV columns are `path`, `tier`, `bytes`, `tokens`, `lines`, and
`h2_count`. Token counts use `tiktoken` with `cl100k_base`. The script has no
required arguments and overwrites the same dated output atomically, so repeated
runs for the same date are idempotent.

Tier labels distinguish always-imported Claude files, runtime and dev
`SKILL.md` files, `.claude/rules/*.md` system-reminder rules, skill references,
script docs, general docs, committed run logs, and other markdown.

Primary caller: humans auditing prompt/load cost for issue #2241. The script is
observability-only and is not part of runtime control flow.
