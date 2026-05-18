# measure-references-heatmap.sh

Counts markdown `Read` tool calls in committed session transcripts and writes
`larch-logs/measure-references-heatmap/<date>.tsv`.

The script parses `larch-logs/*/*/session-transcript.jsonl`, extracts assistant
`tool_use` records where `name == "Read"` and `input.file_path` ends with
`.md`, normalizes local plugin-cache paths back to repo-relative paths when
possible, and ranks files by observed read count. The output columns are
`references_path`, `reads_observed`, and `bytes`; `bytes` is `0` when the
normalized path does not exist in the current checkout.

The script has no required arguments and atomically replaces the dated output on
each run. It is a post-hoc audit helper, not runtime control flow.
