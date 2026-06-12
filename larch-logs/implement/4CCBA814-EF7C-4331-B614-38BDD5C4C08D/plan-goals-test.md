## Goal
Implement issue #4080: [IMPLEMENTING] [BUG] Complete #4060 Codex round-3 gating; panel edge cases; /release notes.

## Implementation Plan
[BUG] Complete #4060 Codex round-3 gating; panel edge cases; /release notes

## Context

- Issue #4060 (PR #4078, merged as ddd306b70) requires: in both `/design` and `/implement`, starting with review round 3, do not spawn Codex as reviewer. In round 3+, Codex runs only as a replacement when Cursor is unavailable. Rounds 1 and 2 keep the status quo (both vendors).
- PR #4078 came from `/implement --emergency` (run `80E2974E`): `BYPASS kind=missing-plan`, no plan review, no code-review panel (self-review mode). It changed only `skills/review/scripts/dispatch-panel.sh` plus its test and contract doc.
- The next `/release` run generated a note for #4078 stating the exact opposite ("Codex now runs as reviewer from round 3 onwards"). The release was aborted at the confirm gate. The published v49.0.17 body is clean; nothing wrong shipped.

## Root cause analysis

**The merged code change is directionally correct.** `dispatch-panel.sh` gates Codex slot emission on `ROUND_NUM -lt 3` (static at line 121, dynamic at line 207). The round number flows end to end: `review-and-fix.sh` passes `--round-num` per round and `review-core.sh:709` forwards it. Tests assert round 3 emits no Codex slots.

**The release note inverted before and after.** `/release` Step 3 composes notes from a PR-list TSV (number, title, labels, author, url). PR #4078's title ("Fixes #4060: Implement issue #4060") and body ("Implement requested changes.") carry no direction signal. The note's "previously" clause paraphrases issue #4060's body, including the Cursor-availability nuance that appears nowhere in the diff. Inference (the /release session transcript was not inspected): the composing model fetched the issue body, which states the desired end state in present tense, and under a "Fixed" framing (issue text = old broken behavior) read it as the previous state, then emitted its negation as the new behavior.

**The emergency implement left #4060 half done**, with two edge-case defects. Details below. Line numbers refer to main at ddd306b70.

## Defects

### D1. The /design half of #4060 is not implemented

`skills/design/scripts/dispatch-plan-review-panel.sh` still emits Codex reviewer slots in every round. The caller already supplies the round: `plan-review-loop.sh` passes `--round-num "$round_num"`, and the panel script parses and validates it (lines 44, 63-64). But `ROUND_NUM` is never consulted for Codex gating. Codex emission sites with no round gate:

- static prompt render: ~line 239 (`render_plan_review_prompt ... codex`)
- static manifest rows: ~line 252 (`_append_manifest_row "codex-plan-${_archetype}" codex`)
- dynamic prompt writes: ~line 271
- dynamic manifest rows: ~line 281
- cosmetic `vendor_note` branch in `write_dynamic_prompt` (~line 238)

Net effect: `/design` Step 3 plan-review rounds 3+ still spawn Codex, contradicting #4060.

### D2. dispatch-panel.sh: round 3+ with Cursor unavailable emits an empty panel

`skills/review/scripts/dispatch-panel.sh:116-129`, with `ROUND_NUM >= 3`, `CURSOR_AVAILABLE=false`, `CODEX_AVAILABLE=true`:

- Cursor arm: false. Codex arm: false (round gate). Both-down Claude-fallback arm: false (Codex is available).
- Result: zero static rows. Dynamic rows are suppressed the same way (line 207).

Issue #4060's body explicitly wants Codex as the replacement when Cursor is unavailable. The new round-3 tests cover only the both-available combo, so this regression is untested.

### D3. dispatch-panel.sh: `--no-fallback` is round-blind; merged doc overpromises

`dispatch-panel.sh:557` applies `--no-fallback` whenever both vendors are available, regardless of round. In round 3+ with both available, the panel is Cursor-only AND has no fallback: one failed Cursor reviewer loses the archetype. Before #4078, the Codex peer row covered it. The merged `dispatch-panel.md` claims "(or in round 3+ where Codex is suppressed), the panel keeps normal fallback", which the code does not do.

