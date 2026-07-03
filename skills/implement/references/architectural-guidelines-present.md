# Architectural Guidelines Present Path

**Consumer**: `/implement` Architectural guidelines Phase A staging, loaded by the main agent after the prepare helper succeeds on the present-plus-ok branch.

**Contract**: Perform the prompt-side architectural-guidelines assessment for the minority path where parsed guidelines are present and the implementation diff was materialized successfully. Persist the staged assessment for Phase B without creating a durable pin in Phase A.

**When to load**: MANDATORY only after prepare stdout shows `ARCHITECTURAL_GUIDELINES_STATUS=present` with `ARCHITECTURAL_GUIDELINES_DIFF_STATUS=ok`. Do not load for `absent`, `invalid`, or present-with-diff-failure branches.

## Present-plus-ok assessment

Compare the parsed guideline entries and materialized diff using prompt-side judgment, then persist an orchestrator-authored assessment.

The assessment body must be either `Consulted ARCHITECTURAL_GUIDELINES.md; no deviations identified.` or a short deviation list with rationale.

Write the assessment body to `$IMPLEMENT_TMPDIR/architectural-guideline-assessment-draft.md`.

Persist it with the current post-7a `HEAD`, the materialized diff fingerprint, and base ref via the write-staged wrapper.

**⚠ Foreground required — do NOT set `run_in_background: true`.**

```bash
"$HOME/.cache/larch/sessions/implement-run-$PPID.sh" skills/implement/scripts/step-architectural-guidelines-write-staged.sh architectural-guideline-assessment-draft.md
```

After the write-staged wrapper succeeds, print the clean or deviation note to chat.

When the note indicates deviations, also append it under `Warnings` in `$IMPLEMENT_TMPDIR/execution-issues.md`.

For the clean case (no deviations identified), omit the `Warnings` append.

Do not call `architectural-guidelines pin-note-from-staged` in Phase A.

Continue to Step 8 only after the present-plus-ok assessment and staged persistence complete successfully.

Sibling contract: `skills/implement/scripts/step-architectural-guidelines-write-staged.md`.
