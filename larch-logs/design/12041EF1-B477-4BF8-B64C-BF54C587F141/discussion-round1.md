## Decision 1: Dependency on PR #3548 (issue #3511 scope-anchor pipeline)
- **Question**: Items 1, 2, 4, 6 target code that exists only on unmerged PR #3548. Design against post-merge main, fold into the open PR, or design only main-applicable items?
- **Resolution**: Assume #3548 merges first. Plan targets post-merge main; implementation of #3547 is blocked until PR #3548 lands. Plan states this hard dependency explicitly.
- **Source**: user

## Decision 2: Item 5 remedy for raw <context_file_N> inlining
- **Question**: Redact + untrusted framing, framing only, or redaction only for context files inlined by launch-claude-subprocess.sh?
- **Resolution**: Redact + untrusted framing — pipe each context file through redact-secrets.sh before inlining and add untrusted-data framing around the blocks.
- **Source**: user

## Decision 3: assess-plan-round.sh fallback when scope anchor missing
- **Question**: When the staged scope anchor (plan-review-scope-anchor.txt) is absent at Step 3.6 invocation, fail or fall back?
- **Resolution**: Prefer the staged scope anchor when present and non-empty; otherwise fall back to the existing feature-description.txt / IMPLEMENT_TMPDIR chain. All current Step 3.6 entry paths run after plan-review-loop.sh materializes the anchor, so the fallback is defensive only.
- **Source**: codebase

## Decision 4: Hard constraint — launch-claude-subprocess.sh consumers
- **Question**: What must not break when adding redaction/framing to the <context_file_N> path?
- **Resolution**: All existing Claude subprocess launch flows (review lanes, sketches, voters) must keep working; redaction must not corrupt non-secret content. redact-secrets.sh is already the repo-standard filter on publish paths, so reuse it unchanged.
- **Source**: codebase
