# skills/fix-issue/scripts/test-fix-issue-step-order.sh — contract

`skills/fix-issue/scripts/test-fix-issue-step-order.sh` is the regression harness pinning the `/fix-issue` Step 0 = find & lock, Step 1 = setup structure established by the fold-find-and-lock refactor (closes #496). It is offline, hermetic, and runs against the on-disk `skills/fix-issue/SKILL.md` and `skills/fix-issue/scripts/step-name-registry.tsv` at harness invocation time — typically the commit checked out in CI, but local developer runs see the working tree. No network, no git state change, no mocks. The harness guards against accidental reversion of the fold or stale renumbering of the breadcrumbs. (Throughout this contract, "preamble" means the YAML front matter, the H1 title, and any body text that appears before the first flush-left line matching `^<!-- step:` — not just YAML.)

Twelve assertions — nine textual literal pins (1-8, 12) plus three operational ordering pins (9-11) via awk-scoped block extraction. Assertions (1), (2), (7), and (8) target `step-name-registry.tsv`; the remaining assertions target `SKILL.md`.

1. `step-name-registry.tsv` contains row with `step=0, name=find & lock` (checked via `awk -F'\t'` exact column match).
2. `step-name-registry.tsv` contains row with `step=1, name=setup` (same).
3. Section anchor `<!-- step:0 — Find and Lock -->` present.
4. Section anchor `<!-- step:1 — Setup -->` present.
5. Anti-pattern #1 contains `treat Step 0 as structural`.
6. Find & lock warning breadcrumb literal `⚠ 0: find & lock` present.
7. No stale `step=1, name=lock` row in `step-name-registry.tsv` (checked via `awk -F'\t'` exact column match to avoid false positives — see #889).
8. No stale `step=2, name=lock` row in `step-name-registry.tsv` (same narrowing).
9. The Step 0 block contains the `find-lock-issue.sh` invocation.
10. The Step 0 block does NOT contain `session-setup.sh` (operational ordering).
11. The Step 1 block contains `session-setup.sh --prefix claude-fix-issue --skip-branch-check`.
12. File-preamble Anti-halt rule contains `child Bash tool calls into the canonical` — proves the rule is broadened beyond the original Skill-only scope (closes #530). The check is scoped to the file preamble (start of file through the first step anchor) so the assertion enforces the locational claim, not just substring presence anywhere in the file. The Bash-call coverage is load-bearing for the Step 6 → Step 7 → Step 8 terminal chain and for the parallel close/announce/cleanup tails in Step 3's not-material closure flow and the Step 6b → Step 7b → Step 8 NON_PR close path; each of those tails has no intervening Skill tool call. The harness diagnoses three distinct preamble-extraction failure modes separately: (a) no flush-left line matching `^<!-- step:` anywhere in the file (preamble end boundary missing), (b) first matching anchor on line 1 (preamble is empty), (c) anchor exists past line 1 but preamble does not contain the broadening literal.

Block extraction boundaries for assertions 9-11: `<!-- step:0 — Find and Lock -->` (start, exact line match) through `<!-- step:1 — Setup -->` (end, exact line match) for Step 0; `<!-- step:1 — Setup -->` (start) through `<!-- step:2` (end, prefix match — anchor is `<!-- step:2 — Read Issue Details -->`) for Step 1. Assertion 12 uses a separate preamble extraction: line 1 through (but not including) the first line matching `^<!-- step:`. The block-scoped assertions are the load-bearing guard against a regression where a future edit keeps the registry rows, anchors, and breadcrumbs intact while moving the matched literal out of its expected location.

The harness uses an accumulator pattern (`fail=1` set on each failure, exit at end) so all failures are reported in a single run. Exits 0 when all 15 assertions pass; exits 1 after running every assertion if any failed.

The harness is wired into `make lint` via the `test-fix-issue-step-order` target in `Makefile`. It is added to `agent-lint.toml`'s `exclude` list alongside this sibling contract because agent-lint's dead-script and S030/orphaned-skill-files rules do not follow Makefile-only references.

TSV encoding: the file must be UTF-8 with LF line endings and no BOM. The awk `$2` comparison will include `\r` if CRLF endings slip in, causing false CI failures.

Edit-in-sync: if the Step Name Registry rows in `step-name-registry.tsv` change (assertions 1, 2, 7, 8), the section anchors rename, anti-pattern #1 reverts, any find & lock warning breadcrumb literal moves, the find-lock-issue.sh invocation form changes, the setup-script invocation form changes, or the file-preamble anti-halt phrase `child Bash tool calls into the canonical` is reworded, update both this harness and this contract in the same PR. The block-extraction boundaries are pinned to the exact anchor literals `<!-- step:0 — Find and Lock -->`, `<!-- step:1 — Setup -->`, and `<!-- step:2` (prefix); a Step 2 anchor rename is the most likely silent breakage and is itself caught by assertion (3) / (4) on the start side, but the Step 2 prefix boundary should be re-pinned in the same PR if Step 2's anchor changes.
