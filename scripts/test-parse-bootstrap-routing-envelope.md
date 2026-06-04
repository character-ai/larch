# test-parse-bootstrap-routing-envelope.sh

Regression harness for `scripts/parse-bootstrap-routing-envelope.sh`.

It sources the parser under `set -euo pipefail` after a file-first `bootstrap-routing.env` pass has already populated routing keys, then lets the stdout fallback loop see duplicate values. Both default mode and `--preserve-coder` must return successfully.

Run through `make test-parse-bootstrap-routing-envelope`; the Makefile also includes it in the harness shards.
