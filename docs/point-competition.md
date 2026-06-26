# Point Competition

Reviewers earn points based on how their findings perform in the [voting process](voting-process.md). The competition incentivizes high-quality, actionable findings and discourages noise.

## Scoring Rules

Each finding's vote outcome determines the points awarded to the reviewer(s) who proposed it:

| Vote Result | Points | Description |
|---|---|---|
| **Accepted in-scope** with a strict majority of YES voters assigning panel severity `blocker` or `major` | +2 | High-severity finding validated by the voting panel |
| **Accepted in-scope** (all other severities) | +1 | The finding was validated by the voting panel |
| **Neutral** (≥1 YES, not accepted) | -0.25 | Insufficient support, but not dismissed |
| **Rejected** (0 YES) | -1 | Finding was unanimously dismissed by the panel |

Panel severity comes from YES voters on the ballot. The finding body's `body_severity` field is forensic metadata only and does not change points.

If a deduplicated finding was proposed by multiple reviewers (merged during deduplication), all contributing reviewers receive the same weighted points for that finding.

`LARCH_UNIQUE_FINDER_BONUS` is an experimental additive bonus and is off by default. Set it to a positive float to reward the sole finder of an accepted in-scope finding; the suggested experimental value is `0.25`. Deduplicated multi-reviewer findings keep shared base credit and receive no uniqueness bonus. OOS scoring remains flat and unaffected. Reviewer pruning's net gate uses value-weighted accepted points minus rejected counts. The unique-finder bonus does not affect pruning. The acceptance-rate floor still uses unweighted accepted and total counts.

Classification replay applies the same bonus when it is enabled. This covers `voting scoreboard` and progress-report Top reviewers. Sole-finder eligibility uses corpus-aware raw attribution from the classification TSV before `--reviewer-labels` filtering for scoring, with a comma-part guard and label-aware tokenization.

Voters do not see proposer labels. Ballots show stable reviewer lines with `anonymous`; scoring uses out-of-band proposer attribution from `proposer-map.tsv`. Legacy classification TSVs without a `scope` column score accepted rows flat +1 (no severity weighting), with `OOS_*` ids excluded from in-scope Top reviewers via prefix fallback, matching `voting-protocol.md` and the helper.

Voter calibration is measured separately from reviewer points. The voter agreement scoreboard and `/voter-calibration` report do not change reviewer scoring, token allocation, or spawning.

## Voter Severity Calibration

Reviewer/proposer scoring still uses panel YES severity aggregation. Voter standing also includes a separate severity calibration score.

**High Rate** is the share of a voter's valid YES-vote severities that are `blocker` or `major`. Missing or invalid YES severities do not enter the denominator. `body_severity` remains forensic metadata and cannot set this score.

**Calibration Score** stays at `1.000` while High Rate is at or below the configured threshold. Above the threshold, it declines linearly toward `0.000` as High Rate approaches all-high tagging. Chronic all-major tagging lowers voter standing. Calibrated use of `blocker`, `major`, `minor`, `nit`, and `uncertain` preserves standing.

## Out-of-Scope Scoring

Out-of-scope (OOS) observations use flat live scoring regardless of panel severity: accepted OOS earns a provisional +1, neutral OOS (≥1 YES, not accepted) earns 0, and rejected OOS (0 YES) costs -1. Accepted OOS follows the active voting tier (3 judges: 2+ YES; 2 judges: unanimous YES; 1 judge: single YES; 0 judges: main-agent adjudication), so degraded panels never auto-accept observations.

| OOS Vote Result | Points | Description |
|---|---|---|
| **OOS Accepted** (meets YES threshold for the tier) | +1 provisional | Reviewer surfaced an issue worth tracking as a GitHub issue |
| **OOS Neutral** (≥1 YES, not accepted) | 0 | Insufficient support, but not dismissed |
| **OOS Rejected** (0 YES) | -1 | Observation was unanimously dismissed by the panel |

Rows with `scope=oos` are scored as OOS even when `finding_id` is `FINDING_N` (for example scope-drift reroutes).

`/analyze-issues` can additionally report fate-adjusted OOS points by reconciling filed OOS issues against their current GitHub issue fate. Open filed OOS issues stay provisional, PR-closed filed OOS issues keep +1, and closed-unfixed or combined-away filed OOS issues become 0 in that retroactive report. No retroactive -1 penalty is added. This report is diagnostic only and does not change live voting results.

## OOS Issue Filing

Out-of-scope items go on the same voting ballot as in-scope findings, with neutralized reviewer lines:

```markdown
### OOS_1: [OUT_OF_SCOPE] <short title>
- **Reviewer**: anonymous
- **Description**: <description>
```

Voters decide whether each OOS item deserves a GitHub issue:

- **2+ YES** -> Accepted: filed as a GitHub issue by `/implement` for future attention, reviewer earns provisional +1
- **≥1 YES below acceptance threshold** -> Neutral: remains an observation reported in the PR body, reviewer earns 0
- **0 YES** -> Rejected: remains an observation reported in the PR body, reviewer loses 1 point

