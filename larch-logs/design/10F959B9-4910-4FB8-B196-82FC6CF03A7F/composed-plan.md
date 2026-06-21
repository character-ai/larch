## Plan

## Approach

- Add one shared neutral cost constant in `python/voting.py`.
- Score only **in-scope** `neutral` rows as `-0.25`.
- Keep **OOS neutral** at `0`.
- Keep accepted, rejected, and silence unchanged.
- Add score formatting so integer scores still render as `3`, while fractional scores render as `2.75` or `-0.25`.
- Update docs, runtime competition notices, and the canonical reviewer rubric in `skills/shared/reviewer-templates.md` so live prompts no longer say in-scope neutral findings earn `0`.
- Update hand-maintained specialist agents `agents/reviewer-edge-cases.md` and `agents/reviewer-testing.md` with the same in-scope non-acceptance wording; they are not template-generated but are loaded by `/review` via `STATIC_REVIEWERS`.
- Regenerate committed template-derived agent artifacts and pre-rendered reviewer bodies from the updated template and hand-maintained specialists.
- Recompute worked example scoreboard totals wherever neutral in-scope rows appear so prose and arithmetic match.

## Files to modify/create

### UPDATED: python/voting.py

- Add `NEUTRAL_FINDING_COST = 0.25` near the existing scoring constants.
- Add a small score-format helper, for example `format_score(score: int | float) -> str`.
  - Return integers without `.0`.
  - Return fractional values with compact formatting.
- Update `_scoreboard_points_from_classification`.
  - Change return values from `int`-only to numeric scores.
  - For `accepted`, keep `accepted_points_from_classification_row`.
  - For `rejected`, keep `-1`.
  - For `neutral`, subtract `NEUTRAL_FINDING_COST` only when the row is in scope.
  - Treat `scope=oos` as OOS.
  - For legacy rows without `scope`, keep `OOS_*` prefix as OOS fallback so legacy OOS neutral stays `0`.
- Use `format_score` in `scoreboard_main`.
- Do not change `classify_result`.
- Do not change `compose_tally_record --neutral`; it remains a count.

### UPDATED: python/plan_review_tally.py

- In `_scoreboard`, subtract `row["neutral"] * voting.NEUTRAL_FINDING_COST` from the in-scope score formula.
- Keep OOS neutral out of the score formula.
- Render the final score through `voting.format_score`.
- Keep all count columns as integers.

### UPDATED: python/review_tally.py

- In the reviewer competition scoreboard loop, subtract `row["neutral"] * voting.NEUTRAL_FINDING_COST` from the score formula.
- Format the computed score with `voting.format_score` before interpolating it into the scoreboard row (the `| {score} |` cell around lines 710–711).
- Keep manifest dead-row and count behavior unchanged.

### UPDATED: python/test_voting.py

- Extend `test_scoreboard_main_weights_classification_tsv`.
- Add an in-scope neutral row and assert the reviewer score includes `-0.25`.
- Add an OOS neutral row and assert it does not change score.
- Add or preserve a legacy no-`scope` assertion.
- If adding a legacy OOS neutral row, assert `OOS_*` legacy fallback does not apply the neutral penalty.

### UPDATED: python/test_plan_review.py

- Update `test_tally_plan_review_mixed_votes_and_artifacts`.
- Assert the reviewer for the current neutral in-scope `FINDING_2` gets `-0.25`.
- Keep the existing OOS assertions.
- Keep the accepted major/blocker score assertion, adjusted only if the target row changes.

### UPDATED: python/test_review_tally.py

- Extend `test_tally_weighted_scoreboard_major_oos_and_coproposers` or add a focused test.
- Include one in-scope neutral finding with a distinct reviewer.
- Assert that reviewer score is `-0.25`.
- Include or assert an OOS neutral case stays `0`.
- Pin existing integer scoreboard assertions (`2`, `3`, `1`) so they still match after `format_score` is applied to reviewers with zero neutral findings.

### UPDATED: docs/point-competition.md

