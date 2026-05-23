## Goal
Add feature-branch creation sub-step to /implement Step 0 to fix main-branch-prohibited regression from #2598

## Implementation Plan
## Plan

### Approach

Add a single new sub-section to `skills/implement/SKILL.md` between the existing "Copy plan + feature description + persist implement run flags" section (line 811) and "Capture branch name (`BRANCH_NAME`)" section (line 859). The new sub-section invokes `${CLAUDE_PLUGIN_ROOT}/scripts/create-branch.sh --branch <derived-name>` with three guard conditions matching the historical /design behavior plus the documented fork-mode carve-out.

Branch creation is gated by re-reading values parsed from the `create-branch.sh --check` call already present at line 799-805 (the "Branch prefix" sub-section) and `forked_target` from prompt state (already established in Step 0). Branch name derivation uses the issue title from `$IMPLEMENT_TMPDIR/feature-description.txt` (composed at line 819, first line is the title) plus `$ISSUE_NUMBER` (resolved at Step 0 tracking adoption, line 624-680).

No new script is introduced. `scripts/create-branch.sh` already supports `--branch <name>` (created in commit `054ba7de` per `git log scripts/create-branch.sh`); its `--branch` mode creates from `origin/main`, validates the `<USER_PREFIX>/` prefix, refuses to overwrite existing branches, and exits 1 on collision. /design used the same script prior to #2598 — the call site moves from /design to /implement; the script is reused unchanged.

Test coverage extends `skills/implement/scripts/test-step2-dispatch.sh` with two new tests covering: (a) /implement on `main` with a fresh issue-anchored tmpdir + a SKILL.md prompt simulation (no actual prompt-side execution; the test exercises the dispatcher contract by writing the spawn-branch file post-creation), and (b) /implement on an existing `<USER_PREFIX>/*` branch (no duplicate creation, dispatcher proceeds). The existing test 19 family stays in place as a defense-in-depth backstop.

### Files to modify

#### 1. `skills/implement/SKILL.md` — add "Create feature branch" sub-section

**Location**: insert a new `### Create feature branch` sub-section heading and body between line 855 (end of "Dirty-tree checkpoint (post-persist)") and line 859 (start of "Capture branch name (`BRANCH_NAME`)").

**Why this position**:
- `ISSUE_TITLE` is available from `$IMPLEMENT_TMPDIR/feature-description.txt` first line (composed at line 819).
- `USER_PREFIX` / `IS_MAIN` / `IS_USER_BRANCH` are available from the "Branch prefix" `--check` call at line 805.
- `ISSUE_NUMBER` is bound at Step 0 tracking adoption (line 624-680, non-fork runs require it set per line 813).
- `BRANCH_NAME` capture at line 859 then captures the just-created branch.
- The rebase macro at line 915 ("Rebase onto latest main") then operates on the feature branch as intended.

**Content** to insert (the outer four-backtick fence is presentational only — the actual SKILL.md insertion uses standard three-backtick code fences):

````markdown
### Create feature branch

After `feature-description.txt` is composed and the dirty-tree checkpoint passes, create the feature branch unless one of the skip conditions below applies. This is the canonical creation site for the issue-anchored, non-fork path; the dispatcher in `scripts/step2-implement.sh` refuses to launch Cursor / Codex on `main` / `master` for non-fork issue-anchored runs (`step2-implement.sh:331-335`, `main-branch-prohibited`).

**Skip creation when any of these is true**:
- `forked_target=true` — fork mode targets the upstream default branch; the dispatcher carves out this case explicitly (`step2-implement.sh:331` checks `_forked_target != "true"`).
- `IS_USER_BRANCH=true` — operator is resuming on an existing `<USER_PREFIX>/*` branch; do not clobber.

**Otherwise** (`IS_MAIN=true`, or `IS_USER_BRANCH=false` and not on a user-prefix branch), derive a kebab-case slug from the issue title (≤40 chars), assemble `BRANCH_NAME_DERIVED=<USER_PREFIX>/<slug>-<ISSUE_NUMBER>`, and call `create-branch.sh --branch`:

