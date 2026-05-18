# measure-ngram-duplication.sh

Finds repeated markdown shingles in prompt-loaded files and writes
`larch-logs/measure-ngram-duplication/<date>.txt`.

The scanned corpus is `CLAUDE.md`, the direct `@...md` imports listed in
`CLAUDE.md`, every runtime `skills/*/SKILL.md`, and every dev
`.claude/skills/*/SKILL.md`. The output contains the top repeated 6-word
shingles that appear in at least 3 files, ranked by
`occurrences * shingle_length`. Environment variables may tune the defaults:
`LARCH_MEASURE_NGRAM_SIZE`, `LARCH_MEASURE_NGRAM_MIN_FILES`, and
`LARCH_MEASURE_NGRAM_LIMIT`.

The script has no required arguments and atomically replaces the dated output on
each run. It is observability-only.
