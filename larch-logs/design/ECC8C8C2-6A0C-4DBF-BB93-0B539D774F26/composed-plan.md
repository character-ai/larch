## Plan

### Approach

`approach-synthesis.txt` is not present in the checkout; the supplied synthesis says `NO_SKETCHES`, so draft from direct repo inspection and the approved outline. No `discussion-round1.md`, `brainstorm.md`, `design-outline.md`, or `.outline-approved` file is present in the checkout, so use the supplied approved outline as the binding scope.

Keep the fix small and local.

1. In `scripts/hook-anti-read-poll.sh`, add `[ -d "$state_dir" ] && [ ! -L "$state_dir" ] || exit 0` immediately after `mkdir -p "$state_dir"` and before `chmod 700 "$state_dir"`. Today the first post-`chmod` guard sits after `chmod` (line 43); the new line closes the mkdir→chmod race window.
2. Add the same guard immediately before `tmp_state=$(mktemp "$state_dir/.${key}.tmp.XXXXXX" ...)`. Today `mktemp` runs at line 70 with no preceding revalidation; the post-`mktemp` cleanup guard at line 71 only runs after temp creation.
3. Preserve the hook's fail-open contract: malformed input, rejected state dirs, and temp write failures still exit 0 and emit no reminder.
4. Do not add ancestor-symlink traversal or a directory-fd helper. The approved outline makes that a non-goal.
5. Keep the existing pre-`mkdir` guards, post-`chmod` guard, pre-read guard, and pre-write / pre-promotion checks. The two new guards narrow extra race windows; they do not replace current checks.

### Files to modify/create

### UPDATED: scripts/hook-anti-read-poll.sh

Insert this guard after `mkdir -p "$state_dir" 2>/dev/null || exit 0` and before `chmod 700 "$state_dir" 2>/dev/null || true`:

```bash
[ -d "$state_dir" ] && [ ! -L "$state_dir" ] || exit 0
```

Insert the same guard immediately before the `tmp_state=$(mktemp "$state_dir/.${key}.tmp.XXXXXX" 2>/dev/null) || exit 0` line.

Do not change reminder text, state-file format, key hashing, threshold logic, or hook registration.

### UPDATED: scripts/test-hook-anti-read-poll.sh

Extend the harness with four layers: a production source-shape check, a post-`mkdir` sibling regression, tightened variant construction for guardless controls, and a chmod side-effect assertion on the swap race variant.

Define shared Python needles for variant builders (inline heredocs, exact textual match, fail if needles missing):

- `PRE_MKDIR_SYMLINK_NEEDLE`: `[ -L "$state_dir" ] && exit 0`
- `PRE_MKDIR_NONDIR_NEEDLE`: `[ -e "$state_dir" ] && [ ! -d "$state_dir" ] && exit 0`
- `STANDALONE_STATE_DIR_GUARD`: `[ -d "$state_dir" ] && [ ! -L "$state_dir" ] || exit 0` (standalone line only; exclude cleanup variants `{ rm -f "$tmp_state" ...; exit 0; }`)

**1. Production hook ordering assertion (addresses FINDING_1, Cursor-Arch)**

Add a small inline Python heredoc that reads the production hook and fails if this ordering is missing:

- A line matching `mkdir -p "$state_dir"`.
- On the next non-empty, non-comment line: `[ -d "$state_dir" ] && [ ! -L "$state_dir" ] || exit 0`.
- Before the first `chmod 700 "$state_dir"` line: the same guard must appear between `mkdir` and `chmod`.

Also assert the pre-`mktemp` guard appears on the line immediately before the `mktemp "$state_dir/.${key}.tmp.XXXXXX"` assignment (only blank lines allowed between them). Fail the harness if either guard shape or ordering is absent so future edits cannot silently vacate coverage.

**2. `chmod_guardless` sibling control (addresses FINDING_1, Codex-dyn-Hook Toctou Security)**