### D4. /release Step 3 has no direction-verification rule

Nothing in `.claude/skills/release/SKILL.md` Step 3 prevents asserting an unverified before/after direction. With this repo's uniform "Fixes #N: Implement issue #N" PR titles, the same inversion can recur on any release.

## Fix instructions

### A. skills/review/scripts/dispatch-panel.sh (D2, D3)

1. Replace the two inline round gates with one precomputed flag after `ROUND_NUM` validation (~line 88):

   ```bash
   # Codex reviewer slots: rounds 1-2 always (status quo); round 3+ only as
   # replacement when Cursor is unavailable (#4060).
   codex_slots_enabled="false"
   if [[ "$CODEX_AVAILABLE" == "true" ]]; then
       if (( ROUND_NUM < 3 )) || [[ "$CURSOR_AVAILABLE" != "true" ]]; then
           codex_slots_enabled="true"
       fi
   fi
   ```

   Use `[[ "$codex_slots_enabled" == "true" ]]` at both emission sites (static ~line 121, dynamic ~line 207). Keep the both-vendors-down Claude-fallback arm unchanged.

2. Make the waterfall flag round-aware (~line 557): apply `--no-fallback` only when both vendors are available AND `codex_slots_enabled` is true (rounds 1-2). Round 3+ keeps normal fallback, matching the already-merged `dispatch-panel.md` sentence. A Cursor slot that fails in round 3+ may then backfill via Codex or Claude; that is consistent with "Codex as replacement when Cursor is unavailable".

3. Extend `skills/review/scripts/test-dispatch-panel.sh`:
   - Round 3, `--codex-available true --cursor-available false`: expect `STATIC_SLOT_COUNT=3` with Codex output files present (replacement panel), and the launch breadcrumb showing `0 Cursor static, 3 Codex static`.
   - Round 3, both available: assert the waterfall invocation does NOT carry `--no-fallback`; round 2 both available still does. Extend the harness waterfall stub to capture argv if it does not already.
   - Optional: a dynamic-slot variant of the Cursor-unavailable case.

4. Update `skills/review/scripts/dispatch-panel.md` to the final semantics: round 3+ Codex-as-replacement, `--no-fallback` only in rounds 1-2 with both vendors.

### B. skills/design/scripts/dispatch-plan-review-panel.sh (D1)

1. Compute the same `codex_slots_enabled` flag from `CODEX_PRESENT`, `CURSOR_PRESENT`, and `ROUND_NUM` after arg validation (~line 67). Same policy: rounds 1-2 unchanged; round 3+ Codex only when Cursor is absent.
2. Gate all four Codex emission sites listed in D1 on it. Leave the both-absent combined-Claude arm (~line 163) and all Cursor arms unchanged. Update the `vendor_note` branch so round 3+ prompts do not advertise Codex.
3. `--no-fallback` is currently unconditional in the waterfall invocation (line 385). Omit it when both vendors are present AND `codex_slots_enabled` is false (round 3+), mirroring A.2. Leave single-vendor and both-absent invocations unchanged (status quo).
4. Extend `skills/design/scripts/test-dispatch-plan-review-panel.sh` with round-3 cases mirroring A.3: Codex suppressed when both present; Codex replacement panel when Cursor absent; `--no-fallback` presence/absence.
5. Update the sibling contract doc `dispatch-plan-review-panel.md` in the same PR.

### C. .claude/skills/release/SKILL.md Step 3 (D4)

Add a direction rule to Step 3 (prose only, no script change):

- Never infer before/after direction from issue or PR prose. Issue bodies often describe the desired end state, not the previous behavior.
- For PRs with no semantic title (pattern `Fixes #N: Implement issue #N`), derive the behavioral direction only from the merged diff (`gh pr diff <PR>`) and its tests.
- When direction cannot be verified from the diff, state the change neutrally, without before/after claims.


## Test plan

- `bash skills/review/scripts/test-dispatch-panel.sh`
- `bash skills/design/scripts/test-dispatch-plan-review-panel.sh`
- `bash scripts/relevant-checks.sh` (or `make lint`), including `make lint-bash32` for the edited shell
- After merge, `/release --dry-run` and confirm the #4078 entry direction reads correctly or neutrally