```bash
IMPLEMENT_TMPDIR="$IMPLEMENT_TMPDIR"
export IMPLEMENT_TMPDIR
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/session-env.sh" ]; then
  CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$IMPLEMENT_TMPDIR/session-env.sh" 2>/dev/null || true)
fi
export CLAUDE_PLUGIN_ROOT

if [ "${forked_target:-false}" != "true" ] && [ "${IS_USER_BRANCH:-false}" != "true" ]; then
  ISSUE_TITLE=$(head -1 "$IMPLEMENT_TMPDIR/feature-description.txt")
  SLUG=$(printf '%s' "$ISSUE_TITLE" \
    | tr '[:upper:]' '[:lower:]' \
    | tr -c 'a-z0-9' '-' \
    | sed 's/--*/-/g; s/^-//; s/-$//' \
    | cut -c1-40 \
    | sed 's/-*$//')
  BRANCH_NAME_DERIVED="${USER_PREFIX}/${SLUG}-${ISSUE_NUMBER}"
  ${CLAUDE_PLUGIN_ROOT}/scripts/create-branch.sh --branch "$BRANCH_NAME_DERIVED"
fi
```

Parse `BRANCH_NAME=<name>` and `ACTION=created` from `create-branch.sh` stdout on success. On exit 1 (branch already exists — should not happen given the `IS_USER_BRANCH` guard, but defense-in-depth covers a stale-tmpdir resume from a different operator), print an operator-visible warning naming the existing branch, set `STALL_TRACKING=true`, skip to Step 18. On exit 2 (git failure), surface the underlying stderr from the captured output and abort.

The downstream "Capture branch name (`BRANCH_NAME`)" section (next sub-section) then captures the canonical `BRANCH_NAME` via `git-current-branch.sh` regardless of which path above ran — the orchestrator does not need to track whether creation just happened; the capture is uniform.
````

#### 2. `skills/implement/SKILL.md` — Step 0 narrative note

**Location**: line 313 (immediately after "Parse `CURRENT_BRANCH`, `IS_MAIN`, `IS_USER_BRANCH`, and `USER_PREFIX` from stdout.").

Append the sentence: "On the clean-main entry path, `/implement` creates the feature branch later in Step 0 (after `feature-description.txt` is composed); see § Create feature branch."

Do **not** edit the `**⚠ /implement requires clean main to start...**` error block at line 363 — that block only fires on `PREFLIGHT_ERROR` (dirty tree or other Step 0 failure), where the (b) "check out or create a `<USER_PREFIX>/*` feature branch" remediation advice still applies.

#### 3. `skills/implement/scripts/test-step2-dispatch.sh` — extend test coverage

**Location**: append two new tests at the end of the file, before the final `summary` print.

**Test 20 (new)**: simulate the new flow's success path. In a scratch git repo on `main` with a `parent-issue.md` carrying `ISSUE_NUMBER=42`:

1. Run `scripts/create-branch.sh --branch "$USER_PREFIX/test-feature-42"` directly (simulates the new SKILL.md block).
2. Confirm `git symbolic-ref --short HEAD` reports the new branch name.
3. Write `step2-spawn-branch.txt` with the new branch name.
4. Invoke the dispatcher with `--coder cursor --cursor-present true`; assert `STATUS=` is **not** `bailed REASON=main-branch-prohibited` (it may be `bailed REASON=cursor-runtime-failure` from the PATH-stubbed cursor, but that is a different bail path).

**Test 21 (new)**: simulate the IS_USER_BRANCH skip path. In a scratch git repo on `$USER_PREFIX/existing-feature-42` with a `parent-issue.md` carrying `ISSUE_NUMBER=42`:

