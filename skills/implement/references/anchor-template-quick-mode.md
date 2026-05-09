# Anchor Comment — Quick-Mode Guidance

**Consumer**: `/implement` quick-mode paths (Step 7a and anchor-section composition under `quick_mode=true`). Load when writing anchor sections in quick mode to apply the correct per-section fallback text.

**Contract**: quick-mode anchor guidance — per-section fallback text for `plan-review-tally`, `code-review-tally`, and `diagrams` sections when `/design` and `/review` are skipped. Keeps the anchor-comment shape stable across mode-selection so Phase 3+ consumers can parse by section marker regardless of mode.

**When to load**: MANDATORY at Step 7a on quick-mode paths. Do NOT load outside quick-mode contexts.

**Sibling files**:
- `anchor-template-canonical-body.md` — canonical template + section markers
- `anchor-template-oos-pipeline.md` — OOS pipeline (Step 9a.1)
- `anchor-template-execution-issues.md` — execution-issues section format (Step 2)
- `anchor-comment-template.md` — thin overview

---

## Quick-mode anchor guidance

Quick mode (`/implement --quick`) skips `/design` and `/review`, so the `plan-review-tally` and `code-review-tally` sections have no standard content. Quick-mode consumers should:

- Leave the `plan-review-tally` and `code-review-tally` sections present (with section markers preserved) but populate the interior with `(plan review skipped — quick mode)` / `(single-reviewer loop — no voting panel)` as appropriate.
- Populate `diagrams` with only the Architecture Diagram (Code Flow Diagram is skipped in quick mode per SKILL.md Step 7a).
- All other sections are populated normally.

This keeps the anchor-comment shape stable across mode-selection so a Phase 3+ consumer can parse by section marker regardless of mode.
