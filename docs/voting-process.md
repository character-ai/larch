# Voting Process

The voting protocol is used by `/design` (plan review) and `/review` (code review) to adjudicate review findings. It replaces the older Negotiation Protocol for these skills. (`/research` continues using the Negotiation Protocol — see [`skills/shared/external-reviewers.md`](../skills/shared/external-reviewers.md).)

## Overview

After reviewers submit findings and findings are deduplicated, a voting panel votes on each finding. `/design` plan review always uses the 3-voter panel (Claude + Codex + Cursor). `/review` (code review) uses a 3-voter panel (Claude + Codex + Cursor) on every round. Claude replacement voters cover unavailable external voters. Each voter casts one of two votes:

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

When a finding is not accepted, it is classified as either **`neutral`** (at least one YES vote but below the acceptance threshold; 0 points) or **`rejected`** (zero YES votes; −1 point). The `neutral` outcome covers what was previously split-panel behavior.

## Degraded-Panel Warnings

The dispatch scripts emit loud degraded-panel warnings when effective judges drop below the expected panel size. Effective means the voter did not fail and produced a non-empty output file. Warnings include the available judge count, missing slots, and the active tier (`unanimous-2`, `single-judge`, or `main-agent-required`) so operators can distinguish a stricter degraded vote from a 0-judge main-agent handoff.

## Voter Panel Composition

`/design` always uses a 3-voter panel in normal mode. `/review` uses a 3-voter panel (Claude + Codex + Cursor) on every round. All launched voters vote on all findings — there is no self-voting exclusion.

| Skill | Voters |
|---|---|
| `/design` (plan review, normal mode) | Claude Code Reviewer subagent + Codex + Cursor — all 3 always launched |
| `/review` (code review) | Claude + Codex + Cursor — all 3 launched every round, with Claude replacements for unhealthy external voters |

## Ballot Format

Before voting, each deduplicated finding receives a stable sequential ID. The ballot is formatted as:

```text
FINDING_1: <reviewer attribution> — <finding description>
FINDING_2: <reviewer attribution> — <finding description>
```

Out-of-scope observations are included on the same ballot with an `[OUT_OF_SCOPE]` prefix:

```text
OOS_1: [OUT_OF_SCOPE] Code — <description of pre-existing issue>
```

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
  -> Format ballot with stable IDs
  -> Launch available voters
  -> Collect votes
  -> Tally per finding using the active tier

Tier outcomes:
  3 eligible: 2+ YES accepts
  2 eligible: 2 YES accepts
  1 eligible: YES accepts, NO rejects
  0 eligible: main agent adjudicates the ballot as untrusted data

Accepted in-scope findings -> implement accepted findings -> score reviewers
Accepted OOS observations -> file GitHub issues -> score reviewers
Neutral and rejected findings -> score reviewers
```

## Out-of-Scope Observations

Reviewers may surface **out-of-scope (OOS) observations** — pre-existing issues or concerns beyond the PR's scope. These are handled alongside in-scope findings on the same ballot but with different vote semantics and outcomes:

- OOS items are included on the ballot with the `[OUT_OF_SCOPE]` prefix
- **YES** on an OOS item means "this deserves a GitHub issue for future attention"
- **NO** means "not worth tracking"
- If an OOS item receives 2+ YES votes, it is **accepted** and filed as a GitHub issue by `/implement`
- Non-accepted OOS items are collected and reported in the PR body for future attention
- **OOS items are never implemented in the current PR** — accepted items result in issue creation only
- OOS scoring mirrors in-scope scoring: accepted OOS earns +1, neutral OOS (≥1 YES, not accepted) scores 0, and rejected OOS (0 YES) costs -1 (see [Point Competition](point-competition.md)).

Claude subagent reviewers always produce OOS observations (via their dual-list output format). External reviewers (Codex, Cursor) **in diff mode** use a slot-kind–dependent output shape: specialist slots (`cursor-specialist-*` and `codex-specialist-*`) produce dual-list output matching the Claude subagent contract (contributing OOS observations via voting). **In `/review` description mode**, all external reviewers produce dual-list output matching the Claude subagent contract and contribute OOS observations via voting (see [skills/review/SKILL.md](../skills/review/SKILL.md) Step 3a).

## Connection to Other Protocols

- **Voting Protocol** is used by `/design` and `/review` — see this document
- **Negotiation Protocol** is used by `/research` — up to N rounds of back-and-forth with external reviewers, where Claude makes the final call
- The key difference: voting uses a democratic panel with threshold rules; negotiation uses bilateral dialogue with Claude as arbiter

See [Point Competition](point-competition.md) for how voting outcomes translate to reviewer scores.
