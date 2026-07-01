### [Plan Review] FINDING_1

### FINDING_1: `skills/design/SKILL.md` still hardcodes cap-5 and six-dynamic Step 3 prose but is omitted from the plan
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Requirements
- **Severity**: important
- **Concern**: The active `/design` orchestrator loads `skills/design/SKILL.md` at Step 3 and Gate C. Lines 381 and 548 still require "up to 6 dynamic" slots with scout cap 3 and a flattened Gate C cap of 5. After Python moves to cap 2 and one dynamic pair, the skill can still instruct the old topology and re-run limits, wasting operator turns and contradicting acceptance.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add `### UPDATED: skills/design/SKILL.md`: replace Step 3 panel text with at most one dynamic archetype pair (Cursor+Codex), cap-2 review rounds, and no reviewer fallback; update Gate C prose to flattened cap 2; drop round-5 rerun language.
  - From Cursor-Innovation: Add ### UPDATED entries for skills/design/references/flags.md skills/design/references/approval-gates.md and skills/design/SKILL.md. Set Gate C re-entry cap and Step 3 dynamic-slot prose to cap 2 and at most one dynamic pair. Match the #3662 uniform-surface pattern.
  - From Cursor-Requirements: Add `### UPDATED: skills/design/SKILL.md`: cap-2 Step 3 dynamic topology (at most one dynamic pair), Gate C cap-aware prompt tied to `ROUND_CAP`/review-round-count (not literal 5), and remove stale 6-slot/3-scout language


### [Plan Review] FINDING_2

### FINDING_2: `flags.md` and `approval-gates.md` still pin Gate C review-run cap at 5 and are omitted from the plan
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Requirements
- **Severity**: important
- **Concern**: `skills/design/references/approval-gates.md` (lines 15, 200) and `skills/design/references/flags.md` (line 57) are normative Gate C authorities. Both still say cap 5. When `ROUND_CAP` becomes 2 in Python, operators following these references can still be offered **Re-run review panel** after the real cap is exhausted, contradicting acceptance that cap = 2 is honored across `/design` plan review.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: `approval-gates.md` (lines 15, 200) and `flags.md` (line 57) are normative for Gate C. Both still say cap 5. `ROUND_CAP` becomes 2 in Python, but operators following these references can offer extra "Re-run review panel" turns and misread when the cap is reached. Add `### UPDATED:` entries for both files: change Gate C review-run cap prose from 5 to 2 and align re-run eligibility with `ROUND_CAP=2`. Optionally extend `skills/design/scripts/test-step3-review-cap.sh` to grep for cap-2 literals.
  - From Cursor-Innovation: Add ### UPDATED entries for skills/design/references/flags.md skills/design/references/approval-gates.md and skills/design/SKILL.md. Set Gate C re-entry cap and Step 3 dynamic-slot prose to cap 2 and at most one dynamic pair. Match the #3662 uniform-surface pattern.
  - From Cursor-Requirements: Add `### UPDATED: skills/design/references/approval-gates.md` (and cross-refs in design SKILL): replace cap-of-5 Gate C re-run gating with cap 2 aligned to `review-round-count.txt` / `ROUND_CAP`


### [Plan Review] FINDING_4

### FINDING_4: Plan-review dispatch loads every scout archetype with no consumer-side max-1 clamp
- **Reviewer(s)**: Cursor-Arch, Cursor-Requirements
- **Severity**: important
- **Concern**: The plan caps scout producers (`plan_scout.py`, `_drafter.py`) at one archetype but does not clamp `python/larch/review/plan_review_panel.py` `_load_dynamic_rows()`, which reads all `scout-plan-manifest.json` entries. A resume or stale manifest with two or more archetypes can still launch more than one dynamic Cursor+Codex pair, violating "at most one dynamic pair" even after producer clamps land.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In `plan_review_panel.py`, clamp dynamic rows to one archetype at dispatch (slice after load or call `filter-manifest --max-archetypes 1`). Add a panel test that a two-archetype manifest dispatches only one pair.
  - From Cursor-Requirements: Add a `plan_review_panel.py` change: slice or reject manifests to one archetype (shared constant with plan scout) before `_dynamic_slot_rows()`, plus a panel test that a two-archetype manifest dispatches only one pair


### [Plan Review] FINDING_5

### FINDING_5: Missing all-slots-dropped handling for the no-fallback review path
- **Reviewer(s)**: Codex-Innovation
- **Severity**: blocking
- **Concern**: The plan only adds `tool-absent` excusal for one-vendor-down panels. When both Cursor and Codex are unavailable, the existing coverage gate in `python/larch/review/review_core_body.py` (lines 855–865) still reaches "no successful launched reviewer output" and returns `panel-failed` instead of reusing the degraded or prune-to-empty completion path the edge-case spec requires.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Add an explicit zero-output or `ALL_SLOTS_DROPPED=true` branch before the coverage gate so a fully absent panel degrades or converges without Claude backfill.


