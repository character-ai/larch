### OOS_1:
- **Description**: Sibling `*.md` contract files are not listed for cutover. Scenario: `implement-bootstrap.md`, `design-publish.md`, `implement-finalize.md`, and similar files still name retired helpers until the grep sweep; grep should catch them, but contract docs can stay stale briefly
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/implement/scripts/test-implement-bootstrap.md
- **Phase**: design

### OOS_2:
- **Description**: [SCOPE-REDUCTION] Stream-placement matrix is very large (three rows × six verbs). Scenario: Parity is valuable, but duplicating near-identical stdout/stderr cases across six mains increases maintenance without new behavioral coverage beyond one shared parametrized table
- **Reviewer**: Cursor-Arch
- **Severity**: nit
- **Focus area**: risk-integration
- **Location**: python/test_tracking_issue.py
- **Phase**: design

### OOS_1:
- **Description**: [SCOPE-REDUCTION] create-issue and mark-false-positive have no live in-repo callers outside the retiring shell helpers and harnesses. Scenario: After parity cutover these verbs remain CLI surface with zero production call sites while issue create flows use other python/cli.py issue verbs. Maintaining full six-verb stream matrices for dead entry points inflates an already ~2750-line diff
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/tracking_issue.py:create_issue_main
- **Phase**: design

### OOS_2:
- **Description**: skills/implement/SKILL.md invariant #2 still names tracking-issue-summary.sh but the plan only lists an emergency-preflight edit for that file. Scenario: The stale helper name is documentation drift only; grep sweep should catch it, but the invariant prose will keep citing a deleted script until updated
- **Reviewer**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: skills/implement/SKILL.md:26
- **Phase**: design

### OOS_1:
- **Description**: Stale tracking-issue-write.sh mention in manifest sanitization prose. Scenario: codex-manifest-schema.md still cites tracking-issue-write.sh as a secrets redaction backstop. Grep sweep should catch it, but it is not operator-critical for F3e cutover.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: skills/implement/references/codex-manifest-schema.md:63
- **Phase**: design

### OOS_2:
- **Description**: Library upsert_summary keeps single-newline framing while shell summary uses marker blank line content. Scenario: upsert_summary() still routes through _upsert_marker_comment with f"{marker}\n{body}". Shell tracking-issue-summary.sh uses marker\n\ncontent. No live consumer calls the library helpers after cutover, so this is latent API drift, not a shipping regression.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: correctness
- **Location**: python/tracking_issue.py:212-227
- **Phase**: design