Build a `chmod_guardless_hook` variant from the production hook that removes only the two pre-`mkdir` state-dir rejection lines (`PRE_MKDIR_SYMLINK_NEEDLE`, `PRE_MKDIR_NONDIR_NEEDLE`). Leave all post-`mkdir` guards intact, including the new pre-`chmod` guard and the pre-`mktemp` guard.

Test setup:

- Ensure `$TMPDIR/larch-read-poll` does not exist.
- Create a redirect directory under the harness temp root.
- Place a leaf symlink at `$TMPDIR/larch-read-poll` pointing at the redirect directory (no parent-dir symlink; sibling to the existing parent state-dir symlink test).
- Run `chmod_guardless_hook` once with a normal Read payload.

Assert:

- Exit code 0 and no reminder output.
- No `.tmp.*` files and no `.state` files appear under the redirect directory.
- The leaf symlink at `$TMPDIR/larch-read-poll` is not replaced with a regular state file.

This proves the new post-`mkdir` / pre-`chmod` guard is load-bearing when early symlink rejection is stripped.

**3. Swap-after-`mkdir` race regression (addresses FINDING_1, Codex-Arch / Codex-Innovation)**

Add a cooperative race harness using a `swap_after_mkdir_hook` variant:

- Copy the production hook.
- Replace the single `mkdir -p "$state_dir" 2>/dev/null || exit 0` line with a block that:
  1. Runs `mkdir -p "$state_dir"` as today.
  2. Atomically replaces `$TMPDIR/larch-read-poll` with a symlink to a fresh redirect directory (for example `rm -rf` the real dir, then `ln -s` the redirect at the leaf path). Use only POSIX constructs already used in the harness.
  3. Continues into the unchanged post-`mkdir` guard, `chmod`, and later logic.

Before running the hook, record the redirect directory mode (for example `stat -f '%OLp'` on macOS / `stat -c '%a'` on Linux via a small portable helper already consistent with harness style).

Run once and assert:

- Exit 0 and no reminder.
- No temp or state files under the redirect directory.
- Redirect directory mode is unchanged after the run (chmod-visible side effect absent). This directly proves `chmod 700` did not run against attacker-controlled storage when the new pre-`chmod` guard fires.

Keep the existing parent state-dir symlink test unchanged; it still covers the normal production path where the leaf path is a symlink before any `mkdir`.

**4. Tightened `fully_guardless` and `deep_guardless` variants (addresses FINDING_1 negative control and FINDING_2)**

Use inline Python heredocs with ordered, exact textual replacement.

`fully_guardless_hook` — construction order matters:

1. Remove `PRE_MKDIR_SYMLINK_NEEDLE` and `PRE_MKDIR_NONDIR_NEEDLE` (same needles as `chmod_guardless`).
2. Remove every standalone `STANDALONE_STATE_DIR_GUARD` line, including cleanup variants `{ rm -f "$tmp_state" 2>/dev/null || true; exit 0; }` that embed the same predicate.

After construction, assert programmatically in the same heredoc:

- Neither pre-`mkdir` needle remains.
- No standalone `STANDALONE_STATE_DIR_GUARD` line remains anywhere in the variant.

Point `$TMPDIR/larch-read-poll` at a symlink to a redirect directory. Run and assert a `.tmp` or final `.state` file lands in the redirect (negative control proving attacker-controlled storage can receive hook output when all guards are stripped).

`deep_guardless_hook` — start from `fully_guardless_hook`, then re-insert exactly one guard: `STANDALONE_STATE_DIR_GUARD` immediately before the `mktemp` assignment.


- Exactly one standalone `STANDALONE_STATE_DIR_GUARD` remains in the variant.
- That occurrence is on the line immediately before `tmp_state=$(mktemp "$state_dir/.${key}.tmp.XXXXXX"`.
- No other standalone `STANDALONE_STATE_DIR_GUARD` occurs above the `mktemp` line.

Fail variant construction if pre-`mkdir` needles survive, if guard count is not exactly one, or if an extra standalone guard above `mktemp` would let an unrelated check satisfy the positive test (FINDING_2).

