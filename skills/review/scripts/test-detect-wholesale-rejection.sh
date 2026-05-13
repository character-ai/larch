#!/usr/bin/env bash
# Regression harness for detect-wholesale-rejection.sh.

set -euo pipefail

DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
grep -Fq 'TERMINATE_EARLY=true' <("$DIR/detect-wholesale-rejection.sh" --accepted-count 0)
grep -Fq 'TERMINATE_EARLY=false' <("$DIR/detect-wholesale-rejection.sh" --accepted-count 1)
echo "All assertions passed."