- Change in-scope neutral scoring from `0` to `-0.25`.
- Keep OOS neutral documented as `0`.
- Recompute the example scoreboard values for rows with in-scope neutral findings:
  - `Correctness`: `+3` → `+2.75` (one major/blocker `+2`, one minor `+1`, one in-scope neutral `-0.25`).
  - `Testing`: `+2` → `+1.75` (one in-scope accepted `+1`, one in-scope neutral `-0.25`, one OOS accepted `+1`).
  - Leave rows with no in-scope neutral findings unchanged.
- Update prose so pruning remains explicitly unweighted and unchanged.

### UPDATED: skills/shared/voting-protocol.md

- Change in-scope `neutral` outcome scoring from `0` to `-0.25`.
- Keep OOS neutral at `0`.
- Update the competition scoring table.
- Update the Neutral column explanation so it says in-scope neutral findings cost `-0.25`, not `0`.
- Recompute and update the worked example scoreboard totals:
  - `_label1_`: `+3` → `+2.75`.
  - `_label2_`: `+1` → `+0.75`.
  - Leave `_label3_` at `0`.
- Keep pruning language unchanged except for clarifying that pruning does not use the neutral penalty.
- Keep example totals aligned with the updated `docs/point-competition.md` example.

### UPDATED: skills/design/references/plan-review.md

- Update the competition notice.
- Update the competition scoring paragraph.
- Say non-accepted in-scope findings with at least one YES cost `-0.25`.
- Keep OOS flat at `+1/0/-1`.

### UPDATED: docs/voting-process.md

- Update non-accepted outcome prose.
- Say in-scope `neutral` costs `-0.25`.

### UPDATED: python/rendering.py

- Update the `competition_notice` prose emitted for review prompts.
- Say in-scope findings with at least one YES below threshold cost `-0.25`.
- Keep pruning wording unchanged.

### UPDATED: skills/shared/reviewer-templates.md

- Update all four identical competition-rubric copies (the `You are scored against this same rubric` blocks).
- Change in-scope non-acceptance wording from `earn 0 if at least one judge found it credible` to cost `-0.25` when at least one judge found it credible and the finding is below acceptance.
- Keep rejected in-scope wording at `-1 if none did`.
- Keep Out-of-Scope guidance unchanged: panel acceptance still earns `+1`, and OOS neutral remains costless.

### UPDATED: agents/reviewer-edge-cases.md

- Hand-edit the competition-rubric block (not template-generated).
- Keep Out-of-Scope guidance unchanged.

### UPDATED: agents/reviewer-testing.md

- Apply the same in-scope non-acceptance wording change as `agents/reviewer-edge-cases.md`.
- Keep OOS guidance unchanged.

### UPDATED: agents/code-reviewer.md

- Regenerate from the updated template; do not hand-edit.

### UPDATED: agents/reviewer-plan-fidelity.md


### UPDATED: agents/reviewer-code-robustness.md


### UPDATED: agents/reviewer-security-structure-tests.md


### UPDATED: agents/pre-rendered/

- Regenerate pre-rendered reviewer bodies via `python3 python/cli.py generate pre-rendered-reviewer-prompts` after both template-derived agents and hand-maintained specialists are updated; do not hand-edit.

## Edge cases

- **OOS neutral:** Must remain `0` in both live tally paths and the shared scoreboard CLI.
- **Legacy classification TSVs:** Rows without `scope` may need `OOS_*` fallback so old OOS neutral rows are not penalized.
- **Fractional totals:** Scores like `2.75` and `-0.25` must render cleanly.
- **Integer totals:** Scores like `3.0` must render as `3` in all scoreboard paths, including `review_tally.py` after neutral subtraction is added.
- **Co-proposers:** Every proposer of a neutral in-scope finding gets the same `-0.25`.
- **Counts:** Neutral count columns remain integer counts.
- **Hand-maintained specialists:** `agents/reviewer-edge-cases.md` and `agents/reviewer-testing.md` must be edited directly; stale rubric text there would leave `/review` teaching the old `earn 0` economics even after tally scoring changes.
- **Generated artifacts:** Edits to template-derived `agents/*.md` and `agents/pre-rendered/*` must come only from the generate commands so `python3 python/cli.py generate check` stays green.

