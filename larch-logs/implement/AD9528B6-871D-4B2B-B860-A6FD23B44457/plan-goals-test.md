## Goal
Implement issue #3534: [IMPLEMENTING] Design logs commit raw reviewer outputs (design_artifact_excluded gap)\n\nDesign-log publish commits raw plan-review reviewer outputs at top level — align design_artifact_excluded() with the round-N exclusion policy..

## Implementation Plan
## Plan

Issue #3534 — exclude raw plan-review reviewer outputs and related diagnostics from committed top-level `larch-logs/design/<run-id>/` artifacts.

**Exclusion-only / byte budget**: this change adds deny patterns to `design_artifact_excluded()` and removes one dead round-N pattern. It never adds a file to the publish set, so per-run flushed design-log bytes strictly decrease (the currently-committed raw transcripts stop being flushed) and cannot increase. Every deny arm is verified against a real producer so the fix introduces no new dead patterns.

Root cause: `design_artifact_excluded()` in `scripts/design-log-publish.sh` is a deny-only denylist. The plan-review panel writes reviewer transcripts to the top level of `$DESIGN_TMPDIR` (`codex-primary-plan-*-output.txt`, `cursor-plan-*-output.txt`, dynamic `*-dyn-*-output.txt`, and the both-externals-down fallback `claude-plan-generic-output.txt`). None match the existing deny patterns, so they get committed. The round-N gate and the implement-log gate both treat `findings.md` / `voting-tally.md` as canonical and exclude raw transcripts; the top-level design gate must match.

### UPDATED: `scripts/design-log-publish.sh`
- In `design_artifact_excluded()`, add one explicit plan-review exclusion branch after the existing suffix denylist and before `return 1`. Comment: raw plan-review transcripts/diagnostics excluded; `findings.md` / `voting-tally.md` canonical; cite issue #3534.
- Exclude transcript families: `cursor-plan-*-output*.txt`, `codex-primary-plan-*-output*.txt`, `claude-plan-*-output*.txt` (`*-output*.txt` covers phased `-output-phase2.txt` and dynamic slugs).
- Exclude sidecars (producer-backed only):
  - Cursor: `.meta`, `.json`, `.cap-hit`, `.tsv`, `.launch-stderr`
  - Codex primary: `.meta`, `.cap-hit`, `.tsv`, `.launch-stderr`
  - Claude: `.meta`, `.tsv`, `.launch-stderr`, `.stderr-tail`, `.stderr`, `.jsonl`
- Do NOT add Cursor/Codex `.stderr` or `.stderr-tail` arms (no producer: `launch-review.sh` emits none; only `launch-claude-subprocess.sh` writes `${OUTPUT}.stderr` / `.stderr-tail`). Do not add codex `.json` or cursor/codex `.jsonl` (no producers).
- Add diagnostic-surface exclusions: `claude-plan-*.prompt` (incl. `claude-plan-generic.prompt`); slot-named collector failure logs `cursor-plan-*-collector.failure.log`, `codex-plan-*-collector.failure.log`, `dyn-cursor-plan-*-collector.failure.log`, `dyn-codex-plan-*-collector.failure.log`, `unknown-slot-collector.failure.log`; exact `plan-review-collector.stderr`; `plan-review-slots.ndjson.output-files.dropped-slots`.
- Keep existing exclusions (`.prompt`, `.sidecar`, `.diag`, `.done`, `.events.jsonl`, `.dirty-tree`, `.untracked-baseline`).

### UPDATED: `scripts/lib-design-round-artifacts.sh`
- In `design_round_artifact_included()`, replace dead `codex-plan-*-output.txt` with `codex-primary-plan-*-output.txt`. No publish-set behavior change (real outputs were already excluded via the catch-all).

