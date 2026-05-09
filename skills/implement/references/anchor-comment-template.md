# Anchor Comment Template

**Consumer**: `/implement` Phase 3 (umbrella #348) — overview of the anchor-comment schema and index of per-step fragment files. This file is the thin overview; load the relevant fragment for each step (see Per-step load table below).

**Contract**: index and overview for the anchor-comment fragment system. Rich content has been partitioned into four per-step fragments (see below) to avoid loading the full 37 KB file at every step. This file retains: the voting-tally extraction guidance consumed by Step 5 consumers, and the edit-in-sync pointer table. The executable source of truth for `SECTION_MARKERS` is `scripts/anchor-section-markers.sh`; `scripts/tracking-issue-write.sh`'s inline `COLLAPSE_PRIORITY` array is a permutation of the same slug set.

**When to load**: do NOT load this overview file at Steps 0.5, 2, 9a.1, or 11 — load the relevant per-step fragment instead. This file may be loaded for the Voting Tally extraction guidance (Step 5 panel consumers) or for orientation on the anchor schema.

**Per-step load table**:

| Step | Fragment to load | Content |
|---|---|---|
| 0.5, 11 | `anchor-template-canonical-body.md` | Anchor first-line marker, seed placeholder, canonical template (all 11 sections including `## Implementation Plan` synthesis heading), section markers, collapse priority |
| 2 (Q/A upsert) | `anchor-template-execution-issues.md` | Execution-issues section format + compose-time sanitization rule |
| 9a.1 | `anchor-template-oos-pipeline.md` | Full OOS pipeline procedure (steps 1–7, Rules A/B, cap, dedup) |
| Quick-mode paths | `anchor-template-quick-mode.md` | Quick-mode fallback text per section |

---

## Voting Tally extraction guidance

The `plan-review-tally` and `code-review-tally` sections contain per-finding vote counts and per-reviewer competition scoreboards. For Phase 3+:

- The tally table format matches the scoreboard format in `skills/shared/voting-protocol.md`.
- Future consumers extracting tallies from an existing anchor comment should use the section-open / section-end markers as the extraction boundary (not prose heuristics).
- If a tally section is present but its interior is collapsed to the `[section '...' truncated — see execution-issues.md locally]` placeholder, treat the tally as unavailable and degrade gracefully — do NOT fabricate counts.

## Edit-in-sync pointers

| File | Relationship |
|---|---|
| `scripts/anchor-section-markers.sh` | Single source of truth for the `SECTION_MARKERS` array (sourced by `tracking-issue-write.sh` and `assemble-anchor.sh`); slug set must match the list in `anchor-template-canonical-body.md`. |
| `scripts/tracking-issue-write.sh` | Inline `COLLAPSE_PRIORITY` array must be a permutation of the slug list in `anchor-template-canonical-body.md` (same set, body-cap collapse priority order). Enforced by a test-harness invariant in `scripts/test-tracking-issue-write.sh`. |
| `${CLAUDE_PLUGIN_ROOT}/scripts/compose-review-findings.sh` | Composes the additive `review-findings-full` fragment from `accepted-plan-findings.md`, plan-review rejected entries, and code-review rejected entries; falls back to `docs/review-archive/issue-<N>.jsonl` archive at the 30 KB inline threshold. Sibling contract: `scripts/compose-review-findings.md`. Invoked by `skills/implement/SKILL.md` Step 5 after `/review` returns or the quick-mode review loop completes. |
| `scripts/assemble-anchor.sh` | Consumes `SECTION_MARKERS` via the shared helper; emits marker pairs and the first-line HTML marker documented in `anchor-template-canonical-body.md`. |
| `scripts/read-plugin-version.sh` | Supplies the best-effort larch plugin version row auto-injected into `run-statistics`. |
| `scripts/read-claude-model.sh` | Supplies the best-effort Claude model row auto-injected into `run-statistics`. |
| `scripts/timing-report.sh` | Writes the sentinel-bracketed `timing-report` fragment consumed by the anchor section. |
| `scripts/tracking-issue-read.sh` | Anchor-marker filter uses the same strict `<!-- larch:implement-anchor v1` prefix documented in `anchor-template-canonical-body.md`. |
| `skills/implement/references/pr-body-template.md` | Sibling slim-projection template for the PR body (Summary + Diagrams + Test plan + `Closes #<N>` + footer only); Phase 3+ the anchor comment is canonical for rich content. |
| `anchor-template-canonical-body.md` | Canonical body: anchor first-line marker, seed placeholder, canonical template (with `## Implementation Plan` synthesis heading), section markers, collapse priority. Loaded at Steps 0.5 and 11. |
| `anchor-template-execution-issues.md` | Execution-issues section format + compose-time sanitization rule. Loaded at Step 2 Q/A upserts and Step 11. |
| `anchor-template-oos-pipeline.md` | Full OOS pipeline procedure. Loaded at Step 9a.1. CI assertions (9a), (9d)-(9h) check this file. |
| `anchor-template-quick-mode.md` | Quick-mode anchor guidance. Loaded on quick-mode paths. |
| `scripts/test-implement-structure.sh` | CI assertions: (9a) pins the three load-bearing literals (`Accepted OOS (GitHub issues filed)`, `\| OOS issues filed \|`, `<details><summary>Execution Issues</summary>`) in `anchor-template-canonical-body.md`; (9b) pins ≥1 reference to `anchor-template-canonical-body.md` and ≥1 reference to `anchor-template-oos-pipeline.md` in SKILL.md; (9d)-(9h) pin Step 9a.1 procedure text in `anchor-template-oos-pipeline.md`; (16c) checks `anchor-template-canonical-body.md` for `## Implementation Plan`. |
