## Goal
Implement issue #3647: [IMPLEMENTING] PR1: Rip out EXONERATE — collapse review voting to YES/NO\n\n# PR1 — Rip out EXONERATE: collapse review voting to YES/NO.

## Implementation Plan
# PR1 — Rip out EXONERATE: collapse review voting to YES/NO

**Part of a 3-PR split of #3644** (the combined spec). Sequence: **this is PR1**, then PR2 (assessor removal, independent), then PR3 (necessity rubric + judge + reviewer — *blocked by this PR*). Implementer: Sonnet.

Read `AGENTS.md`, `KARPATHY_CLAUDE.md`, `BASH_AUTHORING.md`, `docs/voting-process.md`, `docs/point-competition.md`, and `skills/shared/voting-protocol.md` before starting.

## Context

larch review (both `/design` plan review and `/review` / `/implement` code review) accepts too many findings, bloating plans/diffs round over round. One root cause is the **EXONERATE** vote: it scores 0 (shields the proposing reviewer from any penalty) and judges are told "when in doubt, prefer EXONERATE," so the expected value of emitting borderline in-scope spaghetti is positive. In the target design, "real but not necessary" findings are routed to Out-of-Scope (which can still earn +1 as a tracked issue), so EXONERATE is redundant. This PR removes it and collapses voting to **YES/NO**.

This PR is **structural only**: it makes voting binary and simplifies scoring. It does **not** change the judge's acceptance *criteria* — the necessity rubric lands in PR3. After this PR the judge still uses today's "correct / important / worth-implementing" wording, minus EXONERATE.

## Carve-outs — DO NOT TOUCH

- **Dialectic protocol** (`skills/shared/dialectic-protocol.md`, `skills/design/references/dialectic-*`): uses THESIS / ANTI_THESIS; any EXONERATE mention there is contrast prose — leave it.
- **Research** (`skills/research/**`, `scripts/validate-research-output.sh`, `skills/research/references/eval-set.md`): uses the negotiation protocol — leave its EXONERATE references unless a given line is a pure voting-protocol mirror. Verify each occurrence is voting-protocol before editing.

## Change 1 — Scoring (the incentive fix)

New outcome table, **identical for in-scope and OOS**, applied per the existing voting tiers (3 voters: 2+ YES accepts; 2: unanimous; 1: single binding; 0: main-agent adjudication):

| Outcome | Points |
|---|---|
| Accepted (meets YES threshold for the tier) | +1 |
| Not accepted, ≥1 YES | 0 |
| Not accepted, 0 YES | −1 |

This removes the `exonerated` and `split-panel` outcome rows. Update `scripts/lib-vote-tally.sh::classify_result` (and its `.md`) so non-accepted findings classify purely on YES count: `≥1 YES → neutral (0)`, `0 YES → dismissed (−1)`. Remove the EXONERATE branch.

Scoreboard: rename the **Exonerated** column to **Neutral** (it now counts 1-YES non-accepts = 0 points); **Rejected** stays (0-YES = −1). Update the scoreboard tables in `docs/point-competition.md`, `skills/shared/voting-protocol.md`, and `docs/voting-process.md` to match.

## Change 2 — Judge / voter prompt → YES/NO

- `scripts/render-voter-prompt.sh`: remove the two EXONERATE guidance lines (`Vote EXONERATE rather than YES…`, `When in doubt between YES and EXONERATE, prefer EXONERATE`); keep the `Do NOT vote NO solely because you dislike or distrust the proposed fix … Vote NO only when the stated problem is not real or not worth raising` line. Change the output-grammar blocks (both `finding-oos` and `finding-only`) to emit only YES / NO lines (drop the EXONERATE lines). Update the scope-anchor proportionality block (`vote EXONERATE rather than YES` → `vote NO and treat the finding as Out-of-Scope`). Update the OOS rubric so OOS outcomes are YES (file issue) / NO (not worth tracking) — drop EXONERATE. Update the final guard `Lines that do not start with … YES, NO, or EXONERATE` → `… YES or NO`.
- `skills/shared/voting-protocol.md`: the voter prompt template (YES / NO / EXONERATE definitions, output grammar, threshold notes, scoring table, scoreboard) → YES/NO.
- `skills/design/references/plan-review.md`: the inline Voter-1 instruction string and the Codex/Cursor voter instruction string both reference EXONERATE — rewrite to YES/NO (e.g. `vote EXONERATE if the concern is legitimate but not worth implementing` → `vote NO if the concern is not worth implementing in this PR; real-but-deferrable concerns belong in Out-of-Scope`).
- `skills/design/SKILL.md` (Step 3 MAV) and `skills/implement/SKILL.md` (Step 5 MAV): the OOS voter substring that `scripts/test-render-voter-prompt.sh` keeps in sync across four files — update all four identically (drop EXONERATE).

