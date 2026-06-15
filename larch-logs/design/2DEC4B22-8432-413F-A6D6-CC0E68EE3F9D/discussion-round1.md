## Decision 1: Vendor precedence swap
- **Question**: Simple swap (Claude subprocess primary) or true waterfall?
- **Resolution**: Simple swap. When LARCH_DESIGN_DRAFTER is unset, prefer Claude subprocess. On failure, fall back to inline. Codex reachable via LARCH_DESIGN_DRAFTER=codex.
- **Source**: user

## Decision 2: Cursor in drafter
- **Question**: Was Cursor in the user's waterfall description intentional?
- **Resolution**: No. Cursor stays review-only. The drafter change is Codex↔Claude swap only.
- **Source**: user

## Decision 3: Claude model
- **Question**: Which Claude model for the drafter?
- **Resolution**: claude-opus-4-8 (change default from claude-fable-5 to claude-opus-4-8).
- **Source**: issue title + body

2 decisions resolved.
