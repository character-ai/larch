#!/usr/bin/env bash
# redact-tmpdir-paths.sh — rewrite larch session tmpdir literals.

set -euo pipefail

sed -E \
    -e 's#(^|[^[:alnum:]_./-])/(private/)?tmp/(claude|larch)-(implement|design|review|research|fix-issue|issue)-[A-Za-z0-9_-]+#\1<TMPDIR>#g' \
    -e 's#(^|[^[:alnum:]_./-])/(private/)?var/folders/[^/]+/[^/]+/T/(claude|larch)-(implement|design|review|research|fix-issue|issue)-[A-Za-z0-9_-]+#\1<TMPDIR>#g' \
    -e 's#[^[:space:]]*/larch/sessions/(claude|larch)-(implement|design|review|research|fix-issue|issue)-[A-Za-z0-9_-]+#<TMPDIR>#g'
