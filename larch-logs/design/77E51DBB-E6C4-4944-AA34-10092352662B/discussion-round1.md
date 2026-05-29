## Decision 1: Trailer contract is additive and backward-compatible
- **Question**: How should the plan declare the added/deleted split given `diff_lines:` is consumed across ~41 files?
- **Resolution**: Add OPTIONAL `diff_added: <N>` / `diff_deleted: <N>` trailers. Keep `diff_lines: <N>` required and informational. `emit-plan.sh` and `diff-lines.txt` stay unchanged. The gate keys on `diff_added` when present and falls back to current `diff_lines` behavior when absent.
- **Source**: user (Step 1c Q2)

## Decision 2: Hard diff trigger keys on additions; deletions exempt
- **Question**: What should fire the non-downgradeable Split/Cancel hard diff trigger?
- **Resolution**: Key the hard diff trigger on estimated ADDED lines only. Deletions never trip it — arbitrary-size rip-outs are allowed (no deletion cap, not even advisory). `#3118`'s ~4700-line deletion plan must no longer trip.
- **Source**: user (Step 1c Q1)

## Decision 3: Mechanical churn downgrades to soft advisory via self-declared trailer
- **Question**: How should huge-but-trivial mechanical churn be handled, and should the hard prompt gain an override?
- **Resolution**: Optional `mechanical_churn: true` trailer (designer-set) downgrades the diff trigger to a SOFT advisory breadcrumb (no Split/Cancel). The hard prompt stays non-downgradeable otherwise — no new Continue option.
- **Source**: user (Step 1c Q3)

## Decision 4: Additions hard threshold = 2000
- **Question**: What additions threshold should trip the hard trigger?
- **Resolution**: Hard diff trigger fires on `diff_added > 2000` (strict `>`). Legacy fallback path (no `diff_added`) keeps the current `diff_lines > 1500`.
- **Source**: user (Round 1 Q1)

## Decision 5: plan-body-lines > 800 stays unchanged (out of scope)
- **Question**: Is the separate plan-body-lines > 800 hard trigger in scope to change?
- **Resolution**: Out of scope. Leave the `plan_lines > 800` hard signal exactly as-is. This issue targets the diff/churn signal only. `mechanical_churn` and deletions affect only the diff trigger, not plan-body-lines.
- **Source**: user (Round 1 Q2)

## Decision 6: Backward compatibility is a hard constraint
- **Question**: Must legacy plans (with only the `diff_lines:` trailer) keep working?
- **Resolution**: Yes. When `diff_added` is absent, `check-plan-size.sh` must reproduce today's behavior exactly (`diff_lines > 1500` → `diff-lines` reason). The `diff_lines:` trailer and `diff-lines.txt` contract must not break for the ~41 existing consumers.
- **Source**: codebase (consumer-surface analysis)