**OOS items are never implemented in the current PR.** Accepted OOS items result in GitHub issue creation only — this cleanly separates "fix now" (in-scope findings) from "fix later" (OOS observations).

## Scoreboard

After voting completes, a scoreboard is printed showing each reviewer's performance. Attribution labels are skill-specific — `/review` uses specialist players (`Correctness`, `Testing`, `Edge-cases`, `Codex-Correctness`, `Codex-Testing`, `Codex-Edge-cases`, `Claude-Generic`); `/design` uses `Code`, `Codex`, and `Cursor`. One row per independent reviewer:

Accepted, rejected, and OOS artifacts restore reviewer attribution after voting for auditability. Voter-facing files remain neutralized.

| Reviewer | Findings | Accepted | Neutral (≥1 YES) | Rejected (0 YES) | OOS Proposed | OOS Accepted | OOS-Neutral | OOS-Rejected | Score |
|----------|----------|----------|------------------|-----------------|--------------|--------------|-------------|--------------|-------|
| Correctness | 3 | 2 | 1 | 0 | 0 | 0 | 0 | 0 | +2.75 |
| Testing | 2 | 1 | 1 | 0 | 1 | 1 | 0 | 0 | +1.75 |
| Edge-cases | 3 | 2 | 0 | 1 | 0 | 0 | 0 | 0 | +1 |
| Codex-Correctness | 2 | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 0 |
| Codex-Testing | 2 | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 0 |
| Codex-Edge-cases | 2 | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 0 |
| Claude-Generic | 2 | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 0 |

The example assumes one accepted major/blocker finding (+2), one accepted minor finding (+1), and one in-scope neutral finding (-0.25) for Correctness. The Testing row combines one accepted in-scope finding (+1), one in-scope neutral finding (-0.25), and one accepted OOS observation (+1). OOS accepted rows stay flat provisional +1 regardless of voter severity.

When `LARCH_UNIQUE_FINDER_BONUS` is active and rewards at least one accepted in-scope finding, the tally prints one note below the reviewer scoreboard with the bonus value and rewarded sole-finder finding count. The scoreboard table columns do not change.

## Future Plans

Future reviewer token budget should be allocated by precision-value, not cumulative `Score`. The precision-value signal is `net-score-per-finding`.

### Definition

`net-score-per-finding` is pinned to the scoreboard columns above and to `skills/shared/voting-protocol.md` `## Scoreboard`.

- **Numerator (in-scope competition net):** weighted in-scope accepted points minus in-scope rejected points only, i.e. `accepted_weight - Rejected`. Use the same +2/+1/-1 rules from `## Scoring Rules`, including +2 for accepted in-scope major or blocker findings. Exclude OOS accepted and OOS rejected.
- **Denominator:** the in-scope proposed count, the `Findings` / `Proposed` scoreboard column for in-scope rows only. Exclude OOS proposed.
- **Formula:** `net-score-per-finding = (accepted_weight - Rejected) ÷ Proposed`. Division by zero is undefined until a separate policy is stated.
- **Why not raw `Score`:** live tally `Score` also includes `OOS Accepted - OOS Rejected` while `Proposed` / `Findings` is in-scope only (`python/plan_review_tally.py`, `python/review_tally.py`). Dividing full `Score` by in-scope `Proposed` would let OOS-heavy reviewers inflate the signal without raising the denominator.

### Rationale

Illustrative example, assuming every accepted in-scope finding is an ordinary +1 finding with no major or blocker +2 weighting, and rejects are -1:

- **Reviewer A:** 100 proposed, 48 accepted, 24 rejected. In-scope net +24, precision 48%, `net-score-per-finding` +0.24.
- **Reviewer B:** 20 proposed, 15 accepted, 1 rejected. In-scope net +14, precision 75%, `net-score-per-finding` +0.70.

Cumulative `Score`, or raw in-scope net alone, rewards Reviewer A's volume despite Reviewer B's better precision-value.

### Dependencies

Do not ship token allocation until value-weighted points define `value` and voter calibration validates the signal.

## Where Scoring Applies

The competition scoring system is active in skills that use the [voting protocol](voting-process.md):

- **`/design`** — Plan review findings are scored after the voting panel adjudicates
- **`/review`** — Code review findings (round 1) are scored after voting

Skills that use the negotiation protocol (`/research`) do not use competition scoring.

## Conditional spawning

The same finding attribution that awards reviewer points also feeds per-run conditional spawning. In rounds 2-4, reviewer combos may be skipped when recent evidence shows a value-weighted net score ≤ 0 or an acceptance rate below 1/3. Round 2 uses one prior launched round. Rounds 3-4 require two recent launched rounds. The net prune gate uses value-weighted accepted points minus rejected counts. Neutral findings count in the acceptance-rate denominator, but the -0.25 neutral penalty does not change pruning net score. Round 5 re-probes the full panel. This pruning history is run-local, uses unweighted accepted and total counts for the rate gate, and does not affect the persistent scoreboard.
