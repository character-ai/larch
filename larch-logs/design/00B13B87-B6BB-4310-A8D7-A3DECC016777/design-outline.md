## Proposed Design Outline

### Goals
- Move the orchestrator-driven multi-round plan-review loop (today: SKILL.md Gate-C re-runs of single-pass `plan-review-loop.sh`) into `plan-review-loop.sh` itself. One Step 3 entry = N internal rounds.
- Wire the convergence + cap + auto-apply integration on top of Piece 1-4 foundations (`--context-files`, aggregator relaxation, per-round voting/tally, `revise-plan-with-waterfall.sh`).
- Stage per-round forensics under `larch-logs/design/<RUN_ID>/plan-review/round-N/` using the `/implement` write-round distillation pattern.

### Non-goals
- An "assessor" agent (deferred to #2953).
- A new top-level wrapper script — loop lives in `plan-review-loop.sh`.
- Changes to dialectic / sketches / Gate C beyond keeping "Re-run review panel" working.
- Reviewer severity tagging (already emitted; this design only computes `IMPORTANT_ACCEPTED_COUNT`).

### Approach sketch
- Extend `plan-review-loop.sh` argv: `--round-cap N` (`${LARCH_DESIGN_ROUND_CAP:-5}`), `--convergence-threshold N` (`${LARCH_DESIGN_CONVERGENCE_THRESHOLD:-3}`). `--round-num` becomes the starting round (default 1); script iterates internally and writes per-round artifacts under `plan-review/round-N/`.
- After each round's tally, compute `ACCEPTED_COUNT` and `IMPORTANT_ACCEPTED_COUNT` (in-scope `### FINDING_N:` blocks only). Exit loop on convergence / zero-finds / cap. Otherwise invoke `revise-plan-with-waterfall.sh` to mutate `plan.txt` in place, then start next round.
- On revision waterfall total failure (Codex + Cursor + Claude all fail): bail with `LOOP_STATUS=revision-failed` + degraded marker; preserve current plan + accumulated findings.
- Top-level artifacts (`plan.txt`, `accepted-plan-findings.md`, `rejected-findings.md`, `oos-accepted-design.md`, `voting-tally.md`) reflect FINAL state. `plan-review/round-N/` holds the distilled forensic allowlist.
- Extend `design-log-publish.sh` allowlist to stage the broader per-round subtree (today only `findings-classification.tsv` is permitted under `plan-review/`).

### Surfaces in scope
- `skills/design/scripts/plan-review-loop.sh` + `.md` — primary.
- `skills/design/references/plan-review.md` — reviewer-prompt contract; env-var + cap/convergence wording.
- `scripts/design-log-publish.sh` + `.md` — per-round allowlist + recursive staging.
- `skills/design/SKILL.md` — Step 3 invocation, KV parsing, tier-cap re-interpretation, Gate B passive-summary wording.
- `skills/design/scripts/test-plan-review-loop.sh` — extend to cover multi-round paths.
- `scripts/test-design-multi-round-integration.sh` + `.md` — NEW end-to-end harness.

### Open questions
- Gate B's exact post-auto-apply shape (passive summary vs removed entirely) — Step 2a sketches.
- Per-round OOS dedup vs accumulation-then-dedup at Step 5b — Step 2a sketches.
- None other.
