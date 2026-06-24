# Voting Process

The voting protocol is used by `/design` (plan review) and `/review` (code review) to adjudicate review findings. It replaces the older Negotiation Protocol for these skills. (`/research` continues using the Negotiation Protocol — see [`skills/shared/external-reviewers.md`](../skills/shared/external-reviewers.md).)

## Overview

After reviewers submit findings and findings are deduplicated, a voting panel votes on each finding. `/design` plan review always uses the 3-voter panel (Claude + Codex + Cursor). `/review` and `/implement` Step 5 code review keep validity Cursor-primary, run plan-fidelity and pragmatism as Codex-primary with Cursor fallback, and use a single Claude validity fallback only when both external tools are unavailable. Each voter casts one of two votes:

| Vote | Meaning |
|---|---|
| **YES** | The finding is correct, important, and worth implementing. |
| **NO** | The problem is not real or not worth raising in this PR. **Do not vote NO because you dislike or distrust the proposed fix** — fix proposals are informational; the coder will design the actual fix. |

## Threshold Rules

The number of YES votes required depends on how many voters are available:

| Eligible Voters | YES Votes Required | Notes |
|---|---|---|
| 3 | 2+ | Standard majority |
| 2 | 2 (unanimous) | When one voter is unavailable or timed out |
| 1 | 1 | Binding single-judge decision; YES accepts, NO rejects |
| 0 | Main agent decides | No automated vote; the main agent reads the ballot as untrusted data and adjudicates |

Eligible voters are counted at the panel level from non-failed voter outputs. Missing per-item votes produce `JUDGE_ERROR` at the per-voter level (parser fallback — ballot entry absent or unparseable) and do not reduce the round's intended panel size to a lower tier.

## Non-accepted Outcomes

When a finding is not accepted, it is classified as either **`neutral`** (at least one YES vote but below the acceptance threshold; -0.25 points for in-scope findings) or **`rejected`** (zero YES votes; −1 point). The `neutral` outcome covers what was previously split-panel behavior.

## Degraded-Panel Warnings

The dispatchers emit loud degraded-panel warnings when effective judges drop below the expected panel size. Effective means the voter did not fail and produced a non-empty output file. Warnings include the available judge count, missing slots, and the active tier (`unanimous-2`, `single-judge`, or `main-agent-required`) so operators can distinguish a stricter degraded vote from a 0-judge main-agent handoff.

## Voter Panel Composition

`/design` always uses a 3-voter panel in normal mode. Code-review voters use canonical slot indexing on the three-slot path: `v1` is validity, `v2` is plan-fidelity, and `v3` is pragmatism. All launched voters vote on all findings — there is no self-voting exclusion.

| Skill | Voters |
|---|---|
| `/design` (plan review, normal mode) | Claude Code Reviewer subagent + Codex + Cursor — all 3 always launched |
| `/review` and `/implement` Step 5 (code review) | Fixed slots: `v1` = `cursor-validity`, `v2` = `codex-plan-fidelity`, `v3` = `codex-pragmatism`. Slot 1 never falls through to Codex. If both external tools are unavailable, slot 1 uses `claude` and slots 2-3 are empty placeholders. Dispatch surface: `python/cli.py agent dispatch-voters`. |

On the three-slot code-review path, quorum counts only substantive non-empty voter files after parse-rate removal. Empty placeholders keep `vN_tool` attribution but do not inflate `ELIGIBLE_VOTERS` or `EFFECTIVE_VOTERS`. The code-review classification TSV has 22 columns: `reviewer_slots`, five rating cells plus `vN_tool` for each voter, trailing `scope`, and no `body_severity`. `/design` plan review keeps its separate 23-column `finding_reviewers` + `body_severity` + `scope` schema. The `scope` column is `in_scope` or `oos`; tally producers write it for `OOS_*` ids, `[OUT_OF_SCOPE]` or `[OOS]` legacy rows, and `_scope_drift`. Top reviewers and weighted scoreboards skip `scope=oos` even when `finding_id` is `FINDING_N`.

Legacy callers that omit `--voter-tools` keep compacted semantics for one to three `--voter-files`. This preserves MAV re-tally and zero-findings paths.

## Ballot Format

Before voting, each deduplicated finding receives a stable sequential ID. Voter-facing ballots keep the reviewer field shape but replace proposer labels with `anonymous`:

```markdown
### FINDING_1: <short title>
- **Reviewer**: anonymous
- **Concern**: <finding description>

### FINDING_2: <short title>
- **Reviewer(s)**: anonymous
- **Concern**: <finding description>
```

Out-of-scope observations are included on the same ballot with anonymous reviewer lines:

