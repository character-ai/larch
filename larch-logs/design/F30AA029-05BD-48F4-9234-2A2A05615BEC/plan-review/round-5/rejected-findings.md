### [Plan Review] FINDING_2

### FINDING_2: Step 5 fence merge leaves plugin-root guard count harness stale
- **Reviewer(s)**: Codex-Arch, Cursor-Edge, Cursor-Innovation, Codex-dyn-harness-wiring
- **Severity**: important
- **Concern**: Merging Step 5 fences removes one canonical plugin-root source guard, but the timing/rehydration harness and documentation still expect the previous guard count, causing `make test-implement-timing-rehydration` to fail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Update the harness and sibling doc expected source-guard count to 41 as part of the Step 5 merge, or keep the second guarded fence if the count must stay 42
  - From Cursor-Edge: Add plan step to bump expected plugin_root_source_count to 41 and sync SKILL.md line 115 inventory if kept
  - From Cursor-Innovation: Update the expected plugin_root_source_count (and document why) or retain a canonical guard so the count stays 42; prefer reusing the canonical one-liner in Step 0 post-invoke instead of a bespoke grep-only block
  - From Codex-dyn-harness-wiring: Update scripts/test-implement-timing-rehydration.sh to expect the new guard count, or keep two Step 5 fences if that invariant is meant to remain unchanged


### [Plan Review] FINDING_4

### FINDING_4: Banner archetype cap can display a value the launcher ignores
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: nit
- **Concern**: The Step 5 banner can report `dynamic_archetypes_cap` from ambient `LARCH_DYNAMIC_ARCHETYPES_MAX`, while `run-step5-review.sh` reads only session-env plus its default, making the banner misleading.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Accept as cosmetic-only or align banner precedence with run-step5-review.sh (session-env + default 6) to avoid misleading operator copy


### [Plan Review] FINDING_5

### FINDING_5: Step 0 post-invoke block may not export `IMPLEMENT_TMPDIR`
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: nit
- **Concern**: The post-invoke block re-sources `plugin-root.env` but does not export `IMPLEMENT_TMPDIR` parsed from `_inv_out` before routing parse, so later same-turn Bash blocks may not see the tmpdir value.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: After parsing IMPLEMENT_TMPDIR from _inv_out add IMPLEMENT_TMPDIR="$_inv_tmpdir" and export IMPLEMENT_TMPDIR before sourcing parse-bootstrap-routing-envelope.sh


### [Plan Review] FINDING_6

### FINDING_6: Step 5 fence merge leaves tmpdir assign/export harness stale
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: Merging Step 5 telemetry into the banner fence may reduce the `IMPLEMENT_TMPDIR` assign/export count while the timing/rehydration harness still expects the old coupling invariant.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add UPDATED scripts/test-implement-timing-rehydration.sh (and sibling .md if needed) to decrement expected tmpdir assign/export coupling from 12 to 11 after the Step 5 fence merge


### [Plan Review] FINDING_7

### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:308
- **Concern**: [SCOPE-REDUCTION] Item 1 wrapper self-derive does not fix the initial Step 0 invoke path when CLAUDE_PLUGIN_ROOT is unset. Scenario: On first entry IMPLEMENT_TMPDIR and plugin-root.env do not exist so pre-bootstrap guards are no-ops; ${CLAUDE_PLUGIN_ROOT}/scripts/implement-bootstrap-invoke.sh expands to /scripts/implement-bootstrap-invoke.sh and fails before wrapper self-derive runs — the exact #3448 item 1 symptom
- **Proposed resolution**: Add a pre-invoke CLAUDE_PLUGIN_ROOT default in the Step 0 initial fence (issue alternate: explicit ${CLAUDE_PLUGIN_ROOT:-<plugin-root>} line) or invoke implement-bootstrap-invoke.sh via a literal absolute script path; wrapper-only export is necessary but not sufficient


### [Plan Review] FINDING_8

### FINDING_8:
- **Reviewer(s)**: Cursor-dyn-scope-guard
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/implement/SKILL.md:42-59
- **Concern**: [SCOPE-REDUCTION] Step 0 parent-shell post-invoke rehydration exceeds the approved outline (item 1 was wrapper-only; approved Surfaces list only `implement-bootstrap-invoke.sh` and explicitly avoided Step 0 SKILL edits). Scenario: The plan adds an 8-line post-invoke block to both initial and dirty-tree resume Step 0 fences plus acceptance criteria, beyond the three scoped DX fixes and contradicting plan Summary line 7 ("No Step 0 SKILL fallback")
- **Proposed resolution**: Drop the Step 0 fence edits; keep item 1 in `scripts/implement-bootstrap-invoke.sh` only. If the parent shell still needs `CLAUDE_PLUGIN_ROOT` for `parse-bootstrap-routing-envelope.sh`, use the issue's cheaper one-line pre-invoke template export at the fence top, or emit `CLAUDE_PLUGIN_ROOT=` on wrapper stdout and add a single parent parse line—not dual-fence post-invoke sourcing


### [Plan Review] FINDING_9

### FINDING_9:
- **Reviewer(s)**: Codex-dyn-scope-guard
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/implement/SKILL.md:306-318,364-388
- **Concern**: [SCOPE-REDUCTION] Step 0 parent-shell rehydration exceeds the approved SKILL.md surface and the proposed literal block is malformed. Scenario: The approved scope limits SKILL.md edits to the Step 5 Scripted review loop, but the plan adds a new Step 0 parent-shell contract in both initial and resume fences; if retained, the shown block also lacks the outer closing fi before export CLAUDE_PLUGIN_ROOT, which would break the Step 0 fence before routing parse
- **Proposed resolution**: Delete the Step 0 parent-shell rehydration subsection plus related acceptance/failure-mode bullets and keep Item 1 in scripts/implement-bootstrap-invoke.sh; if parent rehydration is separately approved, add the missing fi and a targeted Step 0 test

