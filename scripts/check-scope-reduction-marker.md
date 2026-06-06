# check-scope-reduction-marker.sh

Detects the narrow plan-review scope-cut marker. It exits 0 only when a finding heading, `what:` line, or `- **Concern**:` line starts with `[SCOPE-REDUCTION]` after removing fenced code, inline code spans, and one leading severity bracket such as `[important]`.

Non-leading mentions, fenced-only mentions, and inline-code-only mentions are false. `scripts/lib-vote-tally.sh`, `/design` plan-review dedup, and plan-mode aggregation use this helper as the canonical detector.

The implementation uses one shared Python detector for stdin and `--file`; `python3 -c` receives `-` or the path as argv so caller stdin remains available and the two modes cannot drift.

Harness: `make test-check-scope-reduction-marker`.
