## Decision 1: Fix approach for `_architectural_guidelines_section`
- **Question**: Option A (minimal, check post-merge context inline) or Option B (add `note_readable_any_head` helper)?
- **Resolution**: Option B — add `note_readable_any_head(implement_tmpdir) -> bool` to `architectural_guidelines.py` that checks only `STATUS == "present"` without HEAD_SHA equality. Use it as a fallback in `_architectural_guidelines_section`.
- **Source**: user

## Decision 2: Clear spurious DROPPED_NOTE_ARTIFACT
- **Question**: Should the fix also clear the spurious `DROPPED_NOTE_ARTIFACT` file when the run outcome is `merged`?
- **Resolution**: Yes — when post-merge context is detected, also remove the spurious drop-notice artifact so teardown logs are clean.
- **Source**: user

## Decision 3: Phase B pin scope
- **Question**: Is `_pin_architectural_guidelines_note_best_effort` in step-16-17 also in scope?
- **Resolution**: Yes — guard that function so it does not attempt to re-pin on main HEAD after local cleanup.
- **Source**: user
