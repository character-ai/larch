## Goal
Implement issue #5887: [IMPLEMENTING] Single-vendor code-review voting panel; both-down falls back to main-agent adjudication.

## Implementation Plan
## Plan

### Approach

Draft from direct codebase and doc inspection. The provided approach synthesis is `NO_SKETCHES`, so do not cite planning-panel agreement.

Make the smallest registry-led change:

- Change only `review.voters` slot 1 from Cursor-primary to Codex-primary.
- Keep slots 2 and 3 as they are.
- Keep `design.plan_voters` unchanged.
- Keep the existing dispatch gate in `python/larch/agents/agent_voters.py`: slot 1 always launches; slots 2 and 3 launch only when at least one external is present. This preserves the single-Claude floor when both externals are down.
- Update same-file fallback labels and tests that mirror the old slot-1 default.
- Update docs that state code-review validity is Cursor-primary or that Codex does not vote in code review.

### Files to modify/create

### UPDATED: python/larch/core/config.py

Update `ROLE_DEFAULTS["review.voters"]` only.

For voter 1:

- `primary_tool`: `cursor` -> `codex`.
- `default_label`: `cursor-validity` -> `codex-validity`.
- `output_name`: `cursor-validity-vote-output.txt` -> `codex-validity-vote-output.txt`.
- `semantic_labels`: reorder to `(("codex", "codex-validity"), ("cursor", "cursor-validity"), ("claude", "claude"))`.
- `doc_fallback`: state that all three code-review voters waterfall Codex, then Cursor, then Claude, and that both external tools down still shrinks to the single Claude voter-1 anchor.

Do not edit `ROLE_DEFAULTS["design.plan_voters"]`.

### UPDATED: python/larch/agents/agent_voters.py

Update the `DispatchState` default for `voter_1_tool` from `cursor-validity` to `codex-validity`.

Leave `external_voter23 = cursor_present or codex_present` and the `launched_policies` logic unchanged. This is the required no-triplicate-Claude behavior.

### UPDATED: python/larch/review/review_core_body.py

Update the fallback `default_tool` tuple for code-review tally plumbing:

- `("cursor-validity", "codex-plan-fidelity", "codex-pragmatism")`
- becomes `("codex-validity", "codex-plan-fidelity", "codex-pragmatism")`.

### UPDATED: python/larch/review/_voting_calibration.py

Update code-review fallback labels:

- `_CODE_REVIEW_VOTER_FALLBACKS[1]`: `cursor-validity` -> `codex-validity`. This only affects current tool-aware rows with a missing `v1_tool` cell.
- Do **not** change `normalize_voter_label_to_base_tool("v1")`. Leave the bare `"v1"` shorthand mapped to `cursor`. Plan review (FINDING_1, FINDING_9) confirmed that legacy compact-schema TSVs (no `vN_tool` column) still label the row `v1` when read back, and that shorthand always meant Cursor historically. Remapping it to Codex would silently misattribute old committed Cursor votes to Codex in calibration and agreement analysis. New tool-aware rows already normalize correctly through the `codex` prefix via `v1_tool=codex-validity`, so no change is needed there.

Keep historical explicit labels readable. Do not reject old `cursor-validity` rows.

### MAY_UPDATE: python/larch/review/voting.py

Update `voter_launcher_tool()` only if tests or inspection show slot-1 Codex archetype labels need the same normalization as Cursor labels.

Suggested narrow change:

- map labels starting with `codex-` to `codex`.
- keep labels starting with `cursor-` mapped to `cursor`.
- keep `claude`, `codex`, and `cursor` unchanged.

This is not required for dispatch selection, but it may keep parse-rate warning metadata correct for `codex-validity`.

### UPDATED: python/tests/core/test_external_role_defaults.py

Update `test_voter_and_decompose_roles()`.

Assert for `review.voters`:

- voter 1 default label is `codex-validity`.
- voter 1 output is `codex-validity-vote-output.txt`.
- voter 1 semantic labels are `{"codex": "codex-validity", "cursor": "cursor-validity", "claude": "claude"}`.
- voter 1 remains `validity-correctness`.
- `design.plan_voters` expectations stay unchanged.

### UPDATED: python/tests/agents/test_agent_voters.py

Update expectations for slot-1 primary behavior.

Key changes:

- Happy path should emit or materialize `codex-validity` for voter 1.
- Manifest primary-tool counts should become three `codex` primary rows and zero `cursor` primary rows when both externals are present.
- Rename or rewrite `test_voter1_waterfalls_to_codex_when_cursor_unavailable` to cover Codex down, Cursor up. Expected slot-1 label should be `cursor-validity`.
- Update runtime-failure regression from Cursor primary failure to Codex primary failure. It should prove voter 1 re-dispatches to Cursor when Codex fails at runtime.
- Keep `test_both_externals_down_shrink_not_backfill` behavior unchanged: one Claude voter at slot 1, slots 2 and 3 skipped, no degraded warning.
- Update parse-rate keys and diagnostic filenames from `cursor-validity` to `codex-validity` where the test is exercising the primary happy path.

### UPDATED: python/tests/agents/test_external_dispatch.py

Keep the reload test policy-driven. Update only if expected sentinel setup assumes voter 1 is Cursor-primary in a way that no longer matches production examples.

### UPDATED: python/tests/review/test_voting.py

Update calibration and launcher-label expectations:

- Keep `normalize_voter_label_to_base_tool("v1") == "cursor"` (unchanged; see FINDING_1/FINDING_9 note under `_voting_calibration.py` above). Do not flip this assertion.
- Add or update coverage for `normalize_voter_label_to_base_tool("codex-validity") == "codex"`.
- If `python/larch/review/voting.py` changes, add `voter_launcher_tool("codex-validity") == "codex"`.

Do not remove coverage that explicit `cursor-validity` still normalizes to Cursor.

### MAY_UPDATE: python/tests/review/test_review_tally.py

Update only tests that rely on implicit code-review slot-1 fallback labels.

Do not rewrite tests that explicitly pass `cursor-validity`; those represent supported historical or degraded Cursor fallback labels.

### MAY_UPDATE: python/tests/calibration/test_calibration_replay.py

Update only if compact fallback or labeled-cohort tests assert `v1` maps to Cursor by default.

Preserve compatibility with old committed logs that contain `cursor-validity`.

### UPDATED: docs/voting-process.md

Update current-fact prose:

- Code-review voters are Codex-primary for validity, plan-fidelity, and pragmatism.
- Slot labels on the three-slot path are now `v1=codex-validity`, `v2=codex-plan-fidelity`, `v3=codex-pragmatism`.
- If Codex is down but Cursor is up, launched slots may fall through to Cursor labels.
- If both external tools are down, slot 1 uses `claude` and slots 2 and 3 remain empty placeholders.
- Keep `/design` plan review wording as Claude plus Codex plus Cursor.

### UPDATED: skills/shared/voting-protocol.md

Update shared runtime protocol prose:

- Replace code-review `cursor-validity` fixed-slot wording with `codex-validity`.
- State all three code-review voters waterfall Codex, then Cursor, then Claude.
- Preserve the single-Claude fallback wording for both externals down.
- Keep plan-voter section unchanged.

### UPDATED: docs/run-logs.md

Update the new-write three-slot code-review path description:

- `v1` is `codex-validity`.
- `v2` is `codex-plan-fidelity`.
- `v3` is `codex-pragmatism`.
- `claude` can still appear in `v1_tool` on the both-externals-down fallback path.
- Older logs may still contain `cursor-validity`.

### UPDATED: docs/external-reviewers.md

Update the Voting row:

- `review.voters` code-review validity is `Codex→Cursor→Claude`.
- Plan-fidelity and pragmatism remain `Codex→Cursor→Claude`.
- `design.plan_voters` remains separate and unchanged.

