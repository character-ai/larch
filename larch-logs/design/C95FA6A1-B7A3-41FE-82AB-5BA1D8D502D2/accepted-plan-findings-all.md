### FINDING_3: Update prose-pinning assertions
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: Existing tests still pin long prose substrings that the plan intends to delete from scaffold text, so compression will cause avoidable failures unless those assertions are updated in the same pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In the same test-file update, replace long archetype prose substring asserts with short lens-identify checks plus the new frozen-grammar assertions, or delete redundant checks already covered by the inlined rubric
  - From Cursor-Pragmatic: Add an explicit Files/testing step to update or replace those prose-specific assertions in the same test_rendering.py pass (or constrain compression to text those tests do not pin)
  - From Cursor-Requirements: Add an explicit test_rendering.py step: relax or replace prose-substring assertions with the new frozen-grammar checks; keep only anchors the plan marks byte-identical


### FINDING_6:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/larch/rendering/rendering.py:856-862
- **Concern**: [SCOPE-REDUCTION] Shared oos_proposal_instruction() couples implement compression to design plan-review output. Scenario: Editing oos_proposal_instruction() to DRY specialist and dynamic text also changes render_plan_review_main scaffold even though the plan excludes design plan-review specialist builders; acceptance metrics and review surfaces may shift outside issue scope
- **Proposed resolution**: Either name oos_proposal_instruction() as an intentional cross-surface compress target with plan-review byte impact noted in re-measurement, or keep plan-review text stable by compressing only implement-scoped strings and leaving the shared helper unchanged

### FINDING_5: Keep the ballot-path pointer line intact
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: blocking
- **Concern**: Voter scaffold compression can remove the exact `Read the ballot from this path` substring, which the implement and design voter dispatch paths require before they will proceed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add `Read the ballot from this path` to the rendering.py preserve contract and to the new frozen-grammar tests in `python/tests/rendering/test_rendering.py` (or keep the full line byte-stable).


### FINDING_7:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/larch/rendering/rendering.py:904-920
- **Concern**: [SCOPE-REDUCTION] `_render_specialist_text` is listed as a trim target without scoping to generated scaffold only. Scenario: That function prepends the full `agents/*.md` body via `_load_specialist_body`, which the plan excludes. Treating the whole function as editable invites Python-side truncation of static agent prose or scope creep into out-of-scope agent files
- **Proposed resolution**: Limit rendering.py trimming to `_specialist_tagging`, the optional `--competition-notice` block, and other inline generated scaffold; leave `_load_specialist_body` output byte-for-byte from `agents/*.md`


