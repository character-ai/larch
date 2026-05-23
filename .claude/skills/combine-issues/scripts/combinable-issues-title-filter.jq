# Title filter for open issues eligible for /combine-issues workflows.
# Keep in sync with fetch-combinable-issues.sh (single source via jq -f).
# Excludes managed busy prefixes (including legacy [IN PROGRESS] / [PLANNED]).
# [DESIGNED] is intentionally NOT excluded.
[
  .[] |
  select(
    (.title | test("^\\[(DESIGNING|IMPLEMENTING|STALLED|DONE|PLANNED|IN PROGRESS)\\] ") | not) and
    (.title | test("^\\[LOCKED\\]") | not)
  )
]
