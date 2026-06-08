## Goal
Implement issue #3721: [IMPLEMENTING] logs-size-reduction: Phase 3d: drop cumulative-snapshot and GitHub-redundant /design log copies\n\n## Context.

## Implementation Plan
## Context

Phase 3d of the logs-size-reduction series: the two remaining verified zero-loss cuts in `larch-logs/design/`, surfaced by the post-Phase-3b residual analysis. Filed separately because #3715 (Phase 3b) is already in flight; **blocked on #3715** — same publisher surface (`scripts/design-log-publish.sh`, `scripts/lib-design-round-artifacts.sh`), sequencing avoids merge conflicts.

## Cut 1 — round-level cumulative accepted/rejected snapshots (−1.6 MB)

Verified semantics: `accepted-plan-findings.md` is **cumulative across rounds** — round N's copy is a prefix-snapshot of round N+1's (round-5 ⊇ round-4 ⊇ …), and the top-level copy is byte-identical to the final round's (checked across multi-round runs). It is NOT a per-round projection of that round's `findings.md` (containment probe: 0/8 — cumulative entries come from earlier rounds). Same shape for `rejected-findings.md`.

Change:
- Keep the **top-level** cumulative `accepted-plan-findings.md` / `rejected-findings.md` as the canonical final state.
- Drop the **round-level** copies from the round include set (`scripts/lib-design-round-artifacts.sh` + `.md`): corpus-wide −1,446 KB (328 files) accepted + −228 KB (328 files) rejected.
- Per-round outcome attribution is preserved exactly by each round's `findings-classification.tsv` (`voting_result` column) joined with that round's `findings.md` prose.
- **Coordination with #3706**: its class-C rule ("drop top-level review artifacts byte-identical to the final round copy") must EXCLUDE these two basenames — for cumulative files the keep-direction inverts (keep top, drop rounds). If #3706 lands first, its sweep keeps both copies of these two files and this issue's retro pass removes the round-level ones; if this lands first, #3706's C-list simply omits them.

## Cut 2 — GitHub-redundant snapshots (−0.8 MB)

Same policy already adopted for `plan-goals-test.md` in #3714: content whose canonical home is the GitHub issue is not duplicated into committed logs.

- `issue-body.txt` (259 KB, n=68) — raw snapshot of the tracking-issue body; canonical: the issue itself.
- `issue.json` (193 KB, n=40) — JSON snapshot of the same issue.
- `architecture-diagram.md` (332 KB, n=225) — the same Mermaid body is upserted verbatim into the issue-scoped `larch:diagrams` comment by `/design` Step 5c (`skills/design/scripts/design-publish.sh`); the comment is the canonical, jointly-maintained home per `docs/run-logs.md`.

`feature-description.txt` stays — it is the actual run input (point-in-time, consumed by the renderer), not a redundant snapshot.

Change: add the three basenames to `design_artifact_excluded()` in `scripts/design-log-publish.sh`.

## Retroactive sweep (included)

One log-only PR applying both cuts across all committed design dirs:
- Round-level accepted/rejected deletion guarded by the cumulative-semantics check: delete round copy only when it is a prefix/subset of the top-level cumulative file (containment check; keep on mismatch).
- Skip any run dir containing `pause-state.txt` (resumable runs).
- Bulk-edit disclosure per `docs/run-logs.md`.

## Consumer safety

- `/report-tokens --skill=design`: untouched (`manifest.json`, `token-report-final.json`, `timing-report-final.json`, `run-params.json`).
- `audit-runs --skill design`: reads `manifest.json` only.
- Resume (`design-pause-load.sh`): required set untouched; paused dirs skipped.
- `larch:diagrams` upsert path unchanged — only the committed file copy is dropped.
- Ripple: `SECURITY.md` allowlist paragraph, `docs/run-logs.md`, `scripts/test-design-log-publish.sh`, round-artifact harnesses.

## Expected effect

≈ −2.4 MB and −700 files corpus-wide; design residual lands at ~22–23 MB. Together with #3715 this exhausts the verified duplication in `/design` logs — the remainder is unique prose, consumer-read reports, and forensic vote/classification records (further reduction only via #3719's age-based GC).

## Test plan
(no test plan section in plan-file)
