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

**Include basenames:** `findings.md`, `findings-oos.md`, `findings-classification.tsv`, `oos.md`, `oos-accepted-design.md`, `ballot.txt`, `voting-tally.md`, `plan-review-slots.ndjson`, `plan-review-slots.pre-prune.ndjson`, `plan-voter-slots.ndjson`, `scout-plan-manifest.json`, `reviewer-prune-ledger.tsv`, `round-summary.env`, `round-start-s`, `plan.txt` (round 1 only; see below). `accepted-plan-findings.md` and `rejected-findings.md` are dropped from the round-level include set (#3721) — they are cumulative across rounds (round N's copy is a prefix-snapshot of round N+1's), so the top-level copies in `$DESIGN_TMPDIR/` are kept and the round-level duplicates are dropped; per-round outcome attribution is preserved by each round's `findings-classification.tsv` plus `findings.md`. `findings-in-scope.md` is also dropped from the include set (#3715); it is a strict subset of `findings.md` and is recoverable from `findings-classification.tsv` plus `findings-oos.md`. `round-meta.json` and `panel-manifest.ndjson` are synthesized inside round directories by `scripts/write-design-round-meta.sh` but are **excluded at publish time** by `design_artifact_excluded()` in `design-log-publish.sh` (#3929) — per the concise-allowlist principle, round-level manifests are not committed to design logs. `ballot.txt` is similarly excluded at publish time (derived from `findings-in-scope.md` + `findings-oos.md`). `accepted-plan-findings.md` and `rejected-findings.md` remain excluded from round snapshots and are not count inputs for that writer.

**Include patterns:** `*-vote-output.txt`, `*-vote-output-first-pass.txt`, `voter*-diag.txt`.

**Exclude patterns:** raw reviewer outputs (`cursor-plan-*-output.txt`, `codex-primary-plan-*-output.txt`, `dyn-*-output.txt`) and sidecars (`*.dirty-tree`, `*.untracked-baseline`, `*.done`, `*.diag`, `*.sidecar`, `*.events.jsonl`, `*-output.txt.prompt`, `*-output.txt.meta`, `*-output.txt.json`, `*-output.txt.cap-hit`, `*-vote-prompt.txt`).

Note: `ballot.txt` remains in the include list (copied into round-N/ during the session snapshot) but is excluded at publish time by `design_artifact_excluded()` in `design-log-publish.sh` — it is derived from `findings-in-scope.md` + `findings-oos.md` and is redundant in the committed log.

**`plan.txt` round-1-only / `plan.diff` rounds ≥ 2:** `design-log-publish.sh` stages `plan.txt` for round 1 only. For rounds ≥ 2, it generates a unified diff (`plan.diff`) of the current round's plan vs the previous round's and stages that instead. `plan.diff` is publisher-generated and does not appear in the source session tmpdir. `design_round_artifact_included` only governs source-tmpdir files; `plan.diff` is staged outside the main round-file loop.

## `round-N/revise/` allowlist

The revise include set is empty — no files from `revise/` appear in committed design logs.

`design-log-publish.sh` uses a two-tier check for `revise/` files (mirroring the top-level round pattern):

1. `design_round_revise_artifact_included` — always returns 1 (nothing published from `revise/`).
2. `design_round_revise_artifact_excluded` — returns 0 for known session-only artifacts that are silently skipped: raw vendor outputs (`*-output.txt`), candidate patches (`*-output-candidate.patch`), revision outcome (`revise.env`), revision prompt (`prompt.txt`), and all sidecars (`*.done`, `*.dirty-tree`, `*.meta`, `*.prompt`, `*.sidecar`, `*.sidecar.history`, `*.events.jsonl`, `*.events.history`, `*.untracked-baseline`, `*.diag`, `*.failure-diag`, `*.json`).
3. Anything matching neither function is an **unexpected file** and causes a hard publish failure — the loud-failure contract is preserved so genuinely new files added to `revise/` without a corresponding exclusion entry are immediately visible.

## Vendor failure-diagnostics carrier (#3713)

`design_round_artifact_included` returns 0 for `*.failure-diag` so the composed
vendor-failure carrier is preserved in plan-review round snapshots; the raw
`*.sidecar.history` / `*.events.history` archives remain excluded.
## Concise prune/log audit update

The default plan-review round allowlist is exhaustive and concise: `round-summary.env`, `findings-classification.tsv`, `prune-decision.env`, and `prune-nit.env`. Raw findings, per-round plan/diff files, transcripts, vote prose, manifests (`panel-manifest.ndjson`, `round-meta.json`), and per-round prune ledgers are excluded unless a caller explicitly uses a debug path.