## Change 3 — Parser stays tolerant

Keep the vote parser tolerant: if an external voter still emits `EXONERATE`, map it to `NO` (do not hard-error). Protects against stray external output and old fixtures.

## Change 4 — Token / parse / tally / docs purge

Remove EXONERATE as a vote token and the exonerated scoring concept across the voting surface. Confirmed file surface (re-verify each is voting-protocol, not dialectic/research, before editing):

- Core: `scripts/lib-vote-tally.sh` (+`.md`), `scripts/parse-judge-vote-and-rating.sh` (+`.md`), `scripts/compose-tally-record.sh` (+`.md`), `scripts/write-tally.sh` (+`.md`), `scripts/lib-voter-parse-rate.sh`, `skills/shared/scripts/tally-vote.sh` (+`.md`), `skills/design/scripts/tally-plan-review.sh` (+`.md`), `skills/review/scripts/tally-code-votes.sh` (+`.md`), `skills/review/scripts/emit-tally.sh` (+`.md`), `skills/review/scripts/review-core.sh`, `skills/review-and-fix/scripts/review-and-fix.sh` (+`.md`).
- Prompts: `scripts/render-voter-prompt.sh`, `scripts/render-specialist-prompt.sh`, `skills/design/scripts/render-plan-review-prompt.sh`.
- Docs: `docs/voting-process.md`, `docs/point-competition.md`, `skills/shared/voting-protocol.md`, `skills/design/SKILL.md`, `skills/implement/SKILL.md`, `skills/design/references/plan-review.md`, `docs/workflow-lifecycle.md`, `docs/run-logs.md`, `scripts/larch-log-batches.md`, `scripts/tracking-issue-read.md`, `scripts/launch-review.md`.
- Tests (update expectations): `scripts/test-lib-vote-tally.sh`, `scripts/test-write-tally.sh`, `scripts/test-dispatch-code-voters.sh`, `scripts/test-dispatch-plan-voters.sh`, `scripts/test-launch-review.sh`, `scripts/test-design-structure.sh`, `skills/shared/scripts/test-tally-vote.sh`, `skills/design/scripts/test-tally-plan-review.sh`, `skills/design/scripts/test-findings-classification.sh`, `skills/design/scripts/test-file-design-oos.sh`, `skills/design/scripts/test-record-plan-review-round-timing.sh`, `skills/review/scripts/test-tally-code-votes.sh`, `skills/review/scripts/test-emit-tally.sh`, `skills/review/scripts/test-findings-classification.sh`, `skills/review/scripts/test-dispatch-panel.sh`, `skills/review-and-fix/scripts/test-review-and-fix.sh`, `skills/implement/scripts/test-oos-file-conflict-deps.sh`, `skills/implement/scripts/test-oos-issue-cap.sh`.

Also inspect `skills/issue/scripts/parse-input.sh` (+ its tests) — it surfaced in the grep; confirm whether the EXONERATE reference is load-bearing or incidental and leave issue-skill behavior unchanged unless it is a pure voting mirror.

## Boundary with the other PRs

- **Do NOT** add the necessity rubric, change judge acceptance criteria, or edit reviewer templates / agents — that is PR3 (blocked by this PR).
- **Do NOT** touch the plan-quality assessor — that is PR2.
- This PR keeps acceptance criteria as-is; it only removes EXONERATE and simplifies scoring. It owns **all** EXONERATE-token-and-scoring edits everywhere (including the EXONERATE/exonerated wording in the reviewer Competition notice); PR3 owns the additive necessity-rubric wording.

## Definition of done

1. A prompt rendered by `scripts/render-voter-prompt.sh` offers only YES/NO; no EXONERATE token anywhere in the rendered prompt.
2. `scripts/lib-vote-tally.sh` scores `2+ YES → +1`, `1 YES → 0`, `0 YES → −1` for in-scope and OOS; no exonerated/split-panel paths; the parser maps stray `EXONERATE` → `NO`.
3. Dialectic and research surfaces unchanged.
4. `bash scripts/relevant-checks.sh` and `make lint` pass; all listed `test-*` harnesses pass; `make lint-bash32` and `make lint-bare-grep-probe` clean.
5. Grep sweep: no remaining EXONERATE in the voting surface (dialectic/research carve-outs intentionally retained).
6. `docs/topology.md` regenerated if any topology count changed; the sibling `.md` of every edited script updated in the same PR (`.claude/rules/script-md-siblings.md`).

## Test plan
(no test plan section in plan-file)
