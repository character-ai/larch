## Proposed Design Outline

### Goals
- Collapse `/implement` Steps 16, 16a, 17 into one Bash call via a new `step-16-17.sh` wrapper.
- Print `summary-final.md` between stable BEGIN/END markers so the orchestrator re-emits the body verbatim from captured output, with no separate Read call.
- Preserve the verbatim-emission contract: full body, no paraphrase, `.step17-emitted` written only after emission.

### Non-goals
- No fold of the `.step17-emitted` write or the Step 18b emit path (the separate Step 18 issue).
- No change to the per-agent cost line or the no-free-form-recap rule (NEVER #17 intent unchanged).
- No change to per-step behavior contracts: rejected-findings silent-skip, Slack best-effort, Step 17 tool-failure append.

### Approach sketch
- New `skills/implement/scripts/step-16-17.sh` runs rejected-findings, best-effort Slack announce, then final report in sequence.
- The wrapper prints `summary-final.md` between `---LARCH-SUMMARY-FINAL-BEGIN---` / `---LARCH-SUMMARY-FINAL-END---` and writes `.step17-printed`.
- `skills/implement/SKILL.md` Steps 16/16a/17 collapse to one fence; orchestrator extracts the marked body, emits it verbatim, then writes `.step17-emitted`; breadcrumbs preserved.
- Reword NEVER #17 and the anti-halt terminal boundary to name the wrapper.

### Surfaces in scope
- `skills/implement/scripts/step-16-17.sh` plus `.md` sibling; `step-16.sh` / `step-17.sh` (sequenced or folded).
- `skills/implement/SKILL.md`: Steps 16-17 region, NEVER #17, anti-halt terminal boundary, helper list.
- `scripts/test-implement-fence-shape.sh`, `scripts/test-implement-structure.sh` (fence / step-count pins).

### Open questions
- Compose (wrapper calls `step-16.sh` + `step-17.sh`; modify step-17 for markers) vs fold (wrapper owns all three; retire step-16/17). Recommend compose for minimal churn.
- Marker token name `---LARCH-SUMMARY-FINAL-BEGIN/END---` vs aligning with `/design`'s `LARCH_FINAL_SUMMARY_*`.
