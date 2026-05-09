# Triage and Classification — Digest

**Consumer**: `/fix-issue` Steps 3 (Triage) and 4 (Classify). Common-case reference; load full `triage-classification.md` only when composing the not-material closure explanation (need detailed rationale) or when genuinely uncertain about a classification edge case.

**Contract**: Condensed decision guide covering the triage checklist, `--close-class` mapping, and the PR / NON_PR / SIMPLE / HARD classification rules. Full `triage-classification.md` carries the not-material closure flow step-by-step detail, complete rationale for each decision branch, and the `--quick` short-circuit prose.

**When to load**: before Step 3 (Triage) or Step 4 (Classify). For the common path (issue is material → classify intent and complexity), this digest is sufficient. Load full `triage-classification.md` when composing the not-material closure explanation or when uncertain about a classification edge case.

---

## Triage checklist (Step 3)

Check via Read/Grep/Glob:
- Issue already fixed by recent commits?
- Referenced code/feature still present in the codebase?
- Valid bug/feature request (not filed in error)?
- For investigation/review-only issues: is the **task itself** still relevant (targets, scope, constraints meaningful)?

**If not material**: compose a detailed explanation + research summary. Pick `--close-class` from:
- already-fixed (bug fixed / feature added since filing) → `done`
- duplicate-of #N (restates existing issue) → `duplicate`
- superseded-by #N (replaced by later issue/PR) → `superseded`
- invalid / not-a-bug / false-positive (behavior by design, filed in error) → `false-positive`

SKILL.md Step 3 then invokes `issue-lifecycle.sh close --close-class <value>`, `tracking-issue-write.sh rename --state done` (best-effort), optional `post-issue-slack.sh`, and skips to Step 8.

## Classification rules (Step 4)

**Dimension 1 — Intent** (`PR` vs `NON_PR`):
- `PR`: code change → pull request. Default when genuinely ambiguous.
- `NON_PR`: research/review → issues or written report. Pick when the issue explicitly forbids a PR or mandates research/issues as the deliverable.

**Dimension 2 — Complexity** (only when `INTENT=PR`):
- `SIMPLE`: ≤2 files, obvious solution, no architectural decisions.
- `HARD`: everything else. Default when uncertain.
- `--quick` short-circuit: forces `COMPLEXITY=SIMPLE` when `quick_mode=true` and `INTENT=PR`.
