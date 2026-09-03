#!/usr/bin/env bash
set -euo pipefail
FILE=/Users/zhupanov/larch1/crates/larch-cli/src/audit_umbrella_commands.rs

# snapshot_exchanges: add canonical leaf GET before control
sed -i '' 's/response(200, &search),$/response(200, \&search),/' "$FILE"
sed -i '' '/response(200, &search),$/{ n; s/response(200, control),/response(200, leaf),\n            response(200, control),/; }' "$FILE"

# Fix snapshot_exchanges specifically - use line numbers after remote_parent insert
# Re-read and fix snapshot_exchanges with head/tail if sed failed

# bare_title_only: add leaf GET before control
sed -i '' '/remote_snapshot_accepts_a_bare_title_only_leaf/,/remote_snapshot_accepts_a_backlink_only_leaf/{
  s/response(200, &empty_search()),$/response(200, \&empty_search()),/
  /response(200, &empty_search()),/{ n; s/response(200, &control),/response(200, \&leaf),\n            response(200, \&control),/; }
}' "$FILE"

# backlink_only: add leaf GET before control  
sed -i '' '/remote_snapshot_accepts_a_backlink_only_leaf/,/remote_snapshot_merges_identical/{
  /response(200, &search_items(&\[&leaf\])),/{ n; s/response(200, &control),/response(200, \&leaf),\n            response(200, \&control),/; }
}' "$FILE"

# Update exchange counts 6 -> 7 for affected snapshot tests
sed -i '' '3423s/6/7/' "$FILE"
sed -i '' '3628s/6/7/' "$FILE"
sed -i '' '3661s/6/7/' "$FILE"
sed -i '' '3681s/6/7/' "$FILE"
sed -i '' '3781s/6/7/' "$FILE"

# Insert orphan_parent after remote_parent closing brace - line after remote_parent function
# Find line number of "    fn remote_leaf()" and insert before it
LINE=$(grep -n 'fn remote_leaf()' "$FILE" | head -1 | cut -d: -f1)
head -n $((LINE - 1)) "$FILE" > /Users/zhupanov/larch1/.tmp-part1.rs
cat /Users/zhupanov/larch1/.tmp-orphan-parent.txt >> /Users/zhupanov/larch1/.tmp-part1.rs
tail -n +"$LINE" "$FILE" >> /Users/zhupanov/larch1/.tmp-part1.rs
mv /Users/zhupanov/larch1/.tmp-part1.rs "$FILE"

# Insert new tests after remote_snapshot_accepts_a_backlink_only_leaf test (before merges test)
LINE=$(grep -n 'async fn remote_snapshot_merges_identical_title_and_body_search_copies' "$FILE" | head -1 | cut -d: -f1)
head -n $((LINE - 1)) "$FILE" > /Users/zhupanov/larch1/.tmp-part2.rs
cat /Users/zhupanov/larch1/.tmp-new-tests.txt >> /Users/zhupanov/larch1/.tmp-part2.rs
tail -n +"$LINE" "$FILE" >> /Users/zhupanov/larch1/.tmp-part2.rs
mv /Users/zhupanov/larch1/.tmp-part2.rs "$FILE"

# Replace pagination test
START=$(grep -n 'async fn remote_snapshot_filters_more_than_one_hundred_raw_search_hits' "$FILE" | head -1 | cut -d: -f1)
END=$(grep -n 'async fn remote_snapshot_refuses_incomplete_title_search_results' "$FILE" | head -1 | cut -d: -f1)
head -n $((START - 1)) "$FILE" > /Users/zhupanov/larch1/.tmp-part3.rs
cat /Users/zhupanov/larch1/.tmp-paginated-test.txt >> /Users/zhupanov/larch1/.tmp-part3.rs
tail -n +"$END" "$FILE" >> /Users/zhupanov/larch1/.tmp-part3.rs
mv /Users/zhupanov/larch1/.tmp-part3.rs "$FILE"

# Fix snapshot_exchanges if sed didn't work - manual line fix
sed -i '' '2798,2801s/response(200, &search),/response(200, \&search),/' "$FILE"
python3 /Users/zhupanov/larch1/.tmp-fix-snapshot-exchanges.py 2>/dev/null || true

echo done
