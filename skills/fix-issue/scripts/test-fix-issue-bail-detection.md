# skills/fix-issue/scripts/test-fix-issue-bail-detection.sh — contract

`skills/fix-issue/scripts/test-fix-issue-bail-detection.sh` is the regression harness for the Phase 4 bail-detection prose in `skills/fix-issue/SKILL.md` Step 5a (originally Phase 4 of umbrella #348; renumbered from Step 6a to Step 5a by the fold-find-and-lock refactor closes #496). It is offline, hermetic, and runs against the committed `SKILL.md` — no network, no git state change, no mocks. The harness guards against accidental removal of literal assertions inside the Step 5a block, covering thirteen conceptual checks:

- Positional `$ISSUE_NUMBER` tail after `--merge` (issue-anchored `/implement` adopts via argv position, not removed `--issue`).
- `--no-admin-fallback` in the invocation (issue #559 — branch-protection bypass safety flag forwarded so `/fix-issue --no-admin-fallback` callers are not silently exposed to an `--admin` override).
- `--coder=$coder` in the invocation (pass-through implementer-selection flag forwarded so `/fix-issue --coder=<value>` callers reach `/implement` Step 2's coder selector).
- `[--no-logs-commit if no_logs_commit]` in the invocation — optional larch-log suppression flag.
- `SESSION_ENV_PATH="$FIX_ISSUE_TMPDIR/session-env.sh"` export prose — caller session-env merge for `/implement` Step 0 (`session-setup.sh --caller-env`).
- The literal forward `--session-env $FIX_ISSUE_TMPDIR` is absent — guards the removed argv surface.
- `IMPLEMENT_BAIL_REASON=adopted-issue-closed` — the exact machine token `/implement` emits when the adopted issue is CLOSED; `/fix-issue` scans captured output for this literal.
- `/implement bailed: issue #` — the user-visible warning prefix printed on the bail branch.
- `` Do NOT call `issue-lifecycle.sh close` `` — specific directive fragment (not a bare `Do NOT call` substring) that prevents silent re-routing of the bail path back to Step 6's close call. The full phrase is required because the awk extraction window also includes section 5b, which contains an unrelated `Do NOT call \`/implement\`` sentence.
- `Skip to Step 8` — cleanup redirect on the bail branch.
- `Invoke` followed by `/implement` via the Skill tool — delegation mandate that anchors anti-pattern #5 (NEVER implement inline at Step 5a using Edit/Write/Bash file-modification tools instead of delegating to `/implement` via the Skill tool; closes #1988).
- `larch:implement` present — confirms the canonical Skill name appears in the Step 5a block, anchoring anti-pattern #9 (NEVER use any name other than `larch:implement` as the `skill:` field). Added to address the wrong-skill-name failure mode described in issue #2136 (fixed by issue #2144).
- `larch:fix-issue` absent — guards against the recursive self-invocation failure (issue #2136) where the orchestrator used `skill: "larch:fix-issue"` instead of `"larch:implement"`, permanently sticking the issue in `[IN PROGRESS]`. The NEVER #9 explanatory prose mentioning the wrong name lives in the Anti-patterns section, which is outside the awk extraction window, so this absence check is not confused by that prose.

Extraction boundary: `^### 5a` (start, prefix match) through `^<!-- step:6` (end, prefix match; the real anchor is `<!-- step:6 — Finalize -->`). This scopes the assertions to Step 5a so stray mentions of these literals elsewhere in `SKILL.md` cannot false-pass the harness.

The harness is wired into `make lint` via the `test-fix-issue-bail-detection` target in `Makefile`. It is added to `agent-lint.toml`'s `exclude` list alongside its sibling contract `.md` because agent-lint's dead-script and S030/orphaned-skill-files rules do not follow Makefile-only references. `scripts/test-implement-structure.sh` pins unrelated `/implement` SKILL.md invariants separately; changing Step 5a literals still requires updating this harness and this contract in the same PR as `skills/fix-issue/SKILL.md`.

Edit-in-sync: if the Step 5a narrative rewords any of the literal assertions or restructures the bail branch, update this harness and this contract in the same PR.
