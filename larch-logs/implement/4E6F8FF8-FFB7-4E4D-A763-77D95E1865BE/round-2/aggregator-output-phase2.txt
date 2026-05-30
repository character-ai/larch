### FINDING_1: Blank-line block-boundary fixture missing
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: No harness fixture covers a blank line between optional trailers and `diff_lines:`. An Awk change that treats blank lines as continuations instead of scan terminators could pass current text-boundary fixtures but break real plans that use empty lines before `diff_lines:`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add a fixture with a blank line between optional trailers and diff_lines:; assert parse/keys/values/has_key match text-boundary expectations

### FINDING_2: Octal-rejected fixtures lack keys/values assertions
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The committed harness does not assert empty `keys`/`values` on octal-rejected fixtures (`08`/`09`). An Awk regression could still exit `has_key` with failure while printing `diff_added`/`diff_deleted` in keys/values, and `make test-trailer-helpers` could still pass parse/has_key-only coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add assert_keys/assert_values on octal-rejected (empty) and optionally octal-then-valid for block_len plus last-match-wins
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Add assert_keys and assert_values with empty expected output on TMPROOT/octal-rejected (and document in test-trailer-awk.md).
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_3: `write_fixture` unused `shift`
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `write_fixture` performs `shift` but never uses remaining parameters, adding noise when reading the fixture API.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Remove the unused shift or document the intended multi-arg contract

### FINDING_4: `assert_eq_lines` bypasses `fail()` helper
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `assert_eq_lines` exits directly instead of routing through `fail()`, unlike `assert_has_key` and sibling harnesses.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Route assert_eq_lines failures through fail() after printing got/want diff

