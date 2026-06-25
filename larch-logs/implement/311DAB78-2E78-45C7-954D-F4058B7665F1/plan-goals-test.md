## Goal
Implement issue #5365: [IMPLEMENTING] [BUG] architectural-guidelines Phase A rm loop triggers dangerous-rm safety prompt.

## Implementation Plan
## Summary

During `/implement` Architectural guidelines Phase A staging, the SKILL.md instructs the orchestrator to clear a list of stale artifact files before calling `step-architectural-guidelines-read.sh`. The instruction provides no safe mechanism for the clearing, so the orchestrator writes a bare `for f in ...; do rm -f "$IMPLEMENT_TMPDIR/$f"; done` loop. Claude Code's built-in safety check detects `rm -f "$IMPLEMENT_TMPDIR/$f"` as a "Dangerous rm operation on possibly-empty variable path" and prompts the user for confirmation on every `/implement` run.

## Original report

The question appeared during `/implement --emergency 5351` at the Architectural guidelines Phase A staging step:

```
Dangerous rm operation on possibly-empty variable path: "$IMPLEMENT_TMPDIR/$f"

Do you want to proceed?
❯ 1. Yes
   2. No
```

The relevant orchestrator Bash block:
```bash
for f in architectural-guideline-warnings.md architectural-guideline-warnings.meta.env \
  architectural-guideline-staged-assessment.md architectural-guideline-staged-assessment.env \
  architectural-guideline-materialized-diff.txt architectural-guideline-note.md \
  architectural-guideline-note.meta.env; do
  rm -f "$IMPLEMENT_TMPDIR/$f"
done
bash "$IMPLEMENT_TMPDIR/larch-run.sh" skills/implement/scripts/step-architectural-guidelines-read.sh
```

## Reproduction scenario

Run `/implement` (any issue) on a fresh session to reach the Architectural guidelines Phase A staging step. Every run triggers the prompt because the SKILL.md unconditionally lists artifacts to clear before `step-architectural-guidelines-read.sh`.

## Expected behavior

No permission prompt. Artifact clearing is handled safely inside a script or Python CLI so the orchestrator never needs to write bare `rm -f "$VAR/$f"` loops.

## Observed behavior

Claude Code's built-in safety check fires on `rm -f "$IMPLEMENT_TMPDIR/$f"` inside the for loop, presenting a "Dangerous rm operation on possibly-empty variable path" confirmation dialog.

## Root cause analysis

`skills/implement/SKILL.md` lines 746-752 list 7 specific files to clear at Phase A entry but give the orchestrator no mechanism to do so safely. The orchestrator constructs a `rm -f "$IMPLEMENT_TMPDIR/$f"` for-loop, which Claude Code's built-in safety heuristic flags because `$IMPLEMENT_TMPDIR` could be empty in theory, turning `"$IMPLEMENT_TMPDIR/$f"` into a root-level path like `/architectural-guideline-warnings.md`.

The `step-architectural-guidelines-read.sh` script already calls `python/cli.py architectural-guidelines invalidate --implement-tmpdir "$IMPLEMENT_TMPDIR"`. The artifact clearing belongs in that script or the Python CLI, not in orchestrator-side Bash.

## Evidence

- `skills/implement/SKILL.md` lines 746-752: lists artifacts to clear, provides no helper command.
- `skills/implement/scripts/step-architectural-guidelines-read.sh`: calls `architectural-guidelines invalidate` then `architectural-guidelines read` — the natural place to add clearing.
- `python/cli.py architectural-guidelines invalidate`: already exists; could be extended or a new `clear-staged` verb added.
- No `python/cli.py architectural-guidelines clear*` verb exists today; the orchestrator is left with no safe option.

## Affected files

- `skills/implement/SKILL.md` — Phase A staging section (lines 746-752): instruction to clear artifacts with no safe helper
- `skills/implement/scripts/step-architectural-guidelines-read.sh` — natural home for the clearing
- `python/cli.py` (`architectural-guidelines` domain) — would need a new verb or extension to `invalidate`

## Suggested fix(es)

**Option A (preferred):** Move artifact clearing into `step-architectural-guidelines-read.sh` — have it `rm -f` the 7 named files using a guarded pattern (e.g., `[ -n "$IMPLEMENT_TMPDIR" ] && rm -f "$IMPLEMENT_TMPDIR/architectural-guideline-*.md" ...`) before calling `architectural-guidelines read`. Update SKILL.md to remove the orchestrator-side clearing instruction.

**Option B:** Add a `python/cli.py architectural-guidelines clear-staged --implement-tmpdir "$IMPLEMENT_TMPDIR"` verb that handles all 7 files with a non-empty guard, and update SKILL.md to call it.

Either fix eliminates the orchestrator for-loop and the resulting safety prompt.

## Open questions

- Should the `invalidate` verb be extended to also clear these 7 files, or is a new `clear-staged` verb cleaner?
- Is there a reason the clearing must be orchestrator-side rather than inside `step-architectural-guidelines-read.sh`?

## Test plan
(no test plan section in plan-file)
