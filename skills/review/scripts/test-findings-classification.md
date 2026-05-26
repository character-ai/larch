# test-findings-classification.sh

Offline regression harness for code-review `findings-classification.tsv`.

It covers nested `/implement` round output, standalone `/review --diff`
per-round filenames, OOS ballot IDs, lenient missing-rating handling,
0-judge and empty-ballot paths, review log batch publishing, implement
`write-round` publishing, and parser/vote parity.

Run through:

```bash
bash skills/review/scripts/test-findings-classification.sh
```
