### FINDING_1:
- **Reviewer(s)**: Cursor-Arch, Cursor-Edge, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-race-window-audit
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-design-log-publish.sh:74-76
- **Concern**: Plan-review ancestor harness layout uses `plan-review/round-1/sub/...`. Scenario: `rel` like `round-1/sub/file` fails the plan-review allowlist (`unexpected path under plan-review`) before the new ancestor guard runs, so the case never exercises `design_publish_ancestor_within_root` and the required `plan-review ancestor became a symlink` substring assertion will not match
- **Proposed resolution**: Use an allowlisted file directly under `round-1` (e.g. `findings-classification.tsv`) and set `ANCESTOR_RACE_PARENT` to the physical `round-1` directory (same pattern as render-cache `sub/`, but without a disallowed extra path segment)

### FINDING_2:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-design-log-publish.sh:70-76
- **Concern**: Ancestor cases require a distinct `larch_err` substring but the plan does not say how to capture stderr. Scenario: Sibling blocks redirect with `2>/dev/null` and only assert `PUBLISH_OK=false` on stdout; the ancestor message would be dropped and the anti-false-green substring check would not run
- **Proposed resolution**: Capture publish with merged `2>&1` (or stderr kept) and assert the ancestor-specific substring in that capture; document this in the test `.md` block

### FINDING_3:
- **Reviewer(s)**: Cursor-dyn-race-window-audit
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: plan.txt:70-76 scripts/test-design-log-publish.sh:972-975
- **Concern**: Ancestor cases require ancestor-specific `larch_err` on stderr but the plan does not specify stderr capture. Scenario: Existing leaf-race neighbors wrap publish with `2>/dev/null` and only grep stdout for `PUBLISH_OK=false`, so the planned substring assertions on ancestor messages would be dropped and could false-green on stdout-only failure
- **Proposed resolution**: Capture merged output (`2>&1`) or stderr explicitly when asserting `... ancestor became a symlink before staging`; document that requirement in `scripts/test-design-log-publish.md`
