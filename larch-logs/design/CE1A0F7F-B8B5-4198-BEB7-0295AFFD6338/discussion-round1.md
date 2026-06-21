## Decision 1: Substantive change is /design-only
- **Question**: The issue asks to fix diagram behavior in both /design and /implement. Investigation shows /implement already keeps its diagram out of chat and run logs (tracking issue only), and /design already excludes the diagram from run logs. What is the actual in-scope change set?
- **Resolution**: Substantive code changes land in /design: (a) generate the Architecture Diagram AFTER Gate C approval, not before; (b) stop emitting the diagram to chat. /implement chat-emission and both run-log paths are already compliant; treat them as verify-only and add regression tests to lock them in. No behavior change to /implement diagram routing.
- **Source**: user

## Decision 2: Keep the Code Flow Diagram in the /implement PR body
- **Question**: /implement embeds the Code Flow Diagram in the PR body (collapsed <details>). "Only end up in the tracking issue" could mean removing it from the PR body. Remove or keep?
- **Resolution**: Keep it in the PR body. "Not output to chat" is interpreted narrowly: the complaint is chat clutter, not the collapsed PR-body block, which is useful to reviewers. No PR-body change in /implement.
- **Source**: user

## Decision 3: Preserve existing diagram safeguards (hard constraints)
- **Question**: What current diagram behaviors must not break when moving /design generation after approval?
- **Resolution**: Preserve: (a) the DIAGRAM_REQUIRED=false skip for non-architectural plans (architecture-diagram.skipped marker drives the 5c clear-architecture path); (b) non-blocking sanitizer/generation failure (an approved plan must still publish even if the diagram fails); (c) the existing Step 5c larch:diagrams upsert path in design_publish.py (consumes architecture-diagram.md / architecture-diagram.skipped); (d) Gate C re-entry loops (Discuss further / Re-run review panel) must not regenerate the diagram until the user picks Approve.
- **Source**: codebase

## Decision 4: Tracking issue remains the diagram's sole live destination
- **Question**: Should /design still generate and publish the Architecture Diagram at all?
- **Resolution**: Yes. Keep generating it and upserting it to the tracking-issue larch:diagrams comment. The change is timing (after approval) and visibility (no chat), not removal.
- **Source**: user
