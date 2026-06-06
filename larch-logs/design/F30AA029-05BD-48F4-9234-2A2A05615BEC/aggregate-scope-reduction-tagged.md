### FINDING_8:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:308
- **Concern**: [SCOPE-REDUCTION] Item 1 wrapper self-derive does not fix the initial Step 0 invoke path when CLAUDE_PLUGIN_ROOT is unset. Scenario: On first entry IMPLEMENT_TMPDIR and plugin-root.env do not exist so pre-bootstrap guards are no-ops; ${CLAUDE_PLUGIN_ROOT}/scripts/implement-bootstrap-invoke.sh expands to /scripts/implement-bootstrap-invoke.sh and fails before wrapper self-derive runs — the exact #3448 item 1 symptom
- **Proposed resolution**: Add a pre-invoke CLAUDE_PLUGIN_ROOT default in the Step 0 initial fence (issue alternate: explicit ${CLAUDE_PLUGIN_ROOT:-<plugin-root>} line) or invoke implement-bootstrap-invoke.sh via a literal absolute script path; wrapper-only export is necessary but not sufficient

### FINDING_14:
- **Reviewer(s)**: Cursor-dyn-scope-guard
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/implement/SKILL.md:42-59
- **Concern**: [SCOPE-REDUCTION] Step 0 parent-shell post-invoke rehydration exceeds the approved outline (item 1 was wrapper-only; approved Surfaces list only `implement-bootstrap-invoke.sh` and explicitly avoided Step 0 SKILL edits). Scenario: The plan adds an 8-line post-invoke block to both initial and dirty-tree resume Step 0 fences plus acceptance criteria, beyond the three scoped DX fixes and contradicting plan Summary line 7 ("No Step 0 SKILL fallback")
- **Proposed resolution**: Drop the Step 0 fence edits; keep item 1 in `scripts/implement-bootstrap-invoke.sh` only. If the parent shell still needs `CLAUDE_PLUGIN_ROOT` for `parse-bootstrap-routing-envelope.sh`, use the issue's cheaper one-line pre-invoke template export at the fence top, or emit `CLAUDE_PLUGIN_ROOT=` on wrapper stdout and add a single parent parse line—not dual-fence post-invoke sourcing

### FINDING_15:
- **Reviewer(s)**: Codex-dyn-scope-guard
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/implement/SKILL.md:306-318,364-388
- **Concern**: [SCOPE-REDUCTION] Step 0 parent-shell rehydration exceeds the approved SKILL.md surface and the proposed literal block is malformed. Scenario: The approved scope limits SKILL.md edits to the Step 5 Scripted review loop, but the plan adds a new Step 0 parent-shell contract in both initial and resume fences; if retained, the shown block also lacks the outer closing fi before export CLAUDE_PLUGIN_ROOT, which would break the Step 0 fence before routing parse
- **Proposed resolution**: Delete the Step 0 parent-shell rehydration subsection plus related acceptance/failure-mode bullets and keep Item 1 in scripts/implement-bootstrap-invoke.sh; if parent rehydration is separately approved, add the missing fi and a targeted Step 0 test
