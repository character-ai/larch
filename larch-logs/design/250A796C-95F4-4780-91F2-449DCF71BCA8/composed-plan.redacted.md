## Plan

This is a **SIMPLE-tier** doc-only sweep covering 3 of the 10 items originally bundled in this issue. The other 7 items were dropped after Step 0c re-verification: Items A, D, E, F are already addressed in `main` (commit `c17ee7f2`); Items H, I, J reference a "Step 3.6 plan-quality assessor" feature that does not exist anywhere in the tree. See the issue comment posted during /design for the per-item evidence.

### Files to modify

**UPDATED: `docs/linting.md`** — Add one row to the Makefile-targets harness inventory table describing `make test-stall-recovery-report`. The harness already exists at `skills/implement/scripts/test-stall-recovery-report.sh` and is registered as a `test-harnesses-5` shard dependency in `Makefile:57`; only the user-facing inventory row is missing. Insert the new row immediately after the existing `test-ship-pr-rebase-phase14` row (currently line 207) to keep ship/stall-related harnesses grouped. Match the sibling rows' pipe shape and trailing-pipe presence so markdownlint passes.

Row body, exact:

```
| `make test-stall-recovery-report` | Run the offline state-machine harness for `skills/implement/scripts/stall-recovery-report.sh` (classifier, redaction, retry caps, attempts-file containment). Stubs GitHub-facing commands and exercises classifier branches, malformed-state exit 3, sanitization, dry-run propagation, attempts-file idempotency, and public-surface sentinel redaction without network access. A `make lint` prerequisite via the `test-harnesses-5` shard partition. |
```

**UPDATED: `skills/implement/SKILL.md`** — Add a new `### Bash block prelude` subsection between the existing Extracted Script Registry section body (the `extract-closes-issue-from-pr.sh` invocation pin around line 110) and the existing `### Verbosity Control` subsection at line 112. The new subsection documents the canonical 4-line `CLAUDE_PLUGIN_ROOT` rehydration block that 43 byte-identical sites in this file repeat, and explains the chicken-and-egg constraint (the awk extract cannot be replaced with a sourced helper because `CLAUDE_PLUGIN_ROOT` is unset before the helper would itself be found).

**DO NOT modify the existing 43 awk rehydration sites.** They are already byte-identical and serve as the canonical block by example. The consolidation work here is purely documentation: making the canonical reference explicit and discoverable so future authors don't invent variants. Touching the 43 sites carries unjustified risk (every Bash fence has `lint-foreground-markers` / `lint-bash32` invariants, the rehydration is bootstrap-critical, and no sourced-helper refactor is feasible without architectural change to how `IMPLEMENT_TMPDIR/session-env.sh` is consumed).

The new subsection content, exact:

````markdown
### Bash block prelude

The Claude Code Bash tool does NOT preserve shell state between calls, and `CLAUDE_PLUGIN_ROOT` is not in the inherited environment after Step 0. Every Bash block after Step 0 that calls a plugin script via `"${CLAUDE_PLUGIN_ROOT}/..."` MUST first rehydrate `CLAUDE_PLUGIN_ROOT` from `$IMPLEMENT_TMPDIR/session-env.sh` using the canonical 4-line awk block below — do not invent variants:

```bash
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/session-env.sh" ]; then
  CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$IMPLEMENT_TMPDIR/session-env.sh" 2>/dev/null || true)
fi
export CLAUDE_PLUGIN_ROOT
```

The awk extract intentionally avoids `source "$IMPLEMENT_TMPDIR/session-env.sh"` because it would pull in the entire session-env namespace and might shadow caller-side state. A sourced helper script is NOT feasible: until `CLAUDE_PLUGIN_ROOT` is set, the orchestrator has no portable way to find the helper. The 4-line awk block is the bootstrap and must be inlined at each site. This is **the** canonical snippet; the 43 existing sites in this file are byte-identical instances of it. The `${CLAUDE_PLUGIN_ROOT}/scripts/read-session-env-key.sh` helper is used for OTHER session-env keys (after `CLAUDE_PLUGIN_ROOT` is rehydrated) — see the `LARCH_TOKEN_SESSION_ID` rehydration prose below for that pattern.
````

**UPDATED: `skills/design/SKILL.md`** — Change one word at line 375. Current text reads "this cancellation fence and Step 5c item 9"; replace `item 9` with `item 10`. The post-publish `render-final-summary.sh --post-publish-only` invocation lives at numbered item **10** (line 1265); item 9 (line 1264) is `design-log-publish.sh`. The other line-1266 reference "after the Step 5c item 9 publish attempt" is correct as-is (item 9 IS the publish) and must NOT change.

