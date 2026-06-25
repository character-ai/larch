## Goal
Implement issue #5376: [IMPLEMENTING] [BUG] Final report omits Gantt timing charts from verbatim marker-body emission.

## Implementation Plan
## Summary

The `/implement` Step 17 orchestrator violates the verbatim-emit rule from `skills/shared/final-summary-emit.md` by condensing the `---LARCH-SUMMARY-FINAL-BEGIN---` / `---LARCH-SUMMARY-FINAL-END---` marker body instead of emitting it verbatim. In practice this drops the `### Round N reviewer timing` ASCII Gantt charts from the user-visible chat output. The Gantt charts are correctly generated and appear in the committed `larch-logs/implement/<RUN_ID>/final-summary.md`, so this is a display-only gap rather than a generation bug.

## Original report

no Gantt charts of review process displayed in final report

## Reproduction scenario

1. Run `/implement` or `/im` on any issue that goes through at least one full code-review round.
2. After the run merges, observe the Step 17 final report in chat.
3. The `## Review Phase Detail` section (table + `### Round N reviewer timing` ASCII bar charts + Top reviewers list) is either absent, wrapped in a `<details>` block with only the table, or otherwise condensed.
4. Compare against `larch-logs/implement/<RUN_ID>/final-summary.md` in the repo, which contains the full Gantt charts.

## Expected behavior

The orchestrator emits the full marker body verbatim as plain chat markdown per `skills/shared/final-summary-emit.md` rule 2: "Extract the marker body and emit its full body verbatim as plain chat markdown." and the shared rule: "Do NOT paraphrase, summarize, reorder, or add prose between bullets." This means the `### Round 1 reviewer timing` / `### Round 2 reviewer timing` ASCII Gantt blocks and the `**Top reviewers**` section all appear in the user-visible Step 17 chat output, exactly as they appear in the marker body.

## Observed behavior

The orchestrator condensed the marker body: the `## Review Phase Detail` section was wrapped in a `<details><summary>Review Phase Detail</summary>` HTML block, and only the summary table was included inside it. The `### Round N reviewer timing` ASCII bar charts and the `**Top reviewers**` section were omitted entirely. In the most recent run (RUN_ID `42A39E85-DAC2-466E-86F9-D5D6E98300E0`, PR #5373), the committed `final-summary.md` contained 30 Gantt-related lines including both timing charts, while the chat output showed none of them.

## Root cause analysis

The verbatim emit requirement exists in `skills/shared/final-summary-emit.md` but is not strongly enough enforced in `skills/implement/SKILL.md` Step 17 / NEVER #17. The current NEVER #17 prohibition focuses on preventing *added* free-form prose; it does not explicitly prohibit *condensing* or *omitting* parts of the marker body (such as wrapping sections in `<details>` or dropping Gantt blocks). The shared rule "Do NOT paraphrase, summarize, reorder, or add prose between bullets" in `final-summary-emit.md` does cover this case, but is not reinforced at the Step 17 call site in SKILL.md with enough specificity to prevent the orchestrator from treating the lengthy Gantt charts as optional or collapsible context.

## Evidence

- `larch-logs/implement/42A39E85-DAC2-466E-86F9-D5D6E98300E0/final-summary.md` line 34: `### Round 1 reviewer timing` — full ASCII bar chart present.
- `larch-logs/implement/42A39E85-DAC2-466E-86F9-D5D6E98300E0/final-summary.md` line 56: `### Round 2 reviewer timing` — full ASCII bar chart present.
- `python/closeout.py` lines 16-17: `SUMMARY_BEGIN = "---LARCH-SUMMARY-FINAL-BEGIN---"` / `SUMMARY_END = "---LARCH-SUMMARY-FINAL-END---"` — markers are correctly written.
- `python/closeout.py` lines 126-140: `_print_summary_markers()` correctly emits the full `summary-final.md` between the markers.
- `python/progress_report.py` lines 893-932: `_render_phase_gantt()` generates the `### Round N reviewer timing` sections with ASCII bars — no generation bug.
- `skills/shared/final-summary-emit.md` rule 2: "Extract the marker body and emit its full body verbatim as plain chat markdown." — rule exists but not enforced strongly enough at the Step 17 site.
- `skills/implement/SKILL.md` NEVER #17: prohibits *adding* recap prose but does not explicitly prohibit *condensing* or *omitting* Gantt sections from the marker body.

## Affected files

- `skills/implement/SKILL.md` — Step 17 / NEVER #17 guidance needs an explicit prohibition on wrapping, collapsing into `<details>`, or dropping Gantt/timing sections from the verbatim emit.
- `skills/shared/final-summary-emit.md` — The shared verbatim rule should be cross-referenced or strengthened at the `/implement` Step 17 callsite so the orchestrator does not treat long sections as optional.

## Suggested fix(es)

Add an explicit sentence to `skills/implement/SKILL.md` Step 17 (near the NEVER #17 anchor or the marker-first profile paragraph) such as:

> **Verbatim includes the full `## Review Phase Detail` block.** Do NOT wrap sections in `<details>`, collapse Gantt charts, or omit the `### Round N reviewer timing` ASCII bars or `**Top reviewers**` list. The full marker body — including all Gantt timing sections — must appear as plain chat markdown.

This closes the gap between the shared rule (which says "verbatim") and the call-site guidance (which currently focuses on prohibiting *added* prose rather than prohibiting *omitted* sections).

## Open questions

- Should the Gantt charts be emitted inside a code fence to prevent markdown renderers from mis-interpreting the `█` block characters?
- Is there a context-length concern when the Review Phase Detail is large (many rounds, many reviewers) that motivated the prior condensing, and if so should a separate `--no-gantt` mode be exposed at the orchestrator level for very long runs?

## Test plan
(no test plan section in plan-file)