1. Do **not** call `create-branch.sh --branch` (simulates the SKILL.md skip path when `IS_USER_BRANCH=true`).
2. Confirm `git symbolic-ref --short HEAD` reports `$USER_PREFIX/existing-feature-42`.
3. Write `step2-spawn-branch.txt` with that branch name.
4. Invoke the dispatcher with `--coder cursor --cursor-present true`; assert `STATUS=` is **not** `bailed REASON=main-branch-prohibited`.

The existing test-19 family (19, 19a, 19b, 19c, 19d, 19e) stays unchanged — those guard the dispatcher's defense-in-depth gate, which we *want* to remain firm so a future regression cannot silently re-introduce this bug.

#### 4. `skills/implement/scripts/test-step2-dispatch.md` — extend test inventory

Append entries 20 and 21 to the bulleted inventory at the top of the file, matching the style of existing entries (e.g., "20. Scratch git repo on `$USER_PREFIX/test-feature-42` with `--coder cursor --cursor-present true` ... must NOT emit `STATUS=bailed REASON=main-branch-prohibited`.").

#### 5. `CHANGELOG.md` — add Fixed entry under "Unreleased"

Single line under the next version's "Fixed" section:

```
- /implement — Create the feature branch at the start of Step 0 plan materialization (regression from #2588 / #2598; pre-existing dispatcher main-branch-prohibited guard exposed the gap).
```

### Edge cases

1. **Detached HEAD at Step 0 entry**: handled by existing Preflight (`session-entry-gate.sh` refuses with `PREFLIGHT_ERROR`). Not reached by the new block.
2. **Existing `<USER_PREFIX>/<slug>-<N>` branch with stale work**: `create-branch.sh --branch` returns exit 1 (refuses to overwrite). The new block's exit-1 handler prints the operator-visible message, sets `STALL_TRACKING=true`, and skips to Step 18. This is the safe failure mode — the operator's prior work is preserved.
3. **Issue title with no alphanumeric characters** (degenerate slug): `SLUG` becomes empty; `BRANCH_NAME_DERIVED` becomes `${USER_PREFIX}/-${ISSUE_NUMBER}`. `create-branch.sh` accepts this (the validation at line 96 only requires the prefix); the resulting branch is ugly but functional. Acceptable — a follow-up issue can add a minimum-slug-length fallback, out of scope here.
4. **Forked runs (`forked_target=true`)**: skip creation entirely; the dispatcher's fork carve-out at `step2-implement.sh:331` allows main branch operation for fork mode (the upstream's default branch is the legitimate target).
5. **Re-run after partial failure**: if a prior /implement run created the branch but failed before completion, the operator re-runs from that branch (`IS_USER_BRANCH=true`); the new block skips creation, and execution resumes on the existing branch. This matches the historical /design idempotency contract.

### Breaking changes

None for users. The change is purely additive — /implement starts behaving the way it claimed to (per PR #2598's plan validation) but never actually did. Operators who currently bake "create branch first" into wrapper scripts will see one extra `create-branch.sh --branch` call from /implement that immediately fails with exit 1 (branch exists); the new block handles that exit-1 path with a clear operator message. They can drop the wrapper-side creation.

## Acceptance

1. `/implement <N>` from clean `main` creates `<USER_PREFIX>/<slug>-<N>` and proceeds to Step 2 dispatch without `STATUS=bailed REASON=main-branch-prohibited`.
2. `/implement <N>` from `<USER_PREFIX>/<slug>-<N>` (matching the issue) does **not** re-create the branch; orchestrator proceeds on the existing branch.
3. `/implement <N> --forked` does not create a branch; dispatcher proceeds on the operator-supplied branch (typically `main` on the fork side).
4. `scripts/test-step2-dispatch.sh` tests 20 and 21 pass; existing tests 19 / 19a–e continue to pass.
5. `make lint` passes (markdownlint clean on the new SKILL.md sub-section; bash 3.2 portability OK).
6. `make test-harnesses` passes (the test-step2-dispatch.sh shard membership picks up the new tests).

## Test plan
(no test plan section in plan-file)