Run `deep_guardless_hook` with the same symlinked `$TMPDIR/larch-read-poll` setup and assert exit 0, no reminder, and no temp or state files in the redirect directory.

Prefer exact needle matching for removals and insertions. Fail if expected needles are missing so hook edits cannot make regressions silently vacuous.

Keep the existing `guardless_hook` read-guard negative control and leaf `state_file` symlink test unchanged.

### MAY_UPDATE: SECURITY.md

Only update the Read-poll hook paragraph if the final code makes the current wording stale or materially incomplete.

Current wording already says the hook validates `$state_dir` before filesystem mutation and before temp creation or promotion. After adding explicit post-`mkdir` and pre-`mktemp` revalidation, that description remains accurate. Leave `SECURITY.md` unchanged to avoid scope creep.

### Edge cases

- `mkdir -p` succeeds but `state_dir` is swapped to a symlink before `chmod`: the new post-`mkdir` guard exits 0 before `chmod`; the swap-after-`mkdir` harness models this directly and asserts no chmod side effect on the redirect.
- `state_dir` passes the pre-read guard, then is swapped before `mktemp`: the new pre-`mktemp` guard exits 0 before temp creation; `deep_guardless` proves that guard alone blocks writes when all earlier guards (including both pre-`mkdir` needles) are removed and no other standalone guard survives above `mktemp`.
- A leaf symlink exists at `$TMPDIR/larch-read-poll` with pre-`mkdir` guards stripped: `chmod_guardless` proves the post-`mkdir` guard rejects before `chmod` and `mktemp`.
- A symlink swap happens after `mktemp`: existing pre-write and pre-promotion checks still remove `tmp_state` when possible and exit 0.
- A leaf `state_file` symlink exists: existing tests and guards keep replacing it with a regular state file without following it for reads or writes.
- `jq`, `cksum`, `date`, `mktemp`, or filesystem operations fail: preserve current exit-0 hook behavior.

### Failure modes when non-trivial

- Variant builders could remove the wrong guard occurrence. Mitigate with ordered needles, explicit pre-`mkdir` stripping in `fully_guardless`, and post-construction assertions on guard count, pre-`mkdir` absence, and adjacency to `mktemp` / `mkdir`→`chmod` ordering in the production hook.
- `deep_guardless` could retain a hidden earlier guard or leftover pre-`mkdir` line. Mitigate with assertions that fail if either pre-`mkdir` needle remains or any standalone guard exists above the reinserted pre-`mktemp` line.
- `fully_guardless` negative control could fail if later guards still block promotion. Its assertions should accept either a temp file or a state file in the redirect, but must prove attacker-controlled storage received hook output.
- `swap_after_mkdir` could pass without exercising the race if `chmod` still runs on the redirect. Mitigate with redirect mode before/after comparison.
- `chmod` on a symlinked directory may affect the redirect target in guardless variants. Keep redirects under the harness temp dir and clean with the existing trap.
- Bash 3.2 compatibility matters. Use POSIX-style shell constructs already present in the harness. Avoid arrays, `mapfile`, namerefs, and case-conversion expansions.

### Testing strategy

Run only changed-file relevant checks:

bash scripts/test-hook-anti-read-poll.sh
make test-hook-anti-read-poll
make shellcheck

If `SECURITY.md` changes, also run the relevant Markdown lint path for that file, or `make markdownlint` if no narrower project target is available.

Run `python3 python/cli.py checks run-relevant` before handoff if the implementation workflow expects the standard larch relevant-checks envelope.

### Difficulty

## Acceptance

Run only changed-file relevant checks:

bash scripts/test-hook-anti-read-poll.sh
make test-hook-anti-read-poll
make shellcheck

If `SECURITY.md` changes, also run the relevant Markdown lint path for that file, or `make markdownlint` if no narrower project target is available.

Run `python3 python/cli.py checks run-relevant` before handoff if the implementation workflow expects the standard larch relevant-checks envelope.

review_status: complete
rounds_completed: 2
difficulty: MODERATE
diff_added: 135
diff_deleted: 5
mechanical_churn: false
diff_lines: 140
