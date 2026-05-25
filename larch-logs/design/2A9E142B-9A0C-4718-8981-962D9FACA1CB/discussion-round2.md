## Decision 9: OOS_3 security mitigation — redact close-comment body
- **Question**: How should the `decompose-file-issues.sh close-original` close-comment be redacted before posting via `gh issue comment`?
- **Resolution**: Pipe the composed close-comment body through `scripts/redact-secrets.sh` before passing it to `gh issue comment --body-file`. This mirrors the outbound redaction that `skills/issue/scripts/create-one.sh` applies to issue bodies. The mitigation adds ~5 lines to the plan body and an inline behavior note to `decompose-file-issues.sh` close-original section.
- **Source**: user (Gate B/C round 2 — OOS_3 from Cursor-dyn-script-contract reviewer)
