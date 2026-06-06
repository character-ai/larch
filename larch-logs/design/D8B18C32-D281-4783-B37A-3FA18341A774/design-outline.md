## Proposed Design Outline

### Goals
- Make `/implement` first-detection stall filing actually create the GitHub issue. Today `/issue --input-file` parses 0 items and silently no-ops.
- Fix by reuse: route filing through the existing, tested `issue-input-file` subcommand instead of adding new heading-rendering code.

### Non-goals
- No change to `bug-body` / `bug-comment` body composition or the consumer-repo "Action required" verbatim chat-print path.
- No change to `skills/issue/scripts/parse-input.sh` or `/issue --input-file` 0-item behavior (stays clear of in-flight #3550 / #3547).

### Approach sketch
- Edit `stall-recovery.md` step 4: after `bug-body`, call `issue-input-file --classification-file <class> --body-file <bug-body output>` to synthesize the `### [Bug] /implement stall: <class> at <step>` heading.
- Pass that `INPUT_FILE` to `/larch:issue --input-file` — not the raw heading-less `bug-body` file.
- Keep the `DRY_RUN_DECISION` short-circuit and the `attempt_count==0` + non-terminal first-detection gate unchanged.

### Surfaces in scope
- `skills/implement/references/stall-recovery.md` — step 4 filing wiring (prose procedure the orchestrator follows).
- `skills/implement/scripts/test-stall-recovery-report.sh` — regression pin: `issue-input-file` output parses to `ITEMS_TOTAL=1` under `parse-input.sh`.
- Doc/structure sync: `test-stall-recovery-report.md`; optionally a `test-implement-structure.sh` assertion that step 4 wires `issue-input-file`.

### Open questions
- None.
