#!/usr/bin/env bash
# redact-tmpdir-paths.sh — rewrite larch session tmpdir literals.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LARCH_QUIET_DISABLE=1
export LARCH_QUIET_DISABLE
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
larch_quiet_init

sed -E \
    -e 's#(^|[^[:alnum:]_./-])/(private/)?tmp/(claude|larch)-(implement|design|review|research|fix-issue|issue)-[A-Za-z0-9_-]+#\1<TMPDIR>#g' \
    -e 's#(^|[^[:alnum:]_./-])/(private/)?var/folders/[^/]+/[^/]+/T/(claude|larch)-(implement|design|review|research|fix-issue|issue)-[A-Za-z0-9_-]+#\1<TMPDIR>#g' \
    -e 's#(^|[^[:alnum:]_./-])/([^/"\\[:space:]]+/)*larch/sessions/(claude|larch)-(implement|design|review|research|fix-issue|issue)-[A-Za-z0-9_-]+#\1<TMPDIR>#g' \
    -e 's#(\\n)/([^/"\\[:space:]]+/)*larch/sessions/(claude|larch)-(implement|design|review|research|fix-issue|issue)-[A-Za-z0-9_-]+#\1<TMPDIR>#g' \
    -e 's#(\\n)/(private/)?tmp/(claude|larch)-(implement|design|review|research|fix-issue|issue)-[A-Za-z0-9_-]+#\1<TMPDIR>#g' \
    -e 's#(\\n)/(private/)?var/folders/[^/]+/[^/]+/T/(claude|larch)-(implement|design|review|research|fix-issue|issue)-[A-Za-z0-9_-]+#\1<TMPDIR>#g' \
    -e 's#(^|[^[:alnum:]_./-])(/Users|/home)/[^/"[:space:]]+/[^/"[:space:]]+/#\1<OPERATOR_REPO_PATH>/#g' \
    -e 's#(\\n)(/Users|/home)/[^/"[:space:]]+/[^/"[:space:]]+/#\1<OPERATOR_REPO_PATH>/#g'
