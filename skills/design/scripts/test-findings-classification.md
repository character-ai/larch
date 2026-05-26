# test-findings-classification.sh

Offline regression harness for `findings-classification.tsv` and
`scripts/parse-judge-vote-and-rating.sh`.

Fixtures are created under a per-run `mktemp -d` directory. Each case writes a
small ballot plus voter files and invokes `skills/design/scripts/tally-plan-review.sh`
with explicit `--findings-classification-out` paths so overwrite behavior and
bad-argv no-write behavior are observable.

The harness verifies:

- complete three-judge rating rows, including `vN_tool`;
- lowercase-only parser axes, position-agnostic axis order, duplicate
  last-line-wins behavior, and `--` delimiter rationale scoping;
- partial rows where a missing axis forces `vN_uncertain=true`;
- missing judges with preserved empty vN cells and canonical Cursor placement;
- explicit `--voter` slot labels overriding misleading basenames;
- 0-judge `MainAgent` fallback TSV rows (`voting_result=rejected`) and
  header-only empty-ballot output;
- numeric `FINDING_*` rows before numeric `OOS_*` rows;
- waterfall fallback identity where a Claude runtime voter occupies a non-v1
  position;
- exact diagnostics for MainAgent misuse, `--voter`/`--voter-files` mutual
  exclusion, invalid slots, and legacy `--voter-files` deprecation;
- parser usage / unreadable-file exit diagnostics;
- every data row has exactly 21 tab-separated fields.

Makefile target:

```bash
make test-findings-classification
```
