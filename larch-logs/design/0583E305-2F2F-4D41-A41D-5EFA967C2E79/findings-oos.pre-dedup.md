### OOS_1:
- **Description**: [SCOPE-REDUCTION] Python ports untrusted-block, scope-anchor, and design-tmpdir logic inline while bash libs remain for plan-review-loop.sh, aggregate-findings.sh, and other survivors. Scenario: Future edits to the bash libs (#3780 deferred consumers) can silently desync Python renderers until a prompt regression surfaces
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/rendering.py:22-26,scripts/lib-untrusted-block.sh
- **Phase**: design

### OOS_2:
- **Description**: Default python/cli.py ship pr sanitizes via pr_body.sanitize_fragment (object API) while design/implement/legacy ship-pr paths move to mermaid sanitize (KV contract stream); plan does not require unifying the two surfaces. Scenario: B6 can ship correctly with dual sanitizer entrypoints; long-term drift between PR-body rejection tokens and SKILL KV parsers is possible but pre-existing in spirit
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: correctness
- **Location**: python/pr_body.py:192-239,plan.txt:16-17
- **Phase**: design

