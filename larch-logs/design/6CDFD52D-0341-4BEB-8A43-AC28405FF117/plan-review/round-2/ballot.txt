Verifying the cited locations so merged findings match the code.
Aggregated output (2 findings after merging input FINDING_2 and FINDING_3; input FINDING_1 stays separate):

### FINDING_1: Plan-review ancestor harness uses disallowed path before ancestor guard
- **Reviewer(s)**: Cursor-Arch, Cursor-Edge, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-race-window-audit
- **Severity**: important
- **Concern**: The plan-review ancestor harness is laid out as `plan-review/round-1/sub/...`. If `rel` is something like `round-1/sub/file`, publish fails the plan-review allowlist (`unexpected path under plan-review`) before the new ancestor guard runs, so the case never exercises `design_publish_ancestor_within_root` and the required `plan-review ancestor became a symlink` substring assertion will not match.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch, Cursor-Edge, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-race-window-audit: Use an allowlisted file directly under `round-1` (e.g. `findings-classification.tsv`) and set `ANCESTOR_RACE_PARENT` to the physical `round-1` directory (same pattern as render-cache `sub/`, but without a disallowed extra path segment)

### FINDING_2: Ancestor race cases need stderr capture; `2>/dev/null` drops ancestor `larch_err`
- **Reviewer(s)**: Cursor-Pragmatic, Cursor-dyn-race-window-audit
- **Severity**: important
- **Concern**: Ancestor race cases require an ancestor-specific `larch_err` substring on stderr, but the plan does not specify how to capture stderr. Neighboring leaf-race blocks redirect with `2>/dev/null` and only assert `PUBLISH_OK=false` on stdout, so ancestor messages would be dropped and substring checks on ancestor errors would not run, allowing false-green passes on stdout-only failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Capture publish with merged `2>&1` (or stderr kept) and assert the ancestor-specific substring in that capture; document this in the test `.md` block
  - From Cursor-dyn-race-window-audit: Capture merged output (`2>&1`) or stderr explicitly when asserting `... ancestor became a symlink before staging`; document that requirement in `scripts/test-design-log-publish.md`

**Merge notes**: Input FINDING_2 and FINDING_3 describe the same stderr-capture / false-green risk and were combined into `FINDING_2` above. Input FINDING_1 is a separate correctness issue (allowlist vs ancestor guard ordering) and remains `FINDING_1`. No `LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED` line — structured findings are present.
