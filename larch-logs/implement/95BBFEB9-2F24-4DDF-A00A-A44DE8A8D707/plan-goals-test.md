## Goal
Implement issue #3705: [IMPLEMENTING] logs-size-reduction: Phase 1: stop committing derived/duplicate /design log artifacts at publish\n\n## Context.

## Implementation Plan
## Context

Size audit of committed `larch-logs/design/` (245 run dirs): **123.0 MB actual bytes across 54,721 files** (~234 MB on disk — ~47% of `du` is 4K-block waste from thousands of tiny files). Current publish rules (post-#3534 raw-transcript exclusions + revise-mechanism removal) already ship slim runs (~131–287 KB, ~121–137 files for the 3 newest runs), but several layers of derived/duplicate artifacts still land in every new run.

This is Phase 1 of the logs-size-reduction series: stop generating the waste in **new** runs. Phase 2 (separate issue, blocked on this one) applies the finalized rule set retroactively to committed logs.

## Measured duplication (verified byte-for-byte with cmp on committed runs)

### Exact duplicates

- `composed-plan.redacted.md` == `composed-plan.md` in 20/20 sampled runs (~10 KB/run).
- Top-level `findings.md`, `findings-in-scope.md`, `ballot.txt`, `accepted-plan-findings.md`, `voting-tally.md`, `rejected-findings.md`, `scout-plan-manifest.json`, `plan-review-slots.ndjson` are byte-identical copies of the final `plan-review/round-N/` set in every multi-round run checked (~25–30 KB/run).
- `ballot.txt` == `findings-in-scope.md` + `findings-oos.md` concatenated (67/83 rounds byte-identical; the 16 differing rounds differ exactly by the appended OOS blocks). All three parts are committed separately, so the ballot is fully derived (~6 KB/round + ~6 KB top-level).

### Derived/static artifacts committed every run

- `aggregate-validate.py` — byte-identical static script across all 19 runs carrying it (16.7 KB/run). A script belongs in the repo, not re-committed per run.
- `findings.md.tmp` — temp working file (~10 KB/run).
- `{claude,codex,cursor}-plan-voter-prompt.txt` — rendered template + ballot; both inputs already committed (~18 KB/run combined).
- `aggregator-prompt.md` (~15 KB/run when present) — rendered template + `aggregate-untagged-input.md` (itself committed).
- Findings-pipeline intermediates: `findings-in-scope.pre-dedup.md`, `findings-in-scope.pre-aggregation.md`, `aggregate-untagged-input.md` (~28 KB/run) — `findings.md` + `findings-classification.tsv` are the canonical record per the #3534 precedent ("findings.md / voting-tally.md canonical").
- `scout-plan-manifest.json.raw` + `scout-plan-manifest.json.raw.prompt` (~6 KB/run) — cooked `scout-plan-manifest.json` is kept.
- Top-level `*-vote-output.txt.meta` / `*-vote-output.txt.json` sidecars — round-level equivalents are already excluded by `lib-design-round-artifacts.sh`.

### Snapshot redundancy

- `plan-review/round-N/plan.txt` is a full plan snapshot every round (~10–15 KB each). Measured round-over-round deltas: 4–200 changed lines of ~265 total. Rounds ≥ 2 should commit a unified diff vs the previous round's plan (~1–2 KB) instead of the full snapshot.

## Consumer safety (verified against actual readers)

- `/report-tokens --skill=design` reads `manifest.json`, `token-report-final.json`, `timing-report-final.json`, `run-params.json` (`python/report_tokens_scan.py`) — all unaffected.
- `/audit-runs --skill design` reads `manifest.json::larch_version` only (`scans-design.tsv` has a single scan row) — unaffected.
- Pause/resume (`scripts/design-pause-load.sh`) hard-requires `manifest.json`, `run-params.json`, `pause-state.txt`, `plan.txt` — all unaffected. The `REASON=pause` publish path must keep restoring everything resume needs; the proposed exclusions are derived artifacts resume does not require, but the pause path should be exercised in the harness.
- Forensics: the full decision chain (findings → classification TSV → vote outputs → tally → accepted/rejected → plans → diagrams → execution-issues → token/timing ledgers) is retained. Prompts are reconstructible from templates at the run's `larch_version` (git history) + committed inputs; mid-round plans reconstruct by applying diffs forward from round-1.

## Proposed changes

1. `scripts/design-log-publish.sh::design_artifact_excluded()` — add exclusion patterns:
   `aggregate-validate.py`, `findings.md.tmp`, `composed-plan.redacted.md`, `ballot.txt`, `*-plan-voter-prompt.txt`, `aggregator-prompt.md`, `aggregate-untagged-input.md`, `findings-in-scope.pre-dedup.md`, `findings-in-scope.pre-aggregation.md`, `scout-plan-manifest.json.raw`, `scout-plan-manifest.json.raw.prompt`, `*-vote-output.txt.meta`, `*-vote-output.txt.json`.
2. `scripts/lib-design-round-artifacts.sh` + `.md` — remove `ballot.txt` from the round include basenames; make `plan.txt` round-1-only and stage `plan.diff` (unified diff vs the previous round's plan) for rounds ≥ 2.
3. Publisher top-level dedup: skip staging a top-level review artifact when byte-identical (`cmp -s`) to the staged final-round copy. SIMPLE-tier runs without panel rounds keep their top-level copies (they are the only copy).
4. Ripple: `SECURITY.md` design-log publish-allowlist paragraph, `docs/run-logs.md`, `scripts/test-design-log-publish.sh`, `skills/design/scripts/test-plan-review-loop.sh` golden layouts.

## Expected effect

~45–55% cut vs today's baseline (~229 KB → ~80–160 KB per run; ~125 → ~100 files), on top of the ~85% per-run reduction already landed via #3534 + revise removal. Finalizes the rule set that Phase 2 applies retroactively.

## Out of scope

- Retroactive cleanup of committed logs (Phase 2 issue, blocked on this one).
- `larch-logs/implement/` pruning (separate analysis to follow; 216.6 MB actual / 51.7K files — different heavy hitters).

## Test plan
(no test plan section in plan-file)
