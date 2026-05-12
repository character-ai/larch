## Goal

Scaffold and ship the /block-issue plugin skill that wraps GitHub's native `addBlockedBy` GraphQL mutation, enabling skills to express native blocking relationships with a single two-argument invocation.

## Implementation Plan

New skill `skills/block-issue/` with a minimal SKILL.md and `scripts/add-blocked-by.sh`. The script accepts two issue numbers, resolves their GraphQL node IDs, calls the `addBlockedBy` mutation, verifies the dependency was recorded, and prints a one-line confirmation. Post-scaffold hints applied to README and doc files.

## Test plan

Run `/relevant-checks` (pre-commit + agent-lint) after implementation. Manual verification was already performed live against real issues (#1840–#1844) during this session.
