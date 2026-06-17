# Review Round 1

- Mode: `diff`
- 2 accepted, 2 rejected (1 neutral)

## Accepted Findings

### FINDING_1: Step 17 `--no-print-stdout` suppresses handoff on unchanged-byte post-persist failure
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `step-17.sh` `--no-print-stdout` treats byte inequality (`cksum`) as the only fresh-body signal. When Ship pre-writes `summary-final.md`, Step 17 re-renders identical bytes, and a post-write stamp/upsert failure yields `STEP17_RC!=0` with no markers emitted. Step 18b then withholds `EMIT_BODY` when `WFR_RC!=0`, so the operator gets no top-chat summary despite a valid on-disk `summary-final.md`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Extend handoff for post-write Python failures even when bytes are unchanged, or allow Step 18b Read-emit when `.step17-emitted` is absent and `summary-final.md` is non-empty
  - From codex-specialist-edge-cases-output.txt: Move or remove the old summary before rendering, treat a newly created non-empty summary as fresh, and restore the old file only when no fresh body was written.


### FINDING_13: `print_summary_markers` ignores `cat`/`touch` failures after `set +e`
- **Reviewer(s)**: dyn-bash-portability-output.txt
- **Severity**: important
- **Concern**: `print_summary_markers` in `step-16-17.sh` runs after `set +e` and never checks `cat` or `touch` status. A read or sentinel write failure can still print the end marker and touch `.step17-printed`, letting the orchestrator treat a truncated marker body as a complete NEVER #17 handoff, write `.step17-emitted`, and suppress the Step 18b Read fallback.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-portability-output.txt: run the marker block with errexit enabled (or explicitly test `cat`/`touch` rc) and only touch `.step17-printed` after the full `summary-final.md` body is written between the markers.


