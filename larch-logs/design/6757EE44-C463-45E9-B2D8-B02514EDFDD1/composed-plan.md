## Plan

## Approach

- Treat `approach-synthesis.txt` as `NO_SKETCHES`; base the plan on direct repo inspection.
- Keep this docs-only.
- Use `net-score-per-finding` as the named precision-value signal for future token allocation policy.
- Define it inline, pinned to live scoreboard columns and in-scope-only scope (see below).
- Mention that the in-scope weighted accepted term includes the existing +2 major/blocker weight from the scoring table.
- Do not turn this into a full allocation formula spec.

## Files to modify/create

### UPDATED: `docs/point-competition.md`

- In `## Future Plans`, replace the current score-weighted token allocation sentence.
- Say future reviewer token budget should be allocated by precision-value, not cumulative `Score`.
- Name the precision-value signal: `net-score-per-finding`.
- Add a short **Definition** subsection under `## Future Plans` that pins numerator and denominator to the existing scoreboard (cross-reference `## Scoreboard` above and `skills/shared/voting-protocol.md` `## Scoreboard`):
  - **Numerator (in-scope competition net):** weighted in-scope accepted points minus in-scope rejected points only — i.e. `accepted_weight − Rejected`, using the same +2/+1/−1 rules from `## Scoring Rules`. Exclude OOS accepted and OOS rejected from the numerator.
  - **Denominator:** the scoreboard in-scope proposed count (`Findings` / `Proposed` column — in-scope rows only). Exclude OOS proposed from the denominator.
  - **Formula:** `net-score-per-finding = (accepted_weight − Rejected) ÷ Proposed`, with division by zero undefined until a separate policy is stated.
  - **Why not raw `Score`:** live tally `Score` also includes `OOS Accepted − OOS Rejected` while `Proposed`/`Findings` is in-scope only (`python/plan_review_tally.py`, `python/review_tally.py`); dividing full `Score` by in-scope `Proposed` would let OOS-heavy reviewers inflate the signal without raising the denominator.
- Add a short **Rationale** subsection under `## Future Plans`.
- Include the worked example (illustrative only):
  - **Assumption:** every accepted in-scope finding is an ordinary +1 finding (no major/blocker +2 weighting); rejects are −1.
  - Reviewer A: 100 proposed, 48 accepted, 24 rejected → in-scope net +24, precision 48%, `net-score-per-finding` +0.24.
  - Reviewer B: 20 proposed, 15 accepted, 1 rejected → in-scope net +14, precision 75%, `net-score-per-finding` +0.70.
  - State that cumulative `Score` (or raw in-scope net alone) rewards A's volume despite B's better precision-value.
- Add a short **Dependencies** note:
  - Do not ship token allocation until value-weighted points define `value`.
  - Do not ship token allocation until voter calibration validates the signal.
- Preserve existing scoring tables, scoreboard table, and +2/+1/−1 point rules.

### UPDATED: `skills/shared/voting-protocol.md`

- In `## Scoreboard`, replace the final future-token-allocation sentence.
- Say future token allocation should use precision-value, measured as in-scope `net-score-per-finding` (`(accepted_weight − Rejected) ÷ Proposed` on scoreboard columns; OOS excluded from both numerator and denominator), not cumulative reviewer `Score`.
- Keep this as one concise policy sentence plus the column pin; do not change the scoreboard format, columns, point rules, or nested scoreboard behavior.

## Edge cases

- Do not edit `docs/voting-process.md` or `skills/voter-calibration/SKILL.md`.
- Their existing "unchanged" mentions are diagnostic boundary statements, not allocation policy.
- Do not modify `python/` or `scripts/`; no token-allocation implementation exists in the inspected surfaces.
- Keep code spans, paths, identifiers, and tables byte-stable unless directly updating the target prose.
- When describing `net-score-per-finding`, always use the in-scope column pin above; do not document "net competition score ÷ finding count" without the OOS exclusion.

## Failure modes

- Avoid implying allocation ships now.
- Avoid making acceptance rate the chosen signal.
- Avoid saying raw cumulative `Score` controls budget.
- Avoid changing current reviewer scoring semantics while describing future allocation.
- Avoid an unqualified +24/+14 example that conflicts with preserved +2 major/blocker weighting.

## Testing strategy

- Run `make lint`.
- No Python tests are required unless the implementation changes Python files.
- Optional verification: grep for the old phrase `token allocation will be weighted proportionally to reviewer scores` and confirm only intended text changed.

## Acceptance

- `docs/point-competition.md` "Future Plans" no longer states allocation is "weighted proportionally to reviewer scores". It allocates future reviewer token budget by precision-value (`net-score-per-finding`), with a **Definition** (numerator `accepted_weight − Rejected`, denominator in-scope `Proposed`/`Findings`, OOS excluded), a **Rationale** (the worked example), and a **Dependencies** note (value-weighted points; voter calibration).
- `skills/shared/voting-protocol.md` "Scoreboard" carries the same precision-value policy (in-scope `net-score-per-finding`, OOS excluded from numerator and denominator), not cumulative `Score`.
- The scoring tables, scoreboard schema, and +2/+1/−1 point rules are unchanged.
- `docs/voting-process.md` and `skills/voter-calibration/SKILL.md` are not modified.
- No `python/` or `scripts/` changes.
- `make lint` passes.

review_status: complete
rounds_completed: 2
diff_lines: 24
