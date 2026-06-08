## Goal
Implement issue #3715: [IMPLEMENTING] logs-size-reduction: Phase 3b: collapse remaining duplication in /design run logs\n\n## Context.

## Implementation Plan
## Context

Phase 3b of the logs-size-reduction series. After #3705/#3706 land, `larch-logs/design/` still holds ~39 MB. A residual-composition scan over all 245 committed runs shows the remaining duplication. Policy: no duplicated content in committed logs — one canonical store per content type.

Blocked on #3705 (same publisher surface: `scripts/design-log-publish.sh`, `scripts/lib-design-round-artifacts.sh`).

## Residual duplication (corpus-wide numbers from the scan)

| Item | MB | Disposition |
|---|---|---|
| `plan.txt` (final plan, 244 runs) | 4.6 | **keep** — canonical |
| `composed-plan.md` (pre-review plan, 244 runs) | 4.6 | **diff-encode**: commit `composed-plan.diff` (unified diff vs final `plan.txt`) instead of the full copy — lossless, typically ~10–20% of full size |
| `scout-dynamic-archetypes-prompt.md` (120 runs × 22.5 KB) | 2.7 | **exclude** — rendered prompt family missed by #3705's list (same class as the excluded `render-plan-*.prompt` / `aggregator-prompt.md`) |
| `findings-in-scope.md` (top-level + per-round) | 3.4 | **drop** — strict subset of `findings.md`; scope split is recoverable from `findings-classification.tsv` and `findings-oos.md` |
| `timing-ledger.tsv` (229 runs) | 1.4 | **drop** — raw tick marks; `timing-report-final.json` (kept, consumer-read) is the projection |
| `aggregator-output.txt` (+ `-phase2`) | 1.2 | stage **only when it differs** from `findings.md` (`cmp -s` guard — same rule as #3708's implement-side fix) |
| Per-voter vote outputs (top-level + per-round) | ~1.1 | **cap** rationale prose at ~2 KB per file, keep per-finding vote lines |
| `plan.txt.before-revise` (16 legacy runs) | 0.2 | retro-delete — revise-era artifact missed by #3706's class A |

Kept untouched (unique content): `feature-description.txt`, `discussion-round*.md`, `approach-synthesis.txt`, `execution-issues.md`, `architecture-diagram.md`, `design-outline.md`, `issue-body.txt`, `larch-tokens-*.jsonl` (raw per-call token ledger — finer-grained than `token-report-final.json`, not a duplicate), classification TSVs, manifests/slots, `run-params.json`.

## Changes

1. `scripts/design-log-publish.sh::design_artifact_excluded` — add `scout-dynamic-archetypes-prompt.md`, `findings-in-scope.md`, `timing-ledger.tsv`, `plan.txt.before-revise`; add the `aggregator-output*` cmp-guard; add the vote-output cap at staging.
2. `scripts/lib-design-round-artifacts.sh` + `.md` — drop `findings-in-scope.md` from the round include set.
3. Publisher: stage `composed-plan.diff` (diff vs final `plan.txt`) instead of `composed-plan.md`; document reconstruction (`patch plan.txt composed-plan.diff -o composed-plan.md` semantics) in `docs/run-logs.md`.
4. **Retroactive sweep included** (one log-only PR): apply the same rules to all 245 committed dirs; `composed-plan.md` → re-encoded as diff; deletions verified derivable (`findings-in-scope` ⊂ `findings.md` checked with a containment probe before delete, keep on mismatch).
5. Pause-safety: as in #3706, skip any run dir containing `pause-state.txt`; the pause-reason publish path keeps shipping the live working set.
6. Ripple: `SECURITY.md` allowlist paragraph, `docs/run-logs.md`, `scripts/test-design-log-publish.sh`, `skills/design/scripts/test-plan-review-loop.sh` golden layouts.

## Consumer safety

- `/report-tokens --skill=design`: untouched (`manifest.json`, `token-report-final.json`, `timing-report-final.json`, `run-params.json`).
- `audit-runs --skill design`: reads `manifest.json` only.
- Resume (`design-pause-load.sh`): required set (`manifest.json`, `run-params.json`, `pause-state.txt`, `plan.txt`) untouched; paused dirs skipped in the retro sweep.

## Expected effect

Corpus: ≈ −13–14 MB (39 → ~25–26 MB). New runs: roughly another −35% on the post-#3705 baseline.

## Test plan
(no test plan section in plan-file)
