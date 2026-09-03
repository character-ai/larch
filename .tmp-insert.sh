#!/usr/bin/env bash
set -euo pipefail
FILE=/Users/zhupanov/larch1/crates/larch-cli/src/audit_umbrella_commands.rs
LINE=709
while IFS= read -r l || [ -n "$l" ]; do
  sed -i '' "${LINE}a\\
${l}" "$FILE"
  LINE=$((LINE + 1))
done < /Users/zhupanov/larch1/.tmp-insert-lines.txt