### Approach

- All three edits are pure Markdown changes. No code logic, no script contracts, no test changes, no Makefile targets, no agent-lint topology changes.
- Order: Item G first (one-word edit, smallest blast radius), then Item B (one new table row), then Item C (one new subsection). Each is independent; this order minimizes cascading review attention if any later edit needs revision.
- For Item C, the consolidation interpretation is **define-canonical-once-and-leave-instances-alone**, not **physically-dedupe-bytes**. The 43 sites are already byte-identical; the missing piece is an explicit "this is the canonical snippet" anchor that future authors can cite.

### Edge cases

- **Item B table integrity**: pipe-delimited row alignment must match siblings or markdownlint will flag MD056. Copy the `test-ship-pr-rebase-phase14` row's pipe shape first.
- **Item C insertion position**: place new `### Bash block prelude` immediately before existing `### Verbosity Control` (current line 112); do not touch the worked-example awk block at lines 105-109.
- **Item G surrounding prose**: line 375 narrative only; one-token replacement. The OTHER `item 9` reference at line 1266 (the "publish attempt" reference) is correct and must NOT change.
- **Re-running grep over implement/SKILL.md**: after Item C, `grep -c 'awk.*LARCH_CLAUDE_PLUGIN_ROOT=' skills/implement/SKILL.md` should equal **44** (43 existing + 1 inside the new canonical block).

### Failure modes

1. **Item C accidentally touches the 43 existing rehydration sites.** Highest risk: an implementer interprets "consolidate" as "physically dedupe" and replaces the blocks with a sourced helper. Earliest warning: post-edit grep count `≠ 44` for `awk.*LARCH_CLAUDE_PLUGIN_ROOT=`. Mitigation: plan explicitly forbids it; verification check is the grep count.
2. **Item B's new row breaks the table.** Earliest warning: `pre-commit run markdownlint --files docs/linting.md` flags MD056/MD058, or GitHub preview shows misaligned cells. Mitigation: copy sibling pipe count first, then populate description.
3. **Item C's new `### Bash block prelude` heading conflicts with agent-lint topology.** Earliest warning: `make agent-lint` flags the new heading slug. Mitigation: no existing heading by that name (`grep -n "### Bash block prelude" skills/implement/SKILL.md` is empty); verify post-edit.

### Testing strategy

- No new tests (doc-only sweep, no executable logic changes).
- Validation: `bash scripts/relevant-checks.sh` (or `make lint`) — exercises markdownlint, agent-lint, shellcheck, agnix on the touched files.
- `make test-stall-recovery-report` still passes unchanged (the harness existed already; only the inventory row is being added).

## Acceptance

The PR is acceptable when **all** of the following hold:

1. **Item B**: `docs/linting.md` contains exactly one new row whose first cell reads `` `make test-stall-recovery-report` `` (backticked exact target name), placed immediately after the `test-ship-pr-rebase-phase14` row. The new row matches sibling rows in pipe count and trailing-pipe convention.
2. **Item C**: `skills/implement/SKILL.md` contains exactly one new `### Bash block prelude` subsection inserted immediately before the existing `### Verbosity Control` subsection. The new subsection contains the canonical 4-line awk block in a fenced `bash` codeblock. `grep -c 'awk.*LARCH_CLAUDE_PLUGIN_ROOT=' skills/implement/SKILL.md` equals **44** (43 existing instances preserved + 1 inside the new canonical reference). No existing rehydration site is byte-modified.
3. **Item G**: `skills/design/SKILL.md` line 375 reads "Step 5c item 10" (not "item 9"). The OTHER reference at line 1266 ("after the Step 5c item 9 publish attempt") is unchanged. Net: `grep -c "Step 5c item 9" skills/design/SKILL.md` decreased by 1 and `grep -c "Step 5c item 10" skills/design/SKILL.md` increased by 1 vs. pre-PR.
4. **No other files touched**. The diff covers only `docs/linting.md`, `skills/implement/SKILL.md`, `skills/design/SKILL.md`, plus the standard version-bump + CHANGELOG commit from /implement Step 8.
5. **Validation passes**: `make lint` (or `bash scripts/relevant-checks.sh`) succeeds: markdownlint, agent-lint, shellcheck, agnix all green on the touched files.
6. **CI passes**: GitHub Actions all green on the PR before merge.

diff_lines: 25
