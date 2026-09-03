#!/usr/bin/env bash
set -euo pipefail
FILE=/Users/zhupanov/larch1/crates/larch-cli/src/audit_umbrella_commands.rs
REPL=/Users/zhupanov/larch1/.tmp-fetch-fn.txt
head -n 693 "$FILE" > /Users/zhupanov/larch1/.tmp-audit-new.rs
cat "$REPL" >> /Users/zhupanov/larch1/.tmp-audit-new.rs
tail -n +718 "$FILE" >> /Users/zhupanov/larch1/.tmp-audit-new.rs
sed -i '' 's/fetch_missing_issue(/fetch_canonical_issue(/g' /Users/zhupanov/larch1/.tmp-audit-new.rs
# revert accidental rename in re-read function
sed -i '' '1115s/let canonical = service/let issue = service/' /Users/zhupanov/larch1/.tmp-audit-new.rs
mv /Users/zhupanov/larch1/.tmp-audit-new.rs "$FILE"
