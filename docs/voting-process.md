# Voting Process

The voting protocol is used by `/design` (plan review) and `/review` (code review) to adjudicate review findings. It replaces the older Negotiation Protocol for these skills. (`/research` continues using the Negotiation Protocol — see [`skills/shared/external-reviewers.md`](../skills/shared/external-reviewers.md).)

## Overview

After reviewers submit findings and findings are deduplicated, a voting panel votes on each finding. `/design` (plan review) uses a 3-voter panel (Claude + Codex + Cursor) in normal mode; in `--quick` mode, plan review is Claude-only with no external reviewers or voting panel (see [`skills/design/references/plan-review-quick.md`](../skills/design/references/plan-review-quick.md)). `/review` (code review) uses a 3-voter panel (Claude + Codex + Cursor) on round 1; in rounds 2+ the Codex voter is omitted and a 2-voter panel (Claude + Cursor) is used. Claude replacement voters cover unavailable external voters. Each voter casts one of three votes:

| Vote | Meaning |
|---|---|
| **YES** | The finding is correct, important, and worth implementing. |
| **NO** | The problem is not real or not worth raising in this PR. **Do not vote NO because you dislike the proposed fix** — fix proposals are informational; the coder will design the actual fix. |
| **EXONERATE** | The finding raises a legitimate concern, but is not worth implementing in this PR. Spares the proposing reviewer from losing a point. |

## Threshold Rules

The number of YES votes required depends on how many voters are available:

| Eligible Voters | YES Votes Required | Notes |
|---|---|---|
| 3 | 2+ | Standard majority |
| 2 | 2 (unanimous) | When one voter is unavailable or timed out |
| 1 | 1 | Binding single-judge decision; YES accepts, EXONERATE is exonerated for scoring, NO rejects |
| 0 | Main agent decides | No automated vote; the main agent reads the ballot as untrusted data and adjudicates |

Eligible voters are counted at the panel level from non-failed voter outputs. Missing per-item votes produce `JUDGE_ERROR` at the per-voter level (parser fallback — ballot entry absent or unparseable) and do not reduce the round's intended panel size to a lower tier.

## Multi-voter Exoneration

When a finding is not accepted and is not a `YES == NO` neutral tie, tally code still labels some outcomes **`exonerated`** for scoreboard purposes (see `scripts/lib-vote-tally.sh::classify_result()`). For panels with more than one eligible voter, exoneration follows two paths:

1. **No `NO` votes** — Any `EXONERATE` count with `NO == 0` exonerates (including all-exonerate ballots such as `0Y/0N/3E`).
2. **Mixed `NO` / `EXONERATE`** — Exoneration applies when `EXONERATE` meets or beats `NO` and strictly exceeds `YES` (for example `1Y/2N/3E`).

If `EXONERATE` is positive but neither path holds, the finding stays **`rejected`**.

**History:** PR #2428 narrowed the multi-voter branch to require `YES > 0`, which misclassified valid exoneration panels (notably `0Y/0N/3E` → rejected). Issue #2446 tracks restoring the two-path rule above.

## Degraded-Panel Warnings

The dispatch scripts emit loud degraded-panel warnings when effective judges drop below the expected panel size. Effective means the voter did not fail and produced a non-empty output file. Warnings include the available judge count, missing slots, and the active tier (`unanimous-2`, `single-judge`, or `main-agent-required`) so operators can distinguish a stricter degraded vote from a 0-judge main-agent handoff.

### Sketch-count Independence

