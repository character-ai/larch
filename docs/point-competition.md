# Point Competition

Reviewers earn points based on how their findings perform in the [voting process](voting-process.md). The competition incentivizes high-quality, actionable findings and discourages noise.

## Scoring Rules

Each finding's vote outcome determines the points awarded to the reviewer(s) who proposed it:

| Vote Result | Points | Description |
|---|---|---|
| **Accepted** (meets YES threshold for the tier) | +1 | The finding was validated by the voting panel |
| **Neutral** (≥1 YES, not accepted) | 0 | Insufficient support, but not dismissed |
| **Rejected** (0 YES) | -1 | Finding was unanimously dismissed by the panel |

If a deduplicated finding was proposed by multiple reviewers (merged during deduplication), all contributing reviewers receive the same points for that finding.

## Out-of-Scope Scoring

Out-of-scope (OOS) observations use the same score shape as in-scope findings: accepted OOS earns +1, neutral OOS (≥1 YES, not accepted) earns 0, and rejected OOS (0 YES) costs -1. Accepted OOS follows the active voting tier (3 judges: 2+ YES; 2 judges: unanimous YES; 1 judge: single YES; 0 judges: main-agent adjudication), so degraded panels never auto-accept observations.

| OOS Vote Result | Points | Description |
|---|---|---|
| **OOS Accepted** (meets YES threshold for the tier) | +1 | Reviewer surfaced an issue worth tracking as a GitHub issue |
| **OOS Neutral** (≥1 YES, not accepted) | 0 | Insufficient support, but not dismissed |
| **OOS Rejected** (0 YES) | -1 | Observation was unanimously dismissed by the panel |

## OOS Issue Filing

Out-of-scope items go on the same voting ballot as in-scope findings, labeled with `[OUT_OF_SCOPE]`:

```text
OOS_1: [OUT_OF_SCOPE] Code — <description>
```

Voters decide whether each OOS item deserves a GitHub issue:

- **2+ YES** -> Accepted: filed as a GitHub issue by `/implement` for future attention, reviewer earns +1
- **≥1 YES below acceptance threshold** -> Neutral: remains an observation reported in the PR body, reviewer earns 0
- **0 YES** -> Rejected: remains an observation reported in the PR body, reviewer loses 1 point

**OOS items are never implemented in the current PR.** Accepted OOS items result in GitHub issue creation only — this cleanly separates "fix now" (in-scope findings) from "fix later" (OOS observations).

## Scoreboard

After voting completes, a scoreboard is printed showing each reviewer's performance. Attribution labels are skill-specific — `/review` uses specialist players (`Correctness`, `Testing`, `Edge-cases`, `Codex-Correctness`, `Codex-Testing`, `Codex-Edge-cases`, `Claude-Generic`); `/design` uses `Code`, `Codex`, and `Cursor`. One row per independent reviewer:

| Reviewer | Findings | Accepted | Neutral (≥1 YES) | Rejected (0 YES) | OOS Proposed | OOS Accepted | OOS-Neutral | OOS-Rejected | Score |
|----------|----------|----------|------------------|-----------------|--------------|--------------|-------------|--------------|-------|
| Correctness | 3 | 2 | 1 | 0 | 0 | 0 | 0 | 0 | +2 |
| Testing | 2 | 1 | 1 | 0 | 1 | 1 | 0 | 0 | +2 |
| Edge-cases | 3 | 2 | 0 | 1 | 0 | 0 | 0 | 0 | +1 |
| Codex-Correctness | 2 | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 0 |
| Codex-Testing | 2 | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 0 |
| Codex-Edge-cases | 2 | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 0 |
| Claude-Generic | 2 | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 0 |

## Future Plans

In future iterations, token allocation will be weighted proportionally to reviewer scores — higher-scoring reviewers will receive more tokens, allowing them to conduct deeper analysis.

## Where Scoring Applies

The competition scoring system is active in skills that use the [voting protocol](voting-process.md):

- **`/design`** — Plan review findings are scored after the voting panel adjudicates
- **`/review`** — Code review findings (round 1) are scored after voting

Skills that use the negotiation protocol (`/research`) do not use competition scoring.

## Conditional spawning

The same finding attribution that awards reviewer points also feeds per-run conditional spawning. In rounds 3-4, reviewer combos may be skipped when their last two launched rounds have net score ≤ 0 or an acceptance rate below 1/3. Net score is accepted findings minus rejected findings. Neutral findings count in the acceptance-rate denominator, but they do not change net score. Round 5 re-probes the full panel. This pruning history is run-local and does not affect the persistent scoreboard.
