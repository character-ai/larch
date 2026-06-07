## Goal
Implement issue #3638: [IMPLEMENTING] /implement code review: shrink judge panel on vendor unavailability instead of back-filling duplicates\n\n## Summary.

## Implementation Plan
## Summary

Change the `/implement` Step 5 **code-review voting (judge) panel** so that when an external vendor is unavailable, the panel **shrinks to the distinct available judges** instead of back-filling the empty slot with a duplicate (same-vendor or extra-Claude) voter. Claude is always the floor. The existing acceptance-threshold table already encodes the right semantics (2 judges → unanimous, 1 → binding single), so this is primarily a **dispatch** change, not a tally change.

## Proposed behavior

| Availability | Judge panel | Acceptance rule |
|---|---|---|
| **Both vendors up** | Claude + Codex + Cursor (3) | 2+ YES — **unchanged, same as today** |
| **One vendor down** (Codex *or* Cursor) | Claude + the available vendor (2) | **Unanimous** (both must YES) |
| **Both vendors down** | Claude only (1) | Claude decides **unilaterally** (binding single judge) |

If Claude itself also fails when both externals are down → 0 eligible → the existing **main-agent adjudication** floor still applies.

## Current behavior (for contrast)

`scripts/dispatch-code-voters.sh` launches Voter 1 = Claude (always), Voter 2 = Codex-first waterfall, Voter 3 = Cursor-first waterfall (each external slot: primary → **alternate external** → Claude). The panel is deliberately held at **3 launched slots** by back-filling, which today produces:

- **One vendor down** → the empty slot falls to the *other external*: e.g. **Codex down, Cursor up ⇒ Claude + Cursor + Cursor** (two same-vendor judges).
- **Both down** → **Claude + Claude + Claude** (three same-model judges).

> Note: `skills/shared/voting-protocol.md` (lines ~76–77) describes the one-down case as a *Claude* replacement, but the script actually routes to the **alternate external** first. That doc is out of sync and should be corrected as part of this change.

## Rationale — speed + cost without notable quality loss

The back-fill keeps the count at 3, but the filled slots are **not independent judgment** — they are the same model voting twice (2× Cursor, or 2–3× Claude). You pay for redundant samples that add little signal. Shrinking instead:

- **Cost / speed:** removes **1** voter call when one vendor is down, and **2** voter calls when both are down — on **every** review round (up to 5 rounds per run). External reviewers/voters are frequently unavailable in code-review runs, so this is a recurring saving.
- **Quality safeguard:** the existing threshold table compensates — a 2-judge panel requires **unanimous** YES (stricter than majority), and the single-Claude case is the explicit operator-accepted tradeoff.

**Honest tradeoff:** the both-down case gives up the small ensemble-variance-reduction benefit of 3 independent Claude samples in favor of one authoritative Claude judgment. That is the intended trade.

## Scope of change

- **`scripts/dispatch-code-voters.sh`** — launch each external voter **iff its vendor is available**; **no** cross-vendor or Claude back-fill for an absent external. Panel size = 1 (Claude) + number of available externals. This is the core change.
- **`skills/review/scripts/tally-code-votes.sh` + `skills/shared/voting-protocol.md` threshold table** — should remain **unchanged** (already encodes 3→2+, 2→unanimous, 1→single binding, 0→main agent). Confirm the tally keys off the **eligible-voter count**, not a hardcoded 3.
- **`DEGRADED_PANEL_WARNING`** — a panel that shrank because a vendor was unavailable must **not** be reported as an error/degradation; only genuine voter *failures* should warn. Update the "expected 3" warning logic accordingly.
- **`skills/shared/voting-protocol.md`** — fix the stale one-down "Claude replacement" wording (lines ~76–77) and document the new shrink-not-backfill model.
- **`docs/review-agents.md`** Note A (voting-panel description) and any topology counts.
- **`scripts/test-dispatch-code-voters.sh`** — update the regression harness for shrink-not-backfill.

## Acceptance criteria

- Both vendors available → 3-judge panel (Claude + Codex + Cursor), 2+ YES to accept (unchanged).
- Exactly one external available → 2-judge panel (Claude + that vendor), **unanimous** to accept; **no** duplicate same-vendor voter is launched.
- No external available → **single** Claude judge, binding; **no** extra Claude voters launched.
- Claude remains the always-on floor; if Claude also fails with both externals down, the 0-eligible main-agent adjudication path still applies.
- No spurious `DEGRADED_PANEL_WARNING` when the panel shrank solely due to vendor unavailability.
- `scripts/test-dispatch-code-voters.sh` updated and green.

## Related

- **#3636** — the code-review reviewer/judge analysis this proposal came out of (per-slot-instance + marginal-value findings).
- **#3635** — `/design` judge composition redesign. **Consistency flag:** #3635 specifies `/design`'s Codex-absent judge path as **3 Claude** (a back-fill philosophy), whereas this issue proposes `/implement` should **shrink** to fewer judges. The two skills would diverge on degraded-panel philosophy — worth deciding during `/design` whether to align them (e.g., apply shrink-not-backfill to `/design` too) or keep them intentionally different.

## Test plan
(no test plan section in plan-file)