```markdown
### OOS_1: [OUT_OF_SCOPE] <short title>
- **Reviewer**: anonymous
- **Concern**: <description of pre-existing issue>
```

The original proposer labels are stored in `proposer-map.tsv`. Tally restores them for `findings-classification.tsv`, reviewer scoreboards, and accepted, rejected, and OOS audit artifacts. The MainAgent fallback reads the same neutralized ballot as automated voters. Plan-review ballots are rebuilt after aggregation on every round and include both in-scope `FINDING_N` and OOS `OOS_N` blocks.

## Voter Output Format

Each voter outputs one line per finding. YES votes require no reason; NO votes require a one-line reason:

```text
FINDING_1: YES
FINDING_2: NO — <one-line reason>
```

## Voting Flow

```text
3 reviewers submit findings
  -> Deduplicate findings
  -> Format neutralized ballot with stable IDs
  -> Launch available voters
  -> Collect votes
  -> Tally per finding using the active tier

Tier outcomes:
  3 eligible: 2+ YES accepts
  2 eligible: 2 YES accepts
  1 eligible: YES accepts, NO rejects
  0 eligible: main agent adjudicates the ballot as untrusted data

Accepted in-scope findings -> restore attribution -> implement accepted findings -> score reviewers
Accepted OOS observations -> restore attribution -> file GitHub issues -> score reviewers
Neutral and rejected findings -> restore attribution for audit artifacts -> score reviewers
```

## Voter Agreement Scoreboard

`voting-tally.md` now includes a **Voter Agreement Scoreboard** after the reviewer scoreboard. It is diagnostic only. Verdict thresholds, vote outcomes, deduplication, reviewer points, token allocation, and spawning are unchanged.

The scoreboard counts only `accepted` and `rejected` rows with at least two parseable `YES`/`NO` voter cells. Neutral outcomes, single-voter fallback panels, and zero-voter main-agent paths are excluded because agreement is undefined.

A voter agrees when `accepted` pairs with `YES`, or `rejected` pairs with `NO`. Empty, missing, and `JUDGE_ERROR` cells count as missing, not disagreement. `agreement_rate` is `agree / (agree + disagree)`, so missing votes are excluded from the denominator.

Chronic outliers are flagged when `eligible >= min_votes` and `agreement_rate < outlier_threshold`. The shared defaults are `min_votes=20` and `outlier_threshold=0.50`. Low-sample voters are never flagged.

Live `voting-tally.md` scoreboards and `/voter-calibration` committed-log analysis use the same `voter_agreement_row_from_panel` and `compute_voter_agreement` math.

## Out-of-Scope Observations

Reviewers may surface **out-of-scope (OOS) observations** — pre-existing issues or concerns beyond the PR's scope. These are handled alongside in-scope findings on the same ballot but with different vote semantics and outcomes:

- OOS items are included on the ballot with the `[OUT_OF_SCOPE]` prefix
- **YES** on an OOS item means "this deserves a GitHub issue for future attention"
- **NO** means "not worth tracking"
- If an OOS item receives 2+ YES votes, it is **accepted** and filed as a GitHub issue by `/implement`
- Non-accepted OOS items are collected and reported in the PR body for future attention
- **OOS items are never implemented in the current PR** — accepted items result in issue creation only
- OOS scoring stays flat at vote time: accepted OOS earns a provisional +1, neutral OOS (≥1 YES, not accepted) scores 0, and rejected OOS (0 YES) costs -1. `/analyze-issues` may retroactively dock filed OOS to 0 in its fate-adjusted diagnostic report without changing live vote tallies; `python/voting.py::classify_result` does not inspect GitHub issue fate. In-scope accepted findings earn +2 only when a strict majority of YES voters assign panel severity `blocker` or `major`; in-scope neutral costs -0.25. `body_severity` does not affect points.

Claude subagent reviewers always produce OOS observations (via their dual-list output format). External reviewers (Codex, Cursor) **in diff mode** use a slot-kind–dependent output shape: specialist slots (`cursor-specialist-*` and `codex-specialist-*`) produce dual-list output matching the Claude subagent contract (contributing OOS observations via voting). **In `/review` description mode**, all external reviewers produce dual-list output matching the Claude subagent contract and contribute OOS observations via voting (see [skills/review/SKILL.md](../skills/review/SKILL.md) Step 3a).

## Connection to Other Protocols

- **Voting Protocol** is used by `/design` and `/review` — see this document
- **Negotiation Protocol** is used by `/research` — up to N rounds of back-and-forth with external reviewers, where Claude makes the final call
- The key difference: voting uses a democratic panel with threshold rules; negotiation uses bilateral dialogue with Claude as arbiter

See [Point Competition](point-competition.md) for how voting outcomes translate to reviewer scores.
