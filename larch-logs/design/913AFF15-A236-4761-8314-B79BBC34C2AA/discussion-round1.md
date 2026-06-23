## Decision 1: Consolidation target location
- **Question**: Where should the single consolidated final-summary marker-extraction instruction live?
- **Resolution**: New shared reference file `skills/shared/final-summary-emit.md`.
- **Source**: user

## Decision 2: Repoint scope
- **Question**: Which occurrences should be replaced with a pointer to the single source?
- **Resolution**: The 4 full near-verbatim copies (Step 0b cancel-route final-summary text, the Final summary block, Step 5c item 5, Step 5c abort path) PLUS the brief Anti-halt reminder mention (line 29) and other partial paraphrases/cross-refs.
- **Source**: user

## Decision 3: Behavioral-preservation hard constraint (must not break)
- **Question**: What must not change?
- **Resolution**: No behavioral change. Each emit site keeps its exact runtime behavior: the site-specific source (which completed task/script output the `LARCH_FINAL_SUMMARY_BEGIN`/`END` markers come from — `design-step5c.sh` vs `design-step-final-summary.sh`), the site-specific after-action (continue vs. stop-immediately vs. emit-before-footer), and the hard rule that the body is written as plain orchestrator text, never via a Bash/Python tool call. The shared reference holds the common core (marker extraction + Read-fallback + verbatim/no-paraphrase + `REPORT_GATE_SIDECARS_FILE` follow-on); site-specific glue stays inline at each site.
- **Source**: issue (Acceptance: "No behavioral change")

## Decision 4: Scope boundary — design-only, doc-hygiene, not md-to-py
- **Question**: Is this a Python migration? What files are in scope?
- **Resolution**: Doc-hygiene/readability only. In scope: `skills/design/SKILL.md` and the new `skills/shared/final-summary-emit.md`. The emit must stay orchestrator-side because tool output lands in a collapsible block; no logic moves to Python. Not part of the md-to-py-IV umbrella.
- **Source**: issue (Notes)
