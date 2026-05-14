## Goal
Fix voting-protocol.md ballot format drift to match actual ### FINDING_N: block grammar

## Implementation Plan

### Goal
Fix the ballot-format drift in `skills/shared/voting-protocol.md` so the documented format matches what `ballot-parse.sh` and `tally-plan-review.sh` actually parse.

### Problem
- `voting-protocol.md` "Ballot Format" section shows plain-text `FINDING_1: <description>` format
- `ballot-parse.sh` only recognizes `### FINDING_N:` markdown heading blocks
- `tally-plan-review.sh` parses `### FINDING_N:` (in-scope) and `### OOS_N:` (out-of-scope) blocks
- The "OOS on the Ballot" section shows `OOS_1: [OUT_OF_SCOPE] ...` (plain-text), matching neither parser

### Files to modify
- `skills/shared/voting-protocol.md` — single file, two sections to update

### Changes

**Section 1: "Ballot Format" (lines 15-29)**

Replace the inner code-block content showing:
```
FINDING_1: <reviewer attribution> — <finding description>
FINDING_2: <reviewer attribution> — <finding description>
...
```

With the actual `### FINDING_N:` heading block grammar:
```markdown
### FINDING_1: <short title>
- **Reviewer**: <reviewer attribution>
- **Concern**: <finding description>
- **Suggested revision**: <what to change>

### FINDING_2: <short title>
- **Reviewer**: <reviewer attribution>
- **Concern**: <finding description>
- **Suggested revision**: <what to change>
```

Also update the surrounding prose to note the heading-block format (remove the old framing that said "Format the ballot as:").

**Section 2: "OOS on the Ballot" (lines 211-217)**

Replace the inner code-block showing:
```
OOS_1: [OUT_OF_SCOPE] Code — <description of pre-existing issue>
```

With the actual `### OOS_N:` heading block used by `tally-plan-review.sh`:
```markdown
### OOS_1: <short title of pre-existing issue>
- **Reviewer**: <reviewer attribution>
- **Concern**: <description of pre-existing issue>
```

Add a note that `/review` code review uses `FINDING_N: [OUT_OF_SCOPE]` prefix (not `OOS_N:`) in the ballot file, detected by `ballot-parse.sh`.

### Testing strategy
Run `/relevant-checks` after the edit:
- `pre-commit` will validate markdown lint (markdownlint)
- `agent-lint` will check the skill file

Verify the changed sections look correct by reading the edited file.

diff_lines: 25

## Test plan
(no test plan section in plan-file)
