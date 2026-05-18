# test-collect-findings.sh Contract

Regression harness for `skills/review/scripts/collect-findings.sh`.

It covers description-mode dual-list parsing, OOS extraction, `NO_ISSUES_FOUND`, inline TSV extraction for external reviewer outputs (silent collection — no tsv-fallback execution-issues noise), clean dirty-tree sidecar handling, and a stdout size cap assertion (≤2 KB).

Run with `bash skills/review/scripts/test-collect-findings.sh` or `make test-collect-findings`.
