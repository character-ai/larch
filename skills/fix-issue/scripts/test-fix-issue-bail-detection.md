# skills/fix-issue/scripts/test-fix-issue-bail-detection.sh — contract

`skills/fix-issue/scripts/test-fix-issue-bail-detection.sh` is the regression harness for the Phase 4 bail-detection prose in `skills/fix-issue/SKILL.md` Step 5a (originally Phase 4 of umbrella #348; renumbered from Step 6a to Step 5a by the fold-find-and-lock refactor closes #496). It is offline, hermetic, and runs against the committed `SKILL.md` — no network, no git state change, no mocks. The harness guards against accidental removal of literal assertions inside the Step 5a block, covering twelve conceptual checks:

- `--issue $ISSUE_NUMBER` in the invocation (forwarded to `/implement` so it adopts the queue issue via Phase 3 Branch 2).
- `--no-admin-fallback` in the invocation (issue #559 — branch-protection bypass safety flag forwarded so `/fix-issue --no-admin-fallback` callers are not silently exposed to an `--admin` override).
- `--coder=$coder` in the invocation (pass-through implementer-selection flag forwarded so `/fix-issue --coder=<value>` callers reach `/implement` Step 2's coder selector).
- `[--auto if auto_mode]` in the invocation (pass-through autonomous-mode flag forwarded so `/fix-issue --auto` callers reach `/implement`'s autonomous-mode behavior).
- `[--hard if hard_mode]` in the invocation — encodes that `/fix-issue` delegates HARD/SIMPLE selection to `/implement` via this conditional forward. When `--hard` is not passed, no mode-selection flag is sent and `/implement` decides via its own simplicity classification.
- The invocation does NOT unconditionally contain `--quick` — the old SIMPLE path that always passed `--quick` to `/implement` is removed; `/implement` now decides SIMPLE vs HARD.
- `[--inline if inline_mode and hard_mode]` in the invocation — encodes that `--inline` is forwarded only when `--hard` is also set (because `--inline` only matters when `/design` runs, which requires HARD mode).
- `IMPLEMENT_BAIL_REASON=adopted-issue-closed` — the exact machine token `/implement` emits when the adopted issue is CLOSED; `/fix-issue` scans captured output for this literal.
- `/implement bailed: issue #` — the user-visible warning prefix printed on the bail branch.
- `` Do NOT call `issue-lifecycle.sh close` `` — specific directive fragment (not a bare `Do NOT call` substring) that prevents silent re-routing of the bail path back to Step 6's close call. The full phrase is required because the awk extraction window also includes section 5b, which contains an unrelated `Do NOT call \`/implement\`` sentence.
- `Skip to Step 8` — cleanup redirect on the bail branch.
- `Invoke` followed by `/implement` via the Skill tool — delegation mandate that anchors anti-pattern #5 (NEVER implement inline at Step 5a using Edit/Write/Bash file-modification tools instead of delegating to `/implement` via the Skill tool; closes #1988).

Extraction boundary: `^### 5a` (start, prefix match) through `^## Step 6` (end, prefix match; the real heading is `## Step 6 — Finalize`). This scopes the assertions to Step 5a so stray mentions of these literals elsewhere in `SKILL.md` cannot false-pass the harness.

The harness is wired into `make lint` via the `test-fix-issue-bail-detection` target in `Makefile`. It is added to `agent-lint.toml`'s `exclude` list alongside its sibling contract `.md` because agent-lint's dead-script and S030/orphaned-skill-files rules do not follow Makefile-only references. The paired token-literal assertion on the emitter side lives in `scripts/test-implement-structure.sh` (pins the same token in `skills/implement/SKILL.md`); a rename of the bail token is therefore a dual-repo change caught by CI.

Edit-in-sync: if the Step 5a narrative rewords any of the literal assertions or restructures the bail branch, update this harness and this contract in the same PR.
