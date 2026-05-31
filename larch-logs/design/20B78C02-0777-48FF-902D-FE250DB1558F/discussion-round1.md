## Decision 1: Scope — which skills get the refactor
- **Question**: Collapse only `/implement`'s awk fences (issue scope), or generalize to `/design` and `/review` too?
- **Resolution**: `/implement` only. Touch `skills/implement/SKILL.md` and `scripts/write-session-env.sh`. Codebase check showed only `/implement` has the awk fences (41 sites); `/design` already sources a per-PPID env file (and its 2-line prelude also runs a pause-check `exec`, so it cannot reduce to a bare source line); `/review` is a thin prose SKILL with no rehydration fences. File the `/design` + `/review` harmonization as an OOS follow-up.
- **Source**: user (re-confirmed after codebase finding corrected the "all 3" premise)

## Decision 2: Fence replacement completeness
- **Question**: Replace all 41 awk fences uniformly, or keep the awk form at the first/cold-start site defensively?
- **Resolution**: Uniform single guarded source line at all 41 sites. No defensive awk retention. The `-z`/`-f` guards make the line a safe no-op at cold start.
- **Source**: user

## Decision 3: Where the new file is produced
- **Question**: Which writer emits `plugin-root.env`, and how is its path derived?
- **Resolution**: `scripts/write-session-env.sh` emits a sibling `plugin-root.env` in the same directory as its `--output` target (e.g. `$IMPLEMENT_TMPDIR/plugin-root.env` alongside `session-env.sh`). The writer already validates and holds `CLAUDE_PLUGIN_ROOT_VALUE` (write-session-env.sh:136-181) and is invoked at Step 0 via `session-setup.sh --write-session-env` (session-setup.sh:464-499). New output of an existing sanctioned writer — not a mutation of `session-env.sh`.
- **Source**: codebase

## Decision 4: Hard constraint — NEVER #14 (no prompt-side session-env writes)
- **Question**: Does emitting `plugin-root.env` risk the prompt-side-write prohibition?
- **Resolution**: No. The file is produced only by the sanctioned writer; the prelude line only **sources** it. `skills/implement/SKILL.md:62` NEVER #14 stays intact.
- **Source**: codebase

## Decision 5: Hard constraint — no behavioral change
- **Question**: Must the sourced `CLAUDE_PLUGIN_ROOT` equal the awk-extracted value in all cases?
- **Resolution**: Yes. Refactor-only PR: identical resolved value, fewer characters, determinism unchanged. Context-cost win, not a behavior change.
- **Source**: issue

## Decision 6: `set -u` / IMPLEMENT_TMPDIR guard preservation
- **Question**: The issue's proposed one-liner drops the `[ -n "${IMPLEMENT_TMPDIR:-}" ]` guard present in the awk form. Keep it?
- **Resolution**: Preserve a `${IMPLEMENT_TMPDIR:-}`-safe guard so the line stays a safe no-op under `set -u` when `IMPLEMENT_TMPDIR` is unset (canonical form: `[ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/plugin-root.env" ] && . "$IMPLEMENT_TMPDIR/plugin-root.env"`). Matches the existing fence's guard discipline.
- **Source**: codebase

## Decision 7: Verification surface (in-scope for this PR)
- **Question**: What must be re-checked/updated so the refactor is safe?
- **Resolution**: (a) Verify `lint-skill-md-flag-signature.sh` still resolves the unchanged `${CLAUDE_PLUGIN_ROOT}/…` path tokens (it normalizes tokens, does not assert the awk block). (b) Update the "Bash block prelude" prose section to document the one-line source form as canonical and explain why the tmpdir-local minimal file sidesteps both original objections. (c) Re-check rehydration-touching tests: `test-implement-timing-rehydration.sh`, `test-run-step5-review.sh`, `test-run-step1-plan-log.sh`, `test-session-env-roundtrip.sh`. (d) Add a writer-side regression asserting `plugin-root.env` is emitted and sources cleanly. (e) Run `make lint`.
- **Source**: issue + codebase
