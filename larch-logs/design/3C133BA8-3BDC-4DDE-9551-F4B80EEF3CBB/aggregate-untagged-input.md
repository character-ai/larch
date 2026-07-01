### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:381,548
- **Concern**: `/design` SKILL.md still pins cap-5 and six-dynamic Step 3 prose but is omitted from the plan. Scenario: The active `/design` orchestrator loads `skills/design/SKILL.md` at Step 3 and Gate C. Lines 381 and 548 still require "up to 6 dynamic" slots with scout cap 3 and a flattened Gate C cap of 5. Python can move to cap 2 and one dynamic pair while the skill keeps launching the old topology and re-run limits.
- **Proposed resolution**: Add `### UPDATED: skills/design/SKILL.md`: replace Step 3 panel text with at most one dynamic archetype pair (Cursor+Codex), cap-2 review rounds, and no reviewer fallback; update Gate C prose to flattened cap 2; drop round-5 rerun language.

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/references/approval-gates.md:15,200
- **Concern**: skills/design/references/flags.md:57. Scenario: Gate C authority files still hardcode review-run cap 5 and are not in the plan
- **Proposed resolution**: `approval-gates.md` (lines 15, 200) and `flags.md` (line 57) are normative for Gate C. Both still say cap 5. `ROUND_CAP` becomes 2 in Python, but operators following these references can offer extra "Re-run review panel" turns and misread when the cap is reached. Add `### UPDATED:` entries for both files: change Gate C review-run cap prose from 5 to 2 and align re-run eligibility with `ROUND_CAP=2`. Optionally extend `skills/design/scripts/test-step3-review-cap.sh` to grep for cap-2 literals.

### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/design/references/plan-review.md:36-77
- **Concern**: plan-review.md update is limited to matrix bullets while contradictory normative sections remain. Scenario: The plan only lists round-matrix bullets for `plan-review.md`. The file is Step 3's normative contract and still documents cap 5 (line 54), rounds 3-4 pruning and round-5 re-probe (lines 36, 64), scout cap three (line 44), conditional `--no-fallback` plus round-2 generic Codex fallback (line 46), and both-absent Claude reviewer floor (lines 75-77). A matrix-only edit leaves implementers with conflicting operator guidance versus always-`--no-fallback`, no-generic-Codex, and cap-2 behavior.
- **Proposed resolution**: Expand the `plan-review.md` task to rewrite Dispatch, Single-pass cap, Panel pruning, Dynamic archetypes, and Claude-floor sections: cap 2, round-1 full paired panel plus at most one dynamic pair, round-2 prune on round-1 data only, no generic Codex row, always `--no-fallback`, prune-to-empty convergence; remove rounds 3-5 and legacy fallback prose.

### FINDING_4:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/review/plan_review_panel.py:224-250
- **Concern**: Plan-review dispatch still loads every scout archetype with no consumer-side cap. Scenario: The plan caps producers (`plan_scout.py`, `_drafter.py`) at one archetype but does not clamp `_load_dynamic_rows()`, which reads all `scout-plan-manifest.json` entries. A resume or stale manifest with two or more archetypes can still launch more than one dynamic Cursor+Codex pair, breaking acceptance even after producer clamps land.
- **Proposed resolution**: In `plan_review_panel.py`, clamp dynamic rows to one archetype at dispatch (slice after load or call `filter-manifest --max-archetypes 1`). Add a panel test that a two-archetype manifest dispatches only one pair.

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/references/flags.md:57
- **Concern**: skills/design/references/approval-gates.md:15-200. Scenario: skills/design/SKILL.md:381
- **Proposed resolution**: skills/design/SKILL.md:548 Issue guardrail omits #3662 cap-literal mirror surfaces for /design The issue says to mirror #3662 when moving cap-of-5 literals. #3662 updated flags.md approval-gates.md design SKILL.md and plan-review.md together. The plan changes ROUND_CAP and test-step3-review-cap.sh but does not list flags.md approval-gates.md or design/SKILL.md. flags.md still says Gate C review-run counter cap is 5. approval-gates.md and design SKILL.md still gate Re-run review panel on flattened cap of 5 and Step 3 still advertises up to 6 dynamic slots. Step 3 Python may enforce cap 2 but load-bearing /design orchestrator prose stays on the old contract. Add ### UPDATED entries for skills/design/references/flags.md skills/design/references/approval-gates.md and skills/design/SKILL.md. Set Gate C re-entry cap and Step 3 dynamic-slot prose to cap 2 and at most one dynamic pair. Match the #3662 uniform-surface pattern.

### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/references/plan-review.md:36-77
- **Concern**: plan-review.md update scope is too narrow for acceptance. Scenario: Plan lists only a round-matrix bullet refresh for plan-review.md. Normative sections still describe rounds 2-5 generic Codex round-5 cap rounds 3-4 pruning scout cap three both-absent Claude reviewer and conditional --no-fallback. That conflicts with empty generic_codex_rounds always --no-fallback and no reviewer backfill in acceptance. Step 3 loads this file as the operator contract.
- **Proposed resolution**: Expand the plan-review.md task to rewrite Dispatch Panel pruning Dynamic archetypes Single-pass and Claude-floor sections not just the matrix bullets. Remove generic Codex round-2+ fallback-return and both-absent Claude reviewer rows. Set scout cap to 1 and outer cap to 2.

