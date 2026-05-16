## Goal
Fix 8 architectural defects in coder-dispatch: remove Claude fallback, fix cursor invocation, fix submodule-revert untracked files, check SCRUB_OK, fix in-scope-filtered-out status, add .rs/.toml extensions, align test-review-structure.md contract

## Implementation Plan

Fix 8 architectural defects in `skills/review-and-fix/scripts/review-and-fix.sh`, `scripts/scrub-submodule-paths.sh`, `scripts/test-review-structure.md`, and related test/doc surfaces introduced by #2210.

### Files to modify

1. `skills/review-and-fix/scripts/review-and-fix.sh` — Defects 1, 2, 3, 4, 5
2. `scripts/scrub-submodule-paths.sh` — Defect 7 (add `.rs`, `.toml` to extension list)
3. `scripts/test-review-structure.md` — Defect 8 (align contract markdown with harness assertions)
4. `skills/review-and-fix/scripts/test-review-and-fix.sh` — Update harness assertions for removed Claude path and new SCRUB_OK / status checks
5. `SECURITY.md` — Update triple-layer guarantee for Defect 3 (untracked files)
6. `skills/review-and-fix/scripts/review-and-fix.md` — Update sibling contract doc (script-md-siblings rule)

---

### Defect 1 — Remove Claude fallback from `run_coder_dispatch()`

The `LAUNCH_CLAUDE_SUBPROCESS_SH` variable, the `launch-claude-subprocess.sh` existence check in `run_implement_round`, and the entire Claude fallback block inside `run_coder_dispatch()` (the `if "$LAUNCH_CLAUDE_SUBPROCESS_SH" ...` block) must be deleted. The coder dispatch chain is Codex → Cursor only; Claude has no role as a post-dispatch fallback reviewer.

Specific changes:
- Remove the `LAUNCH_CLAUDE_SUBPROCESS_SH` variable assignment near the top of the script.
- Remove the `[ -x "$LAUNCH_CLAUDE_SUBPROCESS_SH" ] || ...` guard from `run_implement_round`.
- Remove the full Claude fallback block from `run_coder_dispatch()` (lines ~129–136).
- Defect 6 (fail-open STATUS check) becomes moot after this removal.

---

### Defect 2 — Fix cursor invocation in `run_coder_dispatch()`

The current invocation `cursor-agent --print --prompt "$prompt_body"` is wrong: wrong binary name, wrong flags, missing model/auth args, missing workspace.

Changes:
- Source `lib-cursor-launcher-common.sh` near the top of `review-and-fix.sh` (after the existing library sources).
- In `run_coder_dispatch()`, before the cursor invocation, call:
  ```bash
  cursor_launcher_load_model_args
  cursor_launcher_setup_auth_argv
  ```
- Replace the broken cursor invocation with:
  ```bash
  cursor agent -p --trust \
    ${MODEL_ARGS[@]+"${MODEL_ARGS[@]}"} \
    ${CURSOR_AUTH_ARGS[@]+"${CURSOR_AUTH_ARGS[@]}"} \
    --workspace "$PWD" \
    "$prompt_body"
  ```

---

### Defect 3 — `post_dispatch_submodule_revert` misses untracked submodule files

The function only collects tracked-file diffs (`git diff --name-only` and `git diff --name-only --cached`) and reverts them with `git checkout --`. Untracked files created inside a submodule path are not reverted.

Changes in `post_dispatch_submodule_revert`:
- Collect untracked paths via:
  ```bash
  git status --porcelain 2>/dev/null \
    | awk '$1 == "??" { sub(/^../, ""); print }' > "$untracked_set_file"
  ```
- Append untracked paths to `$diff_file`.
- In the revert loop, distinguish tracked vs. untracked: if the path appears in `$untracked_set_file`, use `rm -f` (delete it); otherwise use `git checkout -- "$path"`.

---

### Defect 4 — `SCRUB_OK` not checked after `scrub-submodule-paths.sh`

The scrubber can fail (bad input) and emit `SCRUB_OK false`, but the current code ignores the result and proceeds with whatever output the scrubber wrote. This can pass a corrupt/empty accepted-findings file to the coder.

Changes in `apply_findings_with_coder()`:
- Capture the scrubber exit code safely:
  ```bash
  scrub_out=$("$SCRUB_SUBMODULE_PATHS_SH" --input "$input_file" --output "$scrubbed_file" --log "$round_dir/submodule-scrub.log" 2>/dev/null) || true
  ```
- Parse `SCRUB_OK` from `scrub_out`.
- If `SCRUB_OK` is `false` (or absent when exit was non-zero), write `CODER_STATUS=failed` to the coder result file, emit a warning breadcrumb, and `return 2` so `run_implement_round` routes to `coder-failed`.

---

### Defect 5 — Wrong `else` branch status in `run_implement_round`

In the `fix-required|cap-reached` branch, when `in_scope_count == 0` (all findings were scrubbed out), the else branch sets `status="complete"` which is wrong — the round did not complete successfully; it simply had nothing in scope to apply.

Change: set `status="in-scope-filtered-out"` (and emit a Warning breadcrumb `⚠ review-and-fix: round $round — all accepted findings scrubbed; nothing to apply`).

---

### Defect 6 (moot)

Covered by Defect 1 (Claude fallback removal). No separate fix needed.

---

### Defect 7 — Missing `.rs` and `.toml` in `scrub-submodule-paths.sh` extension list

In `extract_paths()`, the `grep -Eo` extension alternation is missing `.rs` and `.toml`. Add them to the alternation.

Change the regex from:
```
([A-Za-z0-9._/-]+\.(sh|py|md|json|ts|tsx|js|jsx|yml|yaml|txt))(:[0-9]+)?
```
to:
```
([A-Za-z0-9._/-]+\.(sh|py|md|json|ts|tsx|js|jsx|yml|yaml|txt|rs|toml))(:[0-9]+)?
```

---

### Defect 8 — `test-review-structure.md` contract misdocuments harness assertions

The contract claims:
- Assertions 1c/1d verify `agents/orchestrator-judge.md` and `agents/orchestrator-aggregator.md` exist with `HAND-MAINTAINED` comment — but the harness asserts these must NOT exist.
- Assertion 20 checks `references/voting.md` — but the harness actually checks `skills/shared/voting-protocol.md`.

Fix: rewrite `scripts/test-review-structure.md` to accurately describe what the harness actually asserts.

---

### Testing strategy

- Run `scripts/test-review-structure.sh` — validates harness contract alignment (Defect 8).
- Run `skills/review-and-fix/scripts/test-review-and-fix.sh` — validates coder dispatch harness; update stubs and assertions for: (a) Claude removal from chain, (b) SCRUB_OK check path, (c) `in-scope-filtered-out` status.
- Run `scripts/test-scrub-submodule-paths.sh` — add assertions for `.rs`/`.toml` paths being correctly extracted/scrubbed.
- Run `/relevant-checks` after implementation.

### Failure modes

- If `cursor_launcher_load_model_args` is not available (lib not sourced), cursor invocation will fail with an unbound-variable error — caught by the test harness.
- If `SCRUB_OK` parsing is wrong (e.g., reads from wrong FD), the fail-open bug remains — verified by test-review-and-fix.sh's `submodule-violation` case.
- The `post_dispatch_submodule_revert` untracked-file fix assumes `git status --porcelain` format; verified by manual submodule-untracked probe in the test harness.

## Test plan
(no test plan section in plan-file)
