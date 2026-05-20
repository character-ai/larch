# test-collect-findings.sh Contract

Regression harness for `skills/review/scripts/collect-findings.sh`.

It covers description-mode dual-list parsing, OOS extraction, `NO_ISSUES_FOUND`, inline TSV extraction for external reviewer outputs (silent collection — no tsv-fallback execution-issues noise), clean dirty-tree sidecar handling, a stdout size cap assertion (≤2 KB), and the `## preamble` skip-state fix: fixtures with a `## Commits since merge-base` section assert commit-hash bullets are not promoted to `FINDING_N` entries and that parsing recovers on the next non-preamble `##` heading such as `## Findings`.

Run with `bash skills/review/scripts/test-collect-findings.sh` or `make test-collect-findings`.
