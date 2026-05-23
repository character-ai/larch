## Plan

## Implementation Plan — Misc /implement cleanup (issue #2595)

Three independent cleanups bundled in one PR. All edits are docs/prompt updates plus one test-pin sync — no runtime code logic changes. Scope is deliberately narrow: only the three items the issue body enumerates (A: dynamic-archetypes argv removal, B: breadcrumb trim, C: stale `--auto` mentions).

### Item A — Remove `--no-dynamic-archetypes` and `--dynamic-archetypes <N>` argv flags from `/implement`

The internal mechanism (`LARCH_DYNAMIC_ARCHETYPES_MAX` env var, default 6, valid 0..8) stays in place. Only the user-facing CLI argv surface is removed. Internal session-env propagation from a parent skill (via `session-setup.sh --caller-env` reading `LARCH_DYNAMIC_ARCHETYPES_MAX` and forwarding via `write-session-env.sh --dynamic-archetypes`) is preserved — that path is not user-typed.

Files to modify:

- `skills/implement/SKILL.md`
  - Line 4 `argument-hint:` — drop `[--no-dynamic-archetypes] [--dynamic-archetypes <N>]` tokens.
  - Flag table (lines 172-173) — delete the two flag rows.
  - "Removed argv surfaces" line (line 187) — append `--no-dynamic-archetypes`, `--dynamic-archetypes` to the comma-separated list (in alphabetical sort with existing tokens or appended at end; pick one and stay consistent).
  - SESSION_ENV_PATH read block at lines 395-405 — keep as-is (it inherits from parent session-env, not argv). The `-z "${dynamic_archetypes_value:-}"` guard is now vacuously true on first hit but harmless; leave the form unchanged so future re-introduction of internal propagation does not need to re-add the guard.
  - Line 420 (`session_env_args+=(--dynamic-archetypes ...)`) — keep as-is; it forwards inherited session-env to child `write-session-env.sh` and remains correct.
  - Step 5 banner derivation prose at line 1186 — narrow the description of `dynamic_archetypes_value` from "Step 0 parsed or inherited a validated explicit/session-env cap" to "Step 0 inherited a validated session-env cap" (the argv path no longer sets it).

- `skills/im/SKILL.md` line 16 — remove `--no-dynamic-archetypes`, `--dynamic-archetypes` from the forwarded-flag list AND add them to the removed-argv-surfaces parenthetical so the same flags don't appear in both lists.

- `README.md` line 65 — drop the two flag tokens from the `<code>…</code>` argument-hint cell.

- `.claude-plugin/plugin.json` line 4 (`description`) — drop `--no-dynamic-archetypes`, `--dynamic-archetypes` from the inline flag enumeration.

- `docs/skills.md` line 58 — drop the two flag tokens from the `/implement` `Arguments:` line.

- `scripts/test-implement-positional-issue.sh`
  - Line 13 `argument-hint` literal — drop `[--no-dynamic-archetypes] [--dynamic-archetypes <N>]`.
  - Lines 19-25 removed-argv tail literal — append `--no-dynamic-archetypes`, `--dynamic-archetypes` to the heredoc-quoted comma list, matching the exact ordering chosen in `SKILL.md` line 187.

Internal scripts (`scripts/run-step5-review.sh`, `scripts/write-session-env.sh`, `scripts/session-setup.sh`, `skills/review-and-fix/scripts/review-and-fix.sh`) keep their `--dynamic-archetypes` argument flags — those are inter-script internal interfaces, not user-typed argv. The orchestrator-level CLI flag is the only thing removed.

### Item B — Remove `[base 5 + degraded-round retries]` from `/implement 5: code review` breadcrumb

One edit:

- `skills/implement/SKILL.md` line 1188 — delete the ` [base 5 + degraded-round retries]` parenthetical from the breadcrumb format string. The new string reads:

  `> **🔶 /implement 5: code review — review-and-fix.sh, up to $effective_round_cap rounds; 3-judge panel on round 1 (Claude+Codex+Cursor), 2-judge on rounds 2+ (Claude+Cursor); review panel: 6 Cursor specialists; dynamic-archetypes cap=$dynamic_archetypes_cap**`

The runtime behavior (base 5 + degraded-round retries) is unchanged; only the user-visible breadcrumb annotation is dropped. `scripts/test-quick-mode-docs-sync.sh` POS_MARKERS pin `"3-judge panel on round 1"` and `"6 Cursor specialists"`, both of which remain — no test sync needed.