### FINDING_7:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/larch/review/review_core_body.py:855-865
- **Concern**: Missing all-slots-dropped handling for the no-fallback review path. Scenario: The plan only adds `tool-absent` excusal for one-vendor-down panels. When both Cursor and Codex are unavailable, the existing coverage gate still reaches `no successful launched reviewer output` and returns `panel-failed` instead of reusing the degraded or prune-to-empty completion path the edge-case spec requires.
- **Proposed resolution**: Add an explicit zero-output or `ALL_SLOTS_DROPPED=true` branch before the coverage gate so a fully absent panel degrades or converges without Claude backfill.

### FINDING_8:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/references/plan-review.md:46-77
- **Concern**: Plan edge cases forbid Claude reviewer substitutes when both vendors are unavailable, but the plan-review.md update only rewrites the round matrix and leaves Dispatch and both-absent floor prose that still launch a generic Claude reviewer and round-2 generic Codex fallback.. Scenario: Issue acceptance forbids per-slot cross-vendor and Claude reviewer backfill; the new edge-case line reads like a global no-Claude rule. An implementer can remove the both-absent Claude floor or leave contradictory normative text while changing dispatch elsewhere.
- **Proposed resolution**: Narrow the edge case to single-vendor slot drops only, or add an explicit plan-review.md task to rewrite Dispatch, Panel pruning, Single-pass cap, and both-absent sections so they match always --no-fallback, no generic Codex, cap 2, and state clearly whether the both-absent Claude degraded floor stays or is removed.

### FINDING_9:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/larch/review/review_and_fix.py:278-484
- **Concern**: Keeping the public --round-cap flag lets direct Step 5 CLI calls bypass the new 2-round cap. Scenario: python3 python/cli.py review-and-fix step5 --round-cap 5 can still run five rounds, so the issue's cap-2 contract is not enforced on the shipped /implement path
- **Proposed resolution**: Clamp --round-cap to 2 in the public parser or move any higher-cap escape hatch behind an internal-only path

### FINDING_10:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:381,548
- **Concern**: `/design` orchestrator SKILL still hardcodes cap 5 and scout cap 3 while the plan omits this file. Scenario: Step 3 still instructs "up to 6 dynamic slots (scout cap 3)" and Gate C still gates **Re-run review panel** on "below the flattened cap of 5". After `ROUND_CAP=2`, operators at count 2 still see Re-run until count reaches 5, wasting turns even though Step 3 cap-guards block extra loops
- **Proposed resolution**: Add `### UPDATED: skills/design/SKILL.md`: cap-2 Step 3 dynamic topology (at most one dynamic pair), Gate C cap-aware prompt tied to `ROUND_CAP`/review-round-count (not literal 5), and remove stale 6-slot/3-scout language

### FINDING_11:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/references/approval-gates.md:200
- **Concern**: Gate C normative source still pins review re-run cap at 5 and is not in the plan. Scenario: `/design` loads `approval-gates.md` for Gate C. With `ROUND_CAP=2`, "below the flattened cap of 5" keeps offering **Re-run review panel** after the real cap is exhausted, contradicting acceptance "Cap = 2 honored across ... /design plan review"
- **Proposed resolution**: Add `### UPDATED: skills/design/references/approval-gates.md` (and cross-refs in design SKILL): replace cap-of-5 Gate C re-run gating with cap 2 aligned to `review-round-count.txt` / `ROUND_CAP`

### FINDING_12:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/references/plan-review.md:46,54
- **Concern**: Plan-review normative doc update is limited to a round-matrix bullet list; stale dispatch and cap paragraphs remain. Scenario: The plan lists `plan-review.md` but only for matrix bullets. §54 still says "cap of 5" and §46 still documents round-2 generic Codex replacement and conditional `--no-fallback`, which conflicts with empty `generic_codex_rounds`, always-`--no-fallback`, and cap 2
- **Proposed resolution**: Expand the `plan-review.md` entry to require rewriting §Dispatch and the cap paragraph (not just the matrix): cap 2, round-1 full paired panel, round-2 prune-only backup, no generic Codex row, always `--no-fallback`

### FINDING_13:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/review/plan_review_panel.py:224-250
- **Concern**: Plan-review dispatch still loads every scout archetype with no max-1 clamp at the consumer. Scenario: The plan clamps scout producers (`plan_scout.py`, `_drafter.py`) but not `_load_dynamic_rows()`, which iterates the full `scout-plan-manifest.json`. A resumed or stale manifest with 2+ archetypes can still launch more than one dynamic pair in round 1, violating "at most one dynamic pair"
- **Proposed resolution**: Add a `plan_review_panel.py` change: slice or reject manifests to one archetype (shared constant with plan scout) before `_dynamic_slot_rows()`, plus a panel test that a two-archetype manifest dispatches only one pair

### FINDING_14:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/design/plan_scout.py:633-724
- **Concern**: `scout plan-archetypes` still defaults and validates `--max-archetypes` at 3. Scenario: The new one-archetype cap is bypassable through the direct CLI wrapper, so `/design` can still materialize three dynamic archetypes even after the filtered-manifest path is tightened
- **Proposed resolution**: Lower the wrapper default and max validation to 1, and add a direct regression test for `python/cli.py scout plan-archetypes`