**Sketch-count independence (audit conclusion).** Plan-review voting thresholds (3 voters, 2+ YES) and dialectic judge thresholds (3 voters, 2+ same-side) are independent of the `/design` sketch-agent count. The dialectic decision cap `min(5, |contested-decisions|)` naturally handles a smaller pool of contested decisions when fewer sketches diverge. Reducing the regular-mode sketch fan-out from 8 to 4 (umbrella issue #1553) does not require any threshold change.

## Voter Panel Composition

`/design` always uses a 3-voter panel in normal mode. `/review` uses a 3-voter panel on round 1 and a 2-voter panel (Claude + Cursor) in rounds 2+. All launched voters vote on all findings — there is no self-voting exclusion.

| Skill | Voters |
|---|---|
| `/design` (plan review, normal mode) | Claude Code Reviewer subagent + Codex + Cursor — all 3 always launched |
| `/design` (plan review, `--quick` mode) | Claude only — no external reviewers, no voting panel |
| `/review` (code review, round 1) | Claude + Codex + Cursor — all 3 launched, with Claude replacements for unhealthy external voters |
| `/review` (code review, round 2+) | Claude + Cursor — Codex voter omitted to reduce cost; 2-voter panel (unanimous YES required) |

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

Each voter outputs one line per finding. YES votes require no reason; NO and EXONERATE votes require a one-line reason:

```text
FINDING_1: YES
FINDING_2: NO — <one-line reason>
FINDING_3: EXONERATE — <one-line reason>
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
  1 eligible: YES accepts, EXONERATE exonerates, NO rejects
  0 eligible: main agent adjudicates the ballot as untrusted data

Accepted in-scope findings -> implement accepted findings -> score reviewers
Accepted OOS observations -> file GitHub issues -> score reviewers
Neutral, exonerated, and rejected findings -> score reviewers
```

## Out-of-Scope Observations

Reviewers may surface **out-of-scope (OOS) observations** — pre-existing issues or concerns beyond the PR's scope. These are handled alongside in-scope findings on the same ballot but with different vote semantics and outcomes:

- OOS items are included on the ballot with the `[OUT_OF_SCOPE]` prefix
- **YES** on an OOS item means "this deserves a GitHub issue for future attention"
- **NO** means "not worth tracking"
- **EXONERATE** means "legitimate observation but not worth filing an issue"
- If an OOS item receives 2+ YES votes, it is **accepted** and filed as a GitHub issue by `/implement`
- Non-accepted OOS items are collected and reported in the PR body for future attention
- **OOS items are never implemented in the current PR** — accepted items result in issue creation only
- OOS scoring mirrors in-scope scoring: accepted OOS earns +1, neutral or exonerated OOS scores 0, and rejected OOS costs -1 (see [Point Competition](point-competition.md)).

Claude subagent reviewers always produce OOS observations (via their dual-list output format). External reviewers (Codex, Cursor) **in diff mode** use a slot-kind–dependent output shape: specialist slots (`cursor-specialist-*` and `codex-specialist-*`) produce dual-list output matching the Claude subagent contract (contributing OOS observations via voting). **In `/review` description mode**, all external reviewers produce dual-list output matching the Claude subagent contract and contribute OOS observations via voting (see [skills/review/SKILL.md](../skills/review/SKILL.md) Step 3a).

## Connection to Other Protocols

- **Voting Protocol** is used by `/design` and `/review` — see this document
- **Negotiation Protocol** is used by `/research` — up to N rounds of back-and-forth with external reviewers, where Claude makes the final call
- **Dialectic Protocol** is used by `/design` Step 2a.5 (contested design decisions) — see [Relationship to Dialectic Protocol](#relationship-to-dialectic-protocol) below
- The key difference: voting uses a democratic panel with threshold rules; negotiation uses bilateral dialogue with Claude as arbiter; dialectic adjudicates binary debater defenses

See [Point Competition](point-competition.md) for how voting outcomes translate to reviewer scores.

## Relationship to Dialectic Protocol

`/design` Step 2a.5 runs a separate protocol — **dialectic adjudication** — to resolve contested design decisions. This protocol is **structurally parallel to voting-protocol but semantically independent**. The canonical specification lives in [`skills/shared/dialectic-protocol.md`](../skills/shared/dialectic-protocol.md).

### Do not reuse voting-protocol parsers, thresholds, or scoring for dialectic

Maintainers extending Step 2a.5 MUST NOT reuse this document's ballot parser, threshold tables, or scoring rules for dialectic. The two protocols differ on every surface:

| Surface | Voting Protocol | Dialectic Protocol |
|---|---|---|
| Ballot ID prefix | `FINDING_N` (and `OOS_N` for out-of-scope) | `DECISION_N` |
| Vote tokens | `YES` / `NO` / `EXONERATE` | `THESIS` / `ANTI_THESIS` (binary — no third option) |
| Accept threshold (3 voters) | 2+ YES | 2+ same-side |
| Scoring | Reviewer competition scoreboard (+1 / 0 / -1) | **No scoring** (dialectic is not a competition) |
| OOS semantics | In-scope vs `[OUT_OF_SCOPE]` prefix; symmetric scoring for OOS | No OOS concept — every decision is binding or synthesis-falls-back |

### Mechanical "no Claude debaters" rule (debate execution only)

The dialectic protocol diverges from the repo-wide "replacement-first" fallback architecture **for the debate phase only**: when an assigned external debater tool (Cursor for odd-indexed decisions, Codex for even) is unavailable, the bucket is **skipped entirely** and a `Disposition: bucket-skipped` resolution is written — Claude Code Reviewer subagents are **never** substituted into the debate path. This is intentional (see GitHub issue #98 for the rationale): debaters produce adversarial arguments where model-specific writing style could encode tool identity and bias the downstream judge panel.

The **judge panel** (post-debate adjudication, always 3 slots) uses the repo-wide replacement-first pattern normally: when Cursor or Codex is unhealthy, a Claude Code Reviewer subagent replaces that slot so the panel always remains at 3. Judges only adjudicate between pre-authored defenses; the "no Claude substitution" rule is specific to adversarial debate, not to adjudication.
