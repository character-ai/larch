## Goal
Add a mandatory continuation directive to /design Step 5b and update NEVER #12 in /implement to prevent post-design boundary halts

## Implementation Plan

### Goal
Strengthen the anti-halt signal at the post-/design boundary so the `/implement` orchestrator cannot end its turn after `/design` returns, even when the `MANIFEST_WRITTEN=<path>` line appears to look like a done signal.

### Three targeted prose changes (no script changes needed)

**1. `skills/design/SKILL.md` Step 5b — add mandatory continuation directive**

After the current last instruction in Step 5b ("Do NOT write any farewell message such as..."), add a positive directive that instructs the `/design` orchestrator to print a `➡️` continuation directive as the final output line when nested inside `/implement`:

```
When `SESSION_ENV_PATH` is non-empty (nested `/implement` mode) and `MANIFEST_EXPORT_OK=true`,
print the following as the **final output line** of this skill — after repeating warnings (or
immediately after cleanup when there are none):

`➡️ 5: cleanup — manifest written; NEXT REQUIRED: parent /implement must invoke
post-design-boundary.sh immediately as a Bash tool call — do NOT end the orchestrator turn`

This directive replaces the bare `MANIFEST_WRITTEN=<path>` as the terminal visible signal
from `/design`. It is unambiguously an input to the next step, not a completion signal.
```

**2. `skills/implement/SKILL.md` anti-halt reminder (line ~14) — update "Critical boundary" sentence**

Change the current text:
> after `/design` returns (including when its output ends with `MANIFEST_WRITTEN=<path>`)

To:
> after `/design` returns (its output ends with the `➡️ 5: cleanup — manifest written; NEXT REQUIRED:` directive — or with a bare `MANIFEST_WRITTEN=<path>` line from an older run without the directive)

**3. `skills/implement/SKILL.md` NEVER #12 — update to reference the new directive**

Update NEVER #12's "Why" explanation to name both the old and new terminal patterns, and the "How to apply" sentence to name the exact observable symptom the rule targets.

### Files to modify
- `skills/design/SKILL.md` — Step 5b section (near end of file, line ~1011)
- `skills/implement/SKILL.md` — anti-halt reminder (line ~14) and NEVER #12 section (line ~58-61)


## Test plan
Run `/relevant-checks` after changes to confirm markdownlint, agent-lint pass.