### UPDATED: `scripts/test-design-log-publish.sh`
- Rename fictional `codex-plan-*` fixtures to `codex-primary-plan-*`.
- Add excluded top-level transcript fixtures (`codex-primary-plan-arch-output.txt`, `cursor-plan-arch-output.txt`, `claude-plan-generic-output.txt`, dynamic `*-dyn-foo-output.txt`, phased `...-output-phase2.txt` / `-phase3.txt`).
- Add excluded sidecar fixtures for the producer-backed arms only: `claude-plan-generic-output.txt.meta`, Claude `.stderr` / `.stderr-tail`, Cursor `.json`, Claude `.jsonl`, `.launch-stderr` (all three families), `.tsv`, `.meta`, `.cap-hit`. Do NOT fixture Cursor/Codex `.stderr` / `.stderr-tail`.
- Add excluded diagnostic fixtures: `claude-plan-generic.prompt`; slot-named collector logs (`cursor-plan-arch-collector.failure.log`, `codex-plan-arch-collector.failure.log`, `dyn-cursor-plan-foo-collector.failure.log`, `dyn-codex-plan-harness-fidelity-collector.failure.log`, `unknown-slot-collector.failure.log`); `plan-review-collector.stderr`; `plan-review-slots.ndjson.output-files.dropped-slots`.
- Add all new basenames to the deny-list assertion loop. Preserve existing assertions for `out.txt.meta`, `voter-output-1.json`, `plain.json` (proves canonical artifacts still publish).

### UPDATED: `scripts/test-lib-design-round-artifacts.sh`
- Replace `assert_excluded codex-plan-edge-output.txt` → `codex-primary-plan-edge-output.txt`; replace fictional `dyn-cursor-plan-foo-output.txt` → `cursor-plan-dyn-foo-output.txt`; add `assert_excluded codex-primary-plan-dyn-bar-output.txt`; keep `assert_excluded cursor-plan-arch-output.txt`.

### UPDATED: `SECURITY.md`
- Near the raw Codex `*.events.jsonl` publication-boundary paragraph, document that `design-log-publish.sh` excludes raw plan-review transcripts, producer-backed sidecars (Claude `.stderr`/`.stderr-tail`, `.launch-stderr` for all tools, `.meta`, `.tsv`, `.cap-hit`, Cursor `.json`), generic Claude prompts, collector failure logs, dropped-slot diagnostics, and aggregate `plan-review-collector.stderr`. `findings.md` / `voting-tally.md` remain canonical.

### UPDATED: `scripts/design-log-publish.md`
- Document the transcript families and sidecar suffixes in the `design_artifact_excluded` deny-list; include `claude-plan-*.prompt`, slot-named `*-collector.failure.log` patterns, `plan-review-collector.stderr`, and `plan-review-slots.ndjson.output-files.dropped-slots`; note the exclusion-only / non-increasing-flush-bytes property; adjust prose so the gate is no longer described as excluding only sidecars/operational scratch.

### UPDATED: `scripts/lib-design-round-artifacts.md`
- Change `codex-plan-*-output.txt` → `codex-primary-plan-*-output.txt` in the documented exclude patterns.

### Approach / Edge cases
- Denylist (not allowlist); exclusion-only. Distinguish manifest slot names (`codex-plan-*`, `dyn-codex-plan-*`) from output basenames (`codex-primary-plan-*-output.txt`) — collector failure logs follow slot names, so do NOT deny `codex-primary-plan-*-collector.failure.log`.
- `claude-plan-assessor-round-N.txt` does not match `claude-plan-*-output*.txt` (assessor out of scope). Vote outputs untouched. Existing committed run logs are forensic records — do not edit.

## Acceptance

- `design_artifact_excluded()` excludes the three transcript families and the producer-backed sidecars listed above; Cursor/Codex `.stderr`/`.stderr-tail`, codex `.json`, and cursor/codex `.jsonl` are NOT added.
- `design_round_artifact_included()` uses `codex-primary-plan-*-output.txt`; no `codex-plan-*-output.txt` remains in `lib-design-round-artifacts.sh` or its `.md`.
- `bash scripts/test-design-log-publish.sh` passes: excluded raw transcripts/diagnostics are absent from the published tree; canonical `findings.md` / `voting-tally.md` / round artifacts still publish; no fictional `codex-plan-*` fixture bases remain.
- `bash scripts/test-lib-design-round-artifacts.sh` passes with real-name fixtures (static + dynamic codex, dynamic cursor).
- `scripts/design-log-publish.md`, `scripts/lib-design-round-artifacts.md`, and `SECURITY.md` are updated in the same change.
- `bash scripts/relevant-checks.sh` (or `make lint`) passes (sibling-doc, bash32, bare-grep, mermaid lints).
- Per-run flushed design-log bytes do not increase (exclusion-only; verified by the deny + canonical-present assertions).

diff_lines: 172

## Test plan
(no test plan section in plan-file)