### Item C — Audit and clean up stale `--auto` mentions

The user noticed `--auto` referenced misleadingly. `--auto` was removed from `/implement` argv (issue #2497) but several docs still describe `/alias` as forwarding `--auto` to `/implement`. Since `/implement` rejects `--auto`, those docs are stale. Clean up the cross-doc trail; do not touch CHANGELOG (historical record), do not touch test pins that prohibit `--auto` reintroduction, and do not touch `--auto-mode` (a separate token in `scripts/write-session-env.sh` already removed from `step2-implement.sh` per #2497).

**Scope guard — `gh --auto` is OUT OF SCOPE**. `gh pr merge --auto` is GitHub CLI's built-in auto-merge flag (queues a merge once required checks pass) — it is NOT a larch flag and was not removed by issue #2497. The `gh pr merge` error message that originally prompted this audit (`add the --auto flag` suggestion in `gh`'s own stderr) refers to gh's flag, not ours. Do NOT remove, rewrite, or annotate any `gh --auto`, `gh pr merge --auto`, or similar gh-CLI flag references in scripts, docs, or `gh` invocations. Item C touches only references that describe **/implement** (or a delegator forwarding to `/implement`) accepting `--auto`. If a grep hit shows `gh ... --auto`, leave it alone.

Files to modify:

- `skills/alias/SKILL.md`
  - Line 12 (description first sentence) — replace `Delegates to /implement --auto for the full pipeline` with `Delegates to /implement for the full pipeline`.
  - Line 163 (announce-line print) — replace `delegating to /implement --auto [--merge]` with `delegating to /implement [--merge]`.
  - Line 167 (args literal for the Skill tool call) — replace `"--auto [--merge] <feature-description>"` with `"[--merge] <feature-description>"`. This is a real behavioral fix: passing `--auto` to current `/implement` would either be rejected or silently ignored depending on agent interpretation, and removing it brings `/alias`'s forwarded args into compliance with the issue-anchored `/implement` contract.

- `docs/skills.md` line 24 — drop ` with --auto (and other preset flags)` from the `/alias` description. The line now reads: `Create an alias for a larch skill with preset flags. Delegates to /implement for the full pipeline per skills/alias/SKILL.md (code review, version bump, PR). --merge also merges the PR.`

- `docs/workflow-lifecycle.md`
  - Line 35 (mermaid edge label) — change `ALIAS["/alias"] -->|"--auto $ARGS"| IMPLEMENT` to `ALIAS["/alias"] -->|"$ARGS"| IMPLEMENT`.
  - Line 43 — drop `with --auto (and any other preset flags)` from the `/alias` bullet so it reads `delegates to /implement (and any preset flags)`.
  - Line 111 — delete the entire `--auto` row from the flag table (`/design`, `/alias`). The `--auto` flag no longer exists on any of those skills' public argv per current SKILL.md sources. After this removal, the table contains `--quick`, `--full`, `--no-issue` rows.

### Approach

Surgical text edits across 10 files. No runtime script changes, no test logic changes — only the test-pin literal assertions in `scripts/test-implement-positional-issue.sh` need to mirror the SKILL.md argument-hint and removed-argv-list changes. Each item is independent; bundle in one PR because they share the same `/implement` cleanup theme and produce small contiguous diffs in the same files.

### Files to modify (consolidated)

1. `skills/implement/SKILL.md` — Items A & B (argument-hint, flag-table rows, removed-argv list, prose at line 1186, breadcrumb at line 1188)
2. `skills/im/SKILL.md` — Item A (forwarded-flag list at line 16)
3. `skills/alias/SKILL.md` — Item C (lines 12, 163, 167)
4. `README.md` — Item A (line 65)
5. `.claude-plugin/plugin.json` — Item A (line 4 description)
6. `docs/skills.md` — Items A & C (lines 24, 58)
7. `docs/workflow-lifecycle.md` — Item C (lines 35, 43, 111)
8. `scripts/test-implement-positional-issue.sh` — Item A (lines 13, 19-25 literal sync)

### Edge cases

