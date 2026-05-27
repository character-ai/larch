# read-design-classification.sh

Reads `design_classification` from `$DESIGN_TMPDIR/run-params.json` or from an explicit path argument.

The script prints `SIMPLE` or `HARD` on stdout. It tries `python3`, then `jq`, then literal grep fallbacks. If the file is missing, unreadable, or does not contain a valid v2 classification, it prints a warning to stderr and returns `HARD` on stdout.

Regression coverage: `bash scripts/test-read-design-classification.sh`.
