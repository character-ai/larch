## Decision 1: Secondary stdin fix scope
- **Question**: Should `</dev/null` stdin redirection be in this PR?
- **Resolution**: Yes, include in this PR.
- **Source**: user

## Decision 2: Files in scope
- **Question**: Which files need changes?
- **Resolution**: `review-design-step3-loop.sh` (primary), `design-step3-review.sh` (observability), `launch-review.sh` (stdin). Sibling `.md` files updated in same PR.
- **Source**: codebase