- The flag-table row deletions in `skills/implement/SKILL.md` must keep the `--coder` and `--run-id` rows adjacent without leaving a blank line — markdown table rendering is sensitive to blank lines mid-table.
- The "Removed argv surfaces" list in `skills/implement/SKILL.md` line 187 must remain a single line (no wrapping inserted by an editor's auto-format); `scripts/test-implement-positional-issue.sh` greps the full literal as a single token.
- `docs/workflow-lifecycle.md` mermaid edge label change must keep the existing pipe-delimited label syntax (`|"…"|`); the surrounding nodes (`ALIAS`, `IMPLEMENT`) and `style` lines stay byte-identical.
- `.claude-plugin/plugin.json` is JSON: the `description` value is a single string. The deleted flag tokens are embedded in a longer comma list — keep the comma-spacing and surrounding text intact so JSON parses and the prose still reads cleanly.
- `scripts/test-implement-positional-issue.sh` heredoc body at lines 20-22 is byte-exact-matched via `grep -Fq` against the SKILL.md flag list; the test list ordering must exactly match SKILL.md line 187 token-for-token.
- `skills/alias/SKILL.md` line 167 `args:` field is the literal string passed to the Skill tool; removing `--auto` does NOT change the spawn shape (still goes through the same Skill tool invocation) — the only delta is what `/implement` parses.

### Failure modes

Omitted — purely documentation/argv-surface cleanup with no algorithmic or systemic behavior change. Test pins catch any drift between SKILL.md and tests; quick-mode docs-sync test catches reintroduced `/implement --auto` literal in public docs.

### Testing strategy

1. `bash scripts/test-implement-positional-issue.sh` — must pass with the new pins (argument-hint sans dynamic-archetypes, removed-argv tail including dynamic-archetypes flags).
2. `bash scripts/test-implement-structure.sh` — must still pass; the `--auto` reintroduction guard is unchanged.
3. `bash scripts/test-quick-mode-docs-sync.sh` — must still pass; STALE_PHRASES forbid `/implement --auto` in public docs and our removal makes the public-doc check trivially pass.
4. `bash scripts/relevant-checks.sh` (or `make lint`) — runs the repository's pre-commit hooks; must pass.
5. Spot check: `grep -rEn -- '--no-dynamic-archetypes|--dynamic-archetypes' --include='*.md' --include='*.json' .` (excluding `larch-logs/` and internal scripts) returns zero hits in user-facing surfaces after the edit.
6. Spot check: `grep -Fn -- '/implement --auto' docs/ skills/alias/` returns zero hits after the edit.

### Diff size estimate

~80 changed lines net (mostly small per-file deletions/word-level edits across 8 files; the largest single block is the `docs/workflow-lifecycle.md` row deletion and the `scripts/test-implement-positional-issue.sh` literal sync).


## Acceptance

1. `bash scripts/test-implement-positional-issue.sh` passes — `argument-hint` literal no longer contains `[--no-dynamic-archetypes]` / `[--dynamic-archetypes <N>]`; the removed-argv tail literal includes both new tokens (matching the SKILL.md line 187 ordering token-for-token).
2. `bash scripts/test-implement-structure.sh` passes — the `--auto` reintroduction guard still trips when violated.
3. `bash scripts/test-quick-mode-docs-sync.sh` passes — public docs (README.md, docs/review-agents.md, docs/workflow-lifecycle.md, docs/skills.md) contain no `/implement --auto` literal.
4. `bash scripts/relevant-checks.sh` (or `make lint`) passes end-to-end.
5. `grep -rEn -- '--no-dynamic-archetypes|--dynamic-archetypes' --include='*.md' --include='*.json' .` (excluding `larch-logs/` and internal scripts under `scripts/`, `skills/review-and-fix/scripts/`, `skills/review/scripts/`) returns zero hits in user-facing surfaces.
6. `grep -Fn -- '/implement --auto' docs/ skills/alias/` returns zero hits.
7. `grep -Fn -- 'gh pr merge --auto'` or any `gh ... --auto` invocation is unchanged from main — `gh`'s built-in `--auto` flag is OUT OF SCOPE for Item C.
8. `/implement <fresh-issue>` invoked without `--no-dynamic-archetypes` / `--dynamic-archetypes` succeeds with `dynamic_archetypes_cap=6` (the default), and the Step 5 banner reads `up to N rounds; 3-judge panel on round 1 ...` (no `[base 5 + degraded-round retries]` substring).

diff_lines: 80
