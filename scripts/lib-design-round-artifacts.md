# lib-design-round-artifacts.sh

Canonical allowlist for per-round `/design` plan-review forensics under `$DESIGN_TMPDIR/plan-review/round-N/`.

## Consumers

- `skills/design/scripts/plan-review-loop.sh` — `_snapshot_round_dir` copies session-root artifacts into `round-N/` using `design_round_artifact_included`.
- `scripts/design-log-publish.sh` — stages `plan-review/round-N/<file>` and `plan-review/round-N/revise/<file>` using the same functions.

## Edit-in-sync rule

Any allowlist change MUST update, in the same commit:

1. `scripts/lib-design-round-artifacts.sh`
2. This document
3. `skills/design/scripts/plan-review-loop.md` (if snapshot behavior is described)
4. `scripts/design-log-publish.md`
5. `scripts/test-lib-design-round-artifacts.sh`
6. Both consumer scripts if their call sites need adjustment

## Top-level `round-N/` allowlist

**Include basenames:** `findings.md`, `findings-in-scope.md`, `findings-oos.md`, `findings-classification.tsv`, `accepted-plan-findings.md`, `rejected-findings.md`, `oos.md`, `oos-accepted-design.md`, `ballot.txt`, `voting-tally.md`, `plan-review-slots.ndjson`, `plan-voter-slots.ndjson`, `scout-plan-manifest.json`, `round-summary.env`, `plan.txt`.

**Include patterns:** `*-vote-output.txt`, `*-vote-output-first-pass.txt`, `voter*-diag.txt`.

**Exclude patterns:** raw reviewer outputs (`cursor-plan-*-output.txt`, `codex-plan-*-output.txt`, `dyn-*-output.txt`) and sidecars (`*.dirty-tree`, `*.untracked-baseline`, `*.done`, `*.diag`, `*.sidecar`, `*.events.jsonl`, `*-output.txt.prompt`, `*-output.txt.meta`, `*-output.txt.json`, `*-output.txt.cap-hit`, `*-vote-prompt.txt`).

## `round-N/revise/` allowlist

**Include:** `codex-output.txt`, `cursor-output.txt`, `claude-output.txt`, `revise.env`, `prompt.txt`, and `*-candidate.patch`.

Anything else under `revise/` is excluded.