### MAY_UPDATE: docs/agents.md

Update if the stale "three Cursor archetype voters" / "Codex does not vote" statement remains.

New wording should say code-review voters are three Codex-primary archetype voters with Cursor then Claude fallback, and both externals down collapses to one Claude slot-1 voter.

### MAY_UPDATE: docs/review-agents.md

Update Note A if it still says Cursor voters cover all axes or Codex does not vote in code review.

Keep the reviewer-panel `--no-fallback` prose unchanged.

### MAY_UPDATE: docs/skills.md

Update the `/implement` public mirror only if it is hand-maintained in this repo and still says Cursor-only voters or Codex does not vote.

If generated, update the source instead and regenerate by the repo's normal process.

### MAY_UPDATE: skills/review/SKILL.md

Update Step 3 wording if it still says Cursor-only code-review voters or Codex does not vote.

Keep the mechanics statement that voting is owned by `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" agent dispatch-voters` and `review tally-code-votes`.

### Edge cases

- **Both externals down**: unchanged. Only voter 1 is launched. It waterfalls to Claude. Voters 2 and 3 are skipped. Do not spawn three Claude voters. Plan review (FINDING_2/7/8/10, both rounds) repeatedly and independently argued this does not satisfy the issue's literal "no voting" / "existing zero-voter tier" language and should instead dispatch zero voters to trigger `TALLY_STATUS=main-agent-vote-required`. The concern never reached the 2-YES acceptance threshold (evenly split both review rounds), and the operator explicitly approved the plan with this behavior preserved at Gate C, fully informed of the dissent. Revisit at `/implement` time if this reading turns out to be wrong; the code change would be small and isolated to `agent_voters.py`'s `launched_policies` construction.
- **Codex down, Cursor up**: all launched code-review voters can fall through to Cursor labels. Slot indexing remains `v1` validity, `v2` plan-fidelity, `v3` pragmatism.
- **Codex probe passes but runtime fails**: dispatch-waterfall should re-dispatch voter 1 to Cursor, then Claude, rather than dropping the slot.
- **Old logs**: `cursor-validity` remains a valid historical label. Do not make calibration or tally reject it.
- **Plan review**: no changes to `design.plan_voters`, `plan_review_panel.py`, plan-review docs, or plan-voter tests except to prove they did not change.

### Failure modes

- A stale default label can make empty or failed slot-1 rows show `cursor-validity` even after the registry changes.
- Updating dispatch gating could accidentally launch three Claude voters when both externals are down. Avoid touching that logic.
- Changing compact legacy semantics too broadly could corrupt old log analysis. Keep explicit old labels supported.
- Updating plan-voter docs or defaults would violate scope.

### Testing strategy

Run targeted Python tests:

```bash
python3 -m pytest \
  python/tests/core/test_external_role_defaults.py \
  python/tests/agents/test_agent_voters.py \
  python/tests/agents/test_external_dispatch.py \
  python/tests/review/test_voting.py \
  python/tests/review/test_review_tally.py \
  python/tests/calibration/test_calibration_replay.py
```

Run relevant changed-file checks if available:

```bash
python3 python/cli.py checks run-relevant
```

For docs-only follow-up checks, run the repo's relevant Markdown or skill lint if `checks run-relevant` reports a skipped dependency.

## Acceptance

- Code-review voters resolve to single-vendor Codex-first with the stated waterfall (Codex, then Cursor, then Claude) for validity, plan-fidelity, and pragmatism.
- Both-externals-down collapses to a single Claude voter-1 anchor, not three Claude voters. (Open dissent: plan review repeatedly argued this should instead be zero-voter main-agent adjudication; operator approved the preserved single-Claude-anchor reading at Gate C. See Edge cases above.)
- `/design` plan voting (`design.plan_voters`) is untouched: still Claude plus Codex plus Cursor.

diff_lines: 170

## Test plan
(no test plan section in plan-file)
