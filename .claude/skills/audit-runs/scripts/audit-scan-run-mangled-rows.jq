# Shared filter: plan-review accepted rows whose category is non-empty but not canonical.
# Emits one .id per matching object (streamed JSONL input). Used by oos-category-mangle and category-stats.
def catstr:
  (.category // "" |
    if type == "string" then .
    elif type == "number" or type == "boolean" then tostring
    else "" end);
select(
  .phase == "plan-review" and
  .outcome == "accepted" and
  (catstr != "") and
  (catstr | test("^(code-quality|risk-integration|correctness|architecture|security)$") | not)
) | .id