## Failure modes

- Penalizing OOS neutral rows would violate the scope decision.
- Rendering raw floats could produce noisy score strings (`2.0` instead of `2`) in `review_tally.py` scoreboard output.
- Changing `--neutral` from a count to a point value would break run-log contracts.
- Reusing the weighted score in pruning or Top reviewers would violate non-goals.
- Updating code and tally docs but leaving `reviewer-templates.md` stale would keep `/review` and `/design` reviewer prompts teaching the old `earn 0` economics.
- Updating template-derived agents but omitting hand-maintained `reviewer-edge-cases` and `reviewer-testing` would leave `STATIC_REVIEWERS` specialists teaching stale raise-threshold economics.
- Updating scoring prose but leaving worked example totals unchanged would teach contradictory arithmetic.

## Testing strategy

- Run targeted tests:
  - `python3 -m pytest python/test_voting.py python/test_plan_review.py python/test_review_tally.py`
- Regenerate and verify generated artifacts:
  - `python3 python/cli.py generate code-reviewer-agent`
  - `python3 python/cli.py generate reviewer-plan-fidelity-agent`
  - `python3 python/cli.py generate reviewer-code-robustness-agent`
  - `python3 python/cli.py generate reviewer-security-structure-tests-agent`
  - `python3 python/cli.py generate pre-rendered-reviewer-prompts`
  - `python3 python/cli.py generate check`
- Run Python checks:
  - `make py-lint`
  - `make py-test`
- Run full repository lint:
  - `make lint`

## Acceptance

- `python/voting.py` defines `NEUTRAL_FINDING_COST = 0.25` and a `format_score` helper. `_scoreboard_points_from_classification` subtracts the cost for in-scope `neutral` rows only (rows with `scope=oos`, or legacy rows whose id starts with `OOS_`, are excluded), keeps `rejected` at `-1` and `accepted` weighted via `accepted_points_from_classification_row`, and `scoreboard_main` renders the score through `format_score`.
- `python/plan_review_tally.py::_scoreboard` and the `python/review_tally.py` competition-scoreboard loop subtract `row["neutral"] * voting.NEUTRAL_FINDING_COST` (in-scope neutral only) and render the Score cell through `voting.format_score`; OOS neutral stays `0`.
- Integer scores render without a trailing `.0` (e.g. `3`); fractional scores render compactly (e.g. `2.75`, `-0.25`) in all three scoreboard paths.
- `classify_result` is unchanged. `compose_tally_record --neutral` stays a non-negative integer count. Conditional pruning math and `python/progress_report.py` accepted-points/token-allocation paths are unchanged.
- `docs/point-competition.md`, `skills/shared/voting-protocol.md`, `skills/design/references/plan-review.md`, `docs/voting-process.md`, the `python/rendering.py` `competition_notice`, `skills/shared/reviewer-templates.md`, and the hand-maintained `agents/reviewer-edge-cases.md` / `agents/reviewer-testing.md` all state in-scope neutral costs `-0.25` and OOS neutral stays `0`; worked-example scoreboard totals are recomputed to match.
- Template-derived agents (`agents/code-reviewer.md`, `agents/reviewer-plan-fidelity.md`, `agents/reviewer-code-robustness.md`, `agents/reviewer-security-structure-tests.md`) and `agents/pre-rendered/` are regenerated via the `generate` commands (not hand-edited), and `python3 python/cli.py generate check` passes.
- `python3 -m pytest python/test_voting.py python/test_plan_review.py python/test_review_tally.py` passes, including new assertions for in-scope neutral `-0.25`, OOS neutral `0`, legacy `OOS_` fallback, and preserved integer totals. `make py-lint`, `make py-test`, and `make lint` pass.

review_status: complete
rounds_completed: 3
diff_lines: 360
