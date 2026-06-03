---
paths:
  - ".claude/skills/audit-runs/SKILL.md"
  - ".claude/skills/audit-runs/scripts/audit-close-priors.md"
  - ".claude/skills/audit-runs/scripts/audit-close-priors.sh"
  - ".claude/skills/audit-runs/scripts/test-audit-runs.sh"
  - ".claude/skills/combine-issues/SKILL.md"
  - ".claude/skills/combine-issues/scripts/apply-combination.sh"
  - "AGENTS.md"
  - "BASH_AUTHORING.md"
  - "SECURITY.md"
  - "scripts/clarify-comment-post.md"
  - "scripts/clarify-comment-post.sh"
  - "scripts/create-pr.md"
  - "scripts/create-pr.sh"
  - "scripts/design-log-publish.md"
  - "scripts/design-log-publish.sh"
  - "scripts/named-block-write.md"
  - "scripts/named-block-write.sh"
  - "scripts/test-design-log-publish.sh"
  - "scripts/gh-pr-body-update.md"
  - "scripts/gh-pr-body-update.sh"
  - "scripts/plan-block-write.md"
  - "scripts/plan-block-write.sh"
  - "scripts/ship-pr.md"
  - "scripts/ship-pr.sh"
  - "scripts/tracking-issue-summary.md"
  - "scripts/tracking-issue-summary.sh"
  - "scripts/tracking-issue-write.md"
  - "scripts/tracking-issue-write.sh"
  - "skills/design/SKILL.md"
  - "skills/design/references/l3-velocity-deferral-comment.txt"
  - "skills/design/scripts/decompose-file-issues.md"
  - "skills/design/scripts/decompose-file-issues.sh"
  - "skills/implement/SKILL.md"
  - "skills/issue/SKILL.md"
  - "skills/issue/scripts/create-one.md"
  - "skills/issue/scripts/create-one.sh"
  - "skills/report-tokens/scripts/run-analysis.md"
  - "skills/report-tokens/scripts/run-analysis.sh"
  - "skills/review-and-fix/scripts/review-and-fix.md"
  - "skills/review-and-fix/scripts/review-and-fix.sh"
---

# gh `--body` / `--notes` - File-Backed Only

Every `gh ... --body` or `gh ... --notes` invocation in this repository must pass
the content through a file-backed interface.

## Why

Issue #2830 came from composing a multiline PR body inside command substitution:

```bash
gh pr create --body "$(cat <<'EOF'
...
EOF
)"
```

That shape is fragile in assistant-authored Bash. Nested quoting, heredoc
delimiters, and command-substitution boundaries can be corrupted before `gh`
receives argv, producing parse errors instead of a PR. See `BASH_AUTHORING.md`
section 2 for the broader heredoc and quoting context.

## Required Pattern

Use one of these shapes:

```bash
gh issue comment 123 --body-file "$body_file"
gh release create v1.2.3 --notes-file "$notes_file"
```

Write assistant-authored bodies with the Write tool when working interactively.
Shell scripts should use `mktemp`, write the content with `printf '%s'` or a
quoted-delimiter heredoc redirected to the file, and clean the file in an EXIT
trap or immediately after the `gh` command.

For small stable bodies, stdin is also acceptable:

```bash
gh issue comment 123 --body-file - <<'EOF'
Short fixed comment.
EOF
```

Process substitution is also acceptable when it preserves the same file-backed
boundary:

```bash
gh issue comment 123 --body-file <(printf '%s' "$body")
```

## Forbidden Patterns

Do not use any of these forms:

```bash
gh pr create --body "$(cat <<'EOF'
...
EOF
)"
gh issue comment 123 --body "inline text"
gh release create v1.2.3 --notes "inline text"
gh release create v1.2.3 --notes "$(generate_notes)"
```

Inline `--body` / `--notes` is forbidden even when the text is short. The local
rule is intentionally simpler than the failure mode: always use the file-backed
variant so authors do not have to reason about which body is "safe enough".

## PR Creation

For `gh pr create` in this repository, the default path is:

```bash
scripts/create-pr.sh --title "$title" --body-file "$body_file"
```

The wrapper handles push, redaction, existing-PR detection, diagnostics, and
repo argument threading.

Disposable-worktree scripts that push a custom branch and require their own
PR/merge/recovery semantics may invoke `gh pr create --head <branch>
--body-file <path>` directly. The documented current caller is
`scripts/design-log-publish.sh`; keep its sibling `scripts/design-log-publish.md`
in sync with that exception.

Issue-body marker writers use `scripts/named-block-write.sh`, which applies
redaction and `gh issue edit --body-file` for its callers.

## Fixed Literals

If a security-sensitive workflow needs a fixed literal body, commit the literal
as a file and pass that committed path with `--body-file`. `/design` Step 5d uses
`skills/design/references/l3-velocity-deferral-comment.txt` for this reason.
The fixed-literal invariant is preserved by git history and visible in diffs.

## Maintenance

When adding a new caller that invokes `gh ... --body`, `gh ... --body-file`,
`gh ... --notes`, or `gh ... --notes-file`, add that file and its sibling `.md`
contract file to this rule's `paths:` frontmatter so future edits see the
reminder.

## Dynamic Bodies and Redaction

When the body content derives from session data (implementation plans, token
reports, reviewer prose, or any execution-derived text), pipe the content
through `scripts/redact-secrets.sh` (and `scripts/redact-tmpdir-paths.sh` when
the content may contain local tmpdir paths) before writing it to the body file.
The shell-layer redaction inside larch scripts does not automatically protect
prompt-assembled bodies. See `SECURITY.md` for the outbound-redaction policy.

For PR creation specifically, use `scripts/create-pr.sh`; it applies both
redaction passes internally.

## Scope

This rule covers GitHub CLI body-like payloads only: `--body` and `--notes`.
It does not cover `--title`, `git commit -m`, or `gh` calls with no body/notes
payload.
