# lib-design-round-artifacts.sh

Canonical allowlist for per-round `/design` plan-review forensics under `$DESIGN_TMPDIR/plan-review/round-N/`.

## Consumers

- `skills/design/scripts/plan-review-loop.sh` — `_snapshot_round_dir` copies session-root artifacts into `round-N/` using `design_round_artifact_included`.
- `scripts/design-log-publish.sh` — stages `plan-review/round-N/<file>` using the same functions and rejects `plan-review/round-N/revise/<file>`.

## Edit-in-sync rule

Any allowlist change MUST update, in the same commit:

1. `scripts/lib-design-round-artifacts.sh`
2. This document
3. `skills/design/scripts/plan-review-loop.md` (if snapshot behavior is described)
4. `scripts/design-log-publish.md`
5. `scripts/test-lib-design-round-artifacts.sh`
6. Both consumer scripts if their call sites need adjustment

## Top-level `round-N/` allowlist

**Include basenames:** `findings.md`, `findings-oos.md`, `findings-classification.tsv`, `oos.md`, `oos-accepted-design.md`, `ballot.txt`, `voting-tally.md`, `plan-review-slots.ndjson`, `plan-review-slots.pre-prune.ndjson`, `plan-voter-slots.ndjson`, `scout-plan-manifest.json`, `reviewer-prune-ledger.tsv`, `round-summary.env`, `round-start-s`, `plan.txt` (round 1 only; see below). `accepted-plan-findings.md` and `rejected-findings.md` are dropped from the round-level include set (#3721) — they are cumulative across rounds (round N's copy is a prefix-snapshot of round N+1's), so the top-level copies in `$DESIGN_TMPDIR/` are kept and the round-level duplicates are dropped; per-round outcome attribution is preserved by each round's `findings-classification.tsv` plus `findings.md`. `findings-in-scope.md` is also dropped from the include set (#3715); it is a strict subset of `findings.md` and is recoverable from `findings-classification.tsv` plus `findings-oos.md`.

**Include patterns:** `*-vote-output.txt`, `*-vote-output-first-pass.txt`, `voter*-diag.txt`.

**Exclude patterns:** raw reviewer outputs (`cursor-plan-*-output.txt`, `codex-primary-plan-*-output.txt`, `dyn-*-output.txt`) and sidecars (`*.dirty-tree`, `*.untracked-baseline`, `*.done`, `*.diag`, `*.sidecar`, `*.events.jsonl`, `*-output.txt.prompt`, `*-output.txt.meta`, `*-output.txt.json`, `*-output.txt.cap-hit`, `*-vote-prompt.txt`).

Note: `ballot.txt` remains in the include list (copied into round-N/ during the session snapshot) but is excluded at publish time by `design_artifact_excluded()` in `design-log-publish.sh` — it is derived from `findings-in-scope.md` + `findings-oos.md` and is redundant in the committed log.

**`plan.txt` round-1-only / `plan.diff` rounds ≥ 2:** `design-log-publish.sh` stages `plan.txt` for round 1 only. For rounds ≥ 2, it generates a unified diff (`plan.diff`) of the current round's plan vs the previous round's and stages that instead. `plan.diff` is publisher-generated and does not appear in the source session tmpdir. `design_round_artifact_included` only governs source-tmpdir files; `plan.diff` is staged outside the main round-file loop.

## `round-N/revise/` allowlist

The revise include set is empty. Step 3 no longer runs inter-round revise, so newly published design logs must not include revise prompts, outputs, or candidate patches.

Anything under `revise/` is excluded.
