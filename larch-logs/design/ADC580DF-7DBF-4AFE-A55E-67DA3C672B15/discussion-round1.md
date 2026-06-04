## Decision 1: Fold `review_budget` elimination into #3418
- **Question**: `review_budget` is always `full` (both SIMPLE and HARD set it); its `quick` value is dead. Eliminate it as part of this issue, or keep #3418 narrow and file a separate cleanup?
- **Resolution**: Fold the `review_budget` elimination into #3418. It is vestigial (NOT a SIMPLE/HARD synonym — that signal is `design_classification`), and removing it directly simplifies the validate-fold.
- **Source**: user

## Decision 2: Eliminate `--force-validate`; validation unconditional
- **Question**: With `review_budget` gone, `--force-validate` (which only overrode the `quick` skip) is meaningless. Remove it, or keep as a harmless no-op?
- **Resolution**: Remove `--force-validate` entirely. Plan-command validation runs unconditionally on every `/design` plan emit and before publish.
- **Source**: user

## Decision 3: Smart validator-failure handling (auto-repair -> escalate), shared handler
- **Question**: On validation failure, keep today's always-prompt 3-option handler, or have the agent attempt a work-around first and ask the user only when warranted? Apply to just Step 5c or the shared handler (all four sites)?
- **Resolution**: Rewrite the shared `### Plan command validator failure (shared)` handler used by Step 2b, Gate B, discussion-round2, and Step 5c. New flow: the agent diagnoses the root cause from the defect log, auto-fixes the plan and re-validates when confident (no prompt; logged), and escalates via AskUserQuestion — explaining the root cause and offering context-specific options (proposed fix / accept-as-false-positive / edit-myself / cancel) — only when the fix warrants human judgment.
- **Source**: user

## Decision 4: design-publish.sh `--skip-validate` + auto-repair cap (implementation)
- **Question**: How does publish proceed past validation on the explicit "proceed anyway" path, and how is auto-repair bounded?
- **Resolution**: `design-publish.sh` gains `--skip-validate`, used only for the explicit accept / proceed-anyway path (a successful auto-repair re-validates normally and passes, so no bypass is needed there). Auto-repair is capped at 2 attempts before escalating to the user.
- **Source**: user

## Hard constraints / non-goals
- Keep `design_classification` (SIMPLE vs HARD) in `/design` — it is the real tier signal; only `review_budget` is removed.
- Preserve the foreground-required invariant on the Step 5c publish call (no `run_in_background`).
- Preserve the `design-publish.sh` `defects-found` hand-back contract (made smarter, not removed).
- composed-plan validation stays Tier 2 only (Tier 3 dry-run remains disabled for `composed-plan.md`).
- All offline harnesses + `make lint` stay green; update `test-design-publish.sh`, `test-design-structure.sh`, `test-design-postplan-emit.sh`, `test-write-run-params.sh` as needed.
- Scope stays within `/design`; `/implement` already dropped its SIMPLE/HARD split and does not read `review_budget`.
