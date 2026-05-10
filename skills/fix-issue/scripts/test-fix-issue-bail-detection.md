# skills/fix-issue/scripts/test-fix-issue-bail-detection.sh — contract

`skills/fix-issue/scripts/test-fix-issue-bail-detection.sh` is the regression harness for the Phase 4 bail-detection prose in `skills/fix-issue/SKILL.md` Step 5a (originally Phase 4 of umbrella #348; renumbered from Step 6a to Step 5a by the fold-find-and-lock refactor closes #496). It is offline, hermetic, and runs against the committed `SKILL.md` — no network, no git state change, no mocks. The harness guards against accidental removal of sixteen literal assertions inside the Step 5a block, covering eleven conceptual checks (the `--issue $ISSUE_NUMBER`, `--no-admin-fallback`, `--coder=$coder`, and `--auto` forwards each appear once per SIMPLE and HARD bullet, so each forward contributes two literal assertions; `--inline` is HARD-only and contributes one positive HARD assertion plus one negative SIMPLE assertion; `--quick` is SIMPLE-only with a positive unconditional check plus a negative HARD check):

- `--issue $ISSUE_NUMBER` in the SIMPLE bullet (forwarded to `/implement` so it adopts the queue issue via Phase 3 Branch 2).
- `--issue $ISSUE_NUMBER` in the HARD bullet (same rationale).
- `--no-admin-fallback` in the SIMPLE bullet (issue #559 — branch-protection bypass safety flag forwarded so `/fix-issue --no-admin-fallback` callers are not silently exposed to an `--admin` override).
- `--no-admin-fallback` in the HARD bullet (same rationale).
- `--coder=$coder` in the SIMPLE bullet (pass-through implementer-selection flag forwarded so `/fix-issue --coder=<value>` callers reach `/implement` Step 2's coder selector).
- `--coder=$coder` in the HARD bullet (same rationale).
- `[--auto if auto_mode]` in the SIMPLE bullet (pass-through autonomous-mode flag forwarded so `/fix-issue --auto` callers reach `/implement`'s autonomous-mode behavior).
- `[--auto if auto_mode]` in the HARD bullet (same rationale).
- `[--inline if inline_mode]` in the HARD bullet (issue #1040 — pass-through `/design` execution-topology flag forwarded so `/fix-issue --inline` callers reach `/implement`'s `--inline` semantics on the path that actually invokes `/design`).
- The SIMPLE bullet does NOT contain `[--inline if inline_mode]` — encodes the design decision that SIMPLE uses `/implement --quick` (which skips `/design`), so forwarding `--inline` there would be a no-op; the assertion checks for the forwarding spell rather than the substring `--inline` so prose mentions on that line stay tolerated.
- The HARD bullet does NOT contain `[--quick if quick_mode]` — SIMPLE is now the default, so the old no-op safety net is removed; the HARD bullet no longer conditionally forwards `--quick`.
- The SIMPLE bullet unconditionally contains `--quick` — encodes that SIMPLE always uses `/implement --quick` (the reduced review loop path); the assertion checks for the bare substring `--quick` on the SIMPLE line.
- `IMPLEMENT_BAIL_REASON=adopted-issue-closed` — the exact machine token `/implement` emits when the adopted issue is CLOSED; `/fix-issue` scans captured output for this literal.
- `/implement bailed: issue #` — the user-visible warning prefix printed on the bail branch.
- `` Do NOT call `issue-lifecycle.sh close` `` — specific directive fragment (not a bare `Do NOT call` substring) that prevents silent re-routing of the bail path back to Step 6's close call. The full phrase is required because the awk extraction window also includes section 5b, which contains an unrelated `Do NOT call \`/implement\`` sentence.
- `Skip to Step 8` — cleanup redirect on the bail branch.

Extraction boundary: `^### 5a` (start, prefix match) through `^## Step 6` (end, prefix match; the real heading is `## Step 6 — Close Issue`). This scopes the assertions to Step 5a so stray mentions of these literals elsewhere in `SKILL.md` cannot false-pass the harness.

The harness is wired into `make lint` via the `test-fix-issue-bail-detection` target in `Makefile`. It is added to `agent-lint.toml`'s `exclude` list alongside its sibling contract `.md` because agent-lint's dead-script and S030/orphaned-skill-files rules do not follow Makefile-only references. The paired token-literal assertion on the emitter side lives in `scripts/test-implement-structure.sh` (pins the same token in `skills/implement/SKILL.md`); a rename of the bail token is therefore a dual-repo change caught by CI.

Edit-in-sync: if the Step 5a narrative rewords any of the sixteen literal assertions (eleven conceptual checks) or restructures the bail branch, update this harness and this contract in the same PR.