### FINDING_5: [OUT_OF_SCOPE] Duplicated hook-residue commit logic in review-and-fix vs ship-pr
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Hook-residue commit logic is duplicated between `review-and-fix.sh` and ship-pr pre-rebase fixup (#3209); the two sites can diverge on staging scope or failure handling over future edits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extract a small shared helper when next touching residue fixup (optional refactor)

### FINDING_6: [OUT_OF_SCOPE] Cleanup #3212 top-level `find -mtime` tradeoff (documented)
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: #3212 trades nested activity scan for top-level `find -mtime`; age semantics differ from the prior depth-5 activity model. Already documented in cleanup SKILL; no action needed for #3204.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_7: Missing octal-then-valid fixture and related assertions
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: HEAD lacks an invalid-octal-then-valid-strict-trailer fixture. An Awk change that counts `08`/`09` toward `block_len` but excludes them from `has_added` could yield `parse` `block_len=2` (or similar) while `values`/`has_key` still pass, breaking plan-size gating; pure octal-rejected tests would not catch it. Working-tree additions may exist but are not committed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add octal-then-valid fixture and keys/has_key assertions; commit unstaged working-tree additions.
  - From cursor-specialist-testing-output.txt: Add octal-then-valid fixture with parse block_len=1 and value 5 plus keys/values/has_key assertions; commit the existing working-tree hunk.
  - From cursor-specialist-edge-cases-output.txt: Add octal-then-valid fixture; assert parse 1/5/-/-, keys, values diff_added=5, has_key rc=0; commit working-tree additions.

### FINDING_8: [OUT_OF_SCOPE] Cleanup drops nested-activity retention model
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Cleanup uses directory mtime only, not nested activity. An active session directory with an old root mtime but fresh nested files may be deleted after retention.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Document tradeoff or bounded nested mtime without unbounded find.

### FINDING_9: [OUT_OF_SCOPE] Round follow-up residue check ignores untracked files
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: The follow-up residue check ignores untracked files; untracked-only hook residue after the round commit may still report `CODER_STATUS=applied`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Extend check or document reliance on ship-pr backstop explicitly.

### FINDING_10: Block-boundary fixture documentation clarity
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: The `block-boundary` `has_key` test expects `rc=0` for in-block `diff_added` while orphan-above-boundary behavior is only tested in `boundary-orphan-only`; docs overgeneralize that `block-boundary` should assert `has_key` exit 1 for `diff_added`, which can mislead maintainers and weaken coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add a one-line comment in harness or test-trailer-awk.md clarifying two-fixture split.
  - From cursor-specialist-edge-cases-output.txt: Clarify orphan vs in-block fixtures; rename block-boundary fixture for clarity.

### FINDING_11: [OUT_OF_SCOPE] Uncommitted trailer-harness improvements not on HEAD
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Local working-tree edits add octal-then-valid and keys assertions for octal-rejected but are not on HEAD or the review diff snapshot; merge without commit understates coverage on the remote branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Commit or drop the unstaged harness hunk before merge.
  - From cursor-specialist-plan-fidelity-output.txt: Commit or drop local harness deltas before merge

### FINDING_12: `ship-pr.sh` pre-rebase fixup stages all tracked dirty paths
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Pre-rebase fixup auto-commits all tracked dirty paths via `git add -u` and `git-commit.sh` with a fixed chore message. An `/implement` run with tracked secrets or local credentials in the working tree can embed them in branch history before rebase/push without human review.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Restrict staging to an allowlisted path set (e.g. larch-logs/) or run a secret/path policy check before committing; avoid blanket git add -u for automation.

### FINDING_13: `review-and-fix.sh` round follow-up uses `git add -A`
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Round follow-up runs `git add -A` and a second commit when tracked porcelain remains after the round commit. A pre-commit hook or unexpected tracked file can be included in the follow-up commit alongside review fixes, widening blast radius for sensitive or unintended content.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Stage only paths from the round fix delta or an explicit manifest; fail closed when dirty paths fall outside that set.

### FINDING_14: Cleanup top-level mtime can prune actively used session dirs
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-cleanup-semantics-output.txt
- **Severity**: latent
- **Concern**: Cleanup uses top-level `find -mtime` only (not nested activity). A session directory whose root mtime is older than the retention window can be removed even when descendants were written recently (harness now expects this in `stale-toplevel-with-fresh-deep-child-removed`). On typical Unix filesystems, activity deep under `larch-logs/implement/…` does not always bump the session root mtime, so a long-running `/implement` can be pruned while still writing nested artifacts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: consider bounded descendant activity for cache session entries only.
  - From dyn-cleanup-semantics-output.txt: If the hang fix must avoid deep `find`, consider a cheaper freshness signal at the session root (e.g., touch the session dir on implement/design writes, honor `.larch-keepalive`, or a single shallow sentinel) before relying solely on top-level `-mtime`, or document an explicit operator invariant that nested writes must refresh the session root.

### FINDING_15: Cleanup retention uses whole-day `find -mtime` semantics
- **Reviewer(s)**: dyn-cleanup-semantics-output.txt
- **Severity**: latent
- **Concern**: Retention now follows `find -mtime +N` (integral 24-hour day rounding at `find` start) instead of the prior strict `(now - mtime) > RETENTION_DAYS * 86400` second boundary. Entries near the end of the retention window can be classified differently (off by up to roughly one day depending on platform `find` behavior).
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-cleanup-semantics-output.txt: If second-precision parity matters, keep top-level `find` for performance but filter candidates with an explicit `stat`/`test` against `RETENTION_DAYS * 86400`, or document that cleanup uses whole-day `find` semantics and align `LARCH_CLEANUP_RETENTION_DAYS` wording in `SECURITY.md` / `cleanup.md`.

### FINDING_16: Cleanup swallows `find` errors and always exits 0
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-cleanup-semantics-output.txt
- **Severity**: latent
- **Concern**: Age-pass `find` errors are swallowed (`2>/dev/null`, `|| true` on the read loop) and the script always exits 0 with zero removal counts when enumeration fails. Session dirs may retain sensitive `.meta` files when `find` fails silently, or failures become indistinguishable from “nothing stale,” removing the old per-entry warning path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Surface find failures (non-zero exit or explicit partial status); consider bounded descendant activity for cache session entries only.
  - From dyn-cleanup-semantics-output.txt: Emit at least one `larch_err` warning when `find` returns non-zero or produces no readable listing while the parent directory is non-empty and unreadable entries are suspected; keep exit 0 if aborting mid-cleanup is undesirable.

### FINDING_17: [OUT_OF_SCOPE] `write_fixture` does not validate fixture names
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: `write_fixture` does not validate fixture names for path traversal. Only hardcoded names are used today; no current exploit path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Reject names containing / or .. if dynamic names are added later.

### FINDING_18: Octal paths lack `values`-mode assertions
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: No `values`-mode assertions on octal paths; `values` mode could regress while `parse`/`has_key` still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Add assert_values for octal-then-valid and optionally empty octal-rejected.

### FINDING_19: Missing `assert_values` on `none-present` fixture
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Plan edge cases require both `keys` and `values` to print nothing for no-trailer plans; only `keys` is asserted, so `values`-mode regressions can slip through.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Add assert_values "$TMPROOT/none-present" ''

### FINDING_20: Doc vs Awk mismatch on `08`/`09` and `block_len`
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `lib-plan-optional-trailers.md` says regex-matching lines join the block, but Awk excludes `08`/`09` before `block_len`. Aligning Awk with the prose would break `check-plan-size` and octal-rejected parse expectations unless behavior is documented explicitly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Engineer aligns awk with prose and counts octal lines in block_len breaking check-plan-size and octal-rejected parse expectations Document that 08/09 match regex but are not added to block/block_len

### FINDING_21: Harness omits explicit `exit 0`
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Harness omits explicit `exit 0` required by the plan file spec; minor divergence from stated harness contract only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Append exit 0 after PASS echo

### FINDING_22: [OUT_OF_SCOPE] `--dedup` grep in `test-design-structure.sh` not pipeline-anchored
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `--dedup` grep is anywhere-in-file, not pipeline-anchored; a doc-only `--dedup` mention could satisfy the pin without a runnable hook.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Optional follow-up: anchor greps to gate-b-dedup-plan.sh invocations (pre-existing pattern).

### FINDING_23: [OUT_OF_SCOPE] Branch bundles unrelated commits beyond #3204
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Branch bundles unrelated commits beyond the #3204 plan; PR reviewers may treat version/cleanup/ship-pr changes as part of trailer work.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Keep #3204 commit isolated or split PRs

### FINDING_24: Round follow-up can report `applied` when follow-up commit fails with clean tree
- **Reviewer(s)**: dyn-git-commit-ordering-output.txt
- **Severity**: latent
- **Concern**: Round-mode follow-up documents fail-closed behavior when the follow-up commit fails or tracked porcelain remains, but implementation only returns `2` with `CODER_STATUS=failed` when porcelain remains after the attempt. If `git add -A` and `git-commit.sh` fail yet the tracked tree is clean, execution can fall through to the success epilogue and emit `CODER_STATUS=applied` with `CODER_COMMIT_SHA` still pointing at the primary round commit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-git-commit-ordering-output.txt: In the follow-up `else` branch, write the same `result_file` (`CODER_STATUS=failed`, `CODER_TOOL`, etc.) and `return 2` immediately; keep the existing porcelain re-check as a second guard for the success path.

### FINDING_25: `ship-pr.sh` fixup does not re-check tracked porcelain after commit
- **Reviewer(s)**: dyn-git-commit-ordering-output.txt
- **Severity**: latent
- **Concern**: Block 0b performs a single `git add -u -- larch-logs/` fixup commit and does not re-check tracked porcelain afterward. A pre-commit hook that mutates an already-staged `larch-logs/` file during `git-commit.sh` can leave hook-only changes on disk but out of the fixup commit; `drop-bump-commit.sh` Guard 1 may then see dirty tracked porcelain and stall rebump even though Step 5 may have cleaned residue via a follow-up commit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-git-commit-ordering-output.txt: After a successful fixup commit, mirror review-and-fix: if `git status --porcelain --untracked-files=no` is still non-empty within `larch-logs/`, run one more `git add -u -- larch-logs/` + fixup (or `git add -A` scoped to allowlisted paths) before calling `drop-bump-commit.sh`; alternatively document that Step 5 follow-up must always leave the tree clean and add a harness case where hook residue remains only in the working tree after fixup to pin stall vs. second commit behavior.
