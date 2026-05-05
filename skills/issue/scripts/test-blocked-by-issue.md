# test-blocked-by-issue.sh — sibling contract

**Purpose**: structural regression harness pinning `/issue --blocked-by-issue N`, the caller-supplied policy blocker used by `/implement` Step 9a.1 when filing OOS issues. The harness verifies the public flag surface, Step 1 validation rules, Step 4 open-issue probe, Step 4 snapshot augmentation, Step 5 merge / no-external-refs carve-out, and Step 6 application details.

**Makefile wiring**: `make test-blocked-by-issue` (listed in `.PHONY` and in exactly one `test-harnesses-N:` shard prerequisite list — the umbrella `test-harnesses` aggregates all shards).

**Assertions**:
1. Frontmatter `argument-hint` includes `[--blocked-by-issue N]`.
2. Step 1 validations contain the `--no-dedup` mutual-exclusion error, the single-mode rejection error, and the positive-integer validation error.
3. Step 4 probe contains the `gh api "/repos/$REPO/issues/$BLOCKED_BY_ISSUE"` fetch, a `.pull_request != null` PR check, an open-state check, title sanitation with `tr -d '\t\n'`, and explicit `--dry-run` inclusion.
4. Step 4 snapshot augmentation mentions injecting a synthetic open-state row.
5. Step 5 contains the `Caller-supplied --blocked-by-issue merge` heading.
6. Step 5 contains the `Carve-out for --blocked-by-issue` no-external-refs carve-out.
7. Step 6 contains the `Step-5-skip-path policy-edge augmentation` paragraph.
8. Step 6 contains the cached `--blocker-id $BLOCKED_BY_ISSUE_ID` application path.

**Edit-in-sync rules**: if the asserted strings in `skills/issue/SKILL.md` change, update this harness's `assert_present` needles in the same PR. If the flag's semantics change beyond structural wording, update this contract and any `/implement` Step 9a.1 forwarding tests in the same PR.
