### FINDING_1: Step 8+ `require_near` harness snippet syntactically invalid (orphan literals after first call)
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Codex-Generic
- **Severity**: blocking
- **Concern**: The Step 8+ harness example in the plan is not copy-paste-safe Python. The first `require_near(...)` closes, then pre-driver fence and label appear as orphan string literals with no second `require_near(` opener, limit, or closing `)`. Pasting verbatim breaks `scripts/test-implement-structure.sh` at parse/import time or omits the pre-driver adjacency pin while route-exit may be the only enforced fence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Replace the block with two complete calls: first `require_near(skill, matrix_read, route-exit fence, ..., 1200)`, second `require_near(skill, matrix_read, pre-driver fence, ..., <limit>)`, each with balanced parentheses.
  - From Cursor-Innovation: Show two complete calls: `require_near(skill, matrix_read, '... ship route-exit', ..., 1200)` and `require_near(skill, matrix_read, '... ship pre-driver', ..., 1200)` with balanced parentheses and no dangling arguments.
  - From Cursor-Pragmatic: Add a second full `require_near(skill, matrix_read, 'bash "$IMPLEMENT_TMPDIR/larch-run.sh" python/cli.py ship pre-driver', 'Step 8+ matrix read before pre-driver fence', 1200)` call; delete the dangling literals.
  - From Cursor-Requirements: Replace lines 185–196 with two full calls, e.g. reuse `matrix_read`, then `require_near(skill, matrix_read, 'bash "$IMPLEMENT_TMPDIR/larch-run.sh" python/cli.py ship route-exit', 'Step 8+ matrix read before route-exit fence', 1200)` and a second `require_near(skill, matrix_read, 'bash "$IMPLEMENT_TMPDIR/larch-run.sh" python/cli.py ship pre-driver', 'Step 8+ matrix read before pre-driver fence', 1200)`.
  - From Codex-Generic: Replace the snippets with three complete calls: require_near(skill, matrix_read, route-exit fence, label, 1200), require_near(skill, matrix_read, pre-driver fence, label, 1200), and require_near(skill, cleanup_read, step-18 gate fence, label, explicit limit).


### FINDING_2: Step 18 entry-read `require_near` harness snippet incomplete (missing invocation)
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Codex-Generic
- **Severity**: blocking
- **Concern**: The Step 18 adjacency block lists only string literals (cleanup read line and gate fence) without a full `require_near(skill, …)` wrapper, label, limit, or closing `)`. Implementers cannot paste it into `scripts/test-implement-structure.sh`, so Step 18 cleanup read-before-gate ordering stays unenforced.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Wrap in a full `require_near(skill, '**MANDATORY — READ ENTIRE FILE**: Read ...step18-cleanup.md` completely.', 'bash "$IMPLEMENT_TMPDIR/larch-run.sh" skills/implement/scripts/step-18.sh --phase gate', 'Step 18 cleanup read before gate fence', 1200)` call matching the Step 8+ pattern.
  - From Cursor-Innovation: Replace with one complete `require_near(skill, '<cleanup MANDATORY READ line>', 'bash "$IMPLEMENT_TMPDIR/larch-run.sh" skills/implement/scripts/step-18.sh --phase gate', 'Step 18 cleanup read before gate fence', 1200)`.
  - From Cursor-Pragmatic: Replace the fragment with one complete call: `require_near(skill, '<MANDATORY READ step18-cleanup.md line>', 'bash "$IMPLEMENT_TMPDIR/larch-run.sh" skills/implement/scripts/step-18.sh --phase gate', 'Step 18 cleanup read before gate fence', <limit>)`.
  - From Cursor-Requirements: Emit one complete call: `require_near(skill, '**MANDATORY — READ ENTIRE FILE**: Read \`${CLAUDE_PLUGIN_ROOT}/skills/implement/references/step18-cleanup.md\` completely.', 'bash "$IMPLEMENT_TMPDIR/larch-run.sh" skills/implement/scripts/step-18.sh --phase gate', 'Step 18 cleanup read before gate fence', 1200)` (adjust limit if post-banner skeleton exceeds 1200 chars).
  - From Codex-Generic: Replace the snippets with three complete calls: require_near(skill, matrix_read, route-exit fence, label, 1200), require_near(skill, matrix_read, pre-driver fence, label, 1200), and require_near(skill, cleanup_read, step-18 gate fence, label, explicit limit).


### FINDING_3: Design `assert_followed_count_at_least` Call 1 missing closing `)`
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: blocking
- **Concern**: The design harness Call 1 example ends after the label argument without a closing `)`. Copy-pasting into `scripts/test-design-structure.sh` fails at bash parse time, so invariant→finalize-read adjacency is never registered.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Close Call 1 with `)` before Call 2; keep Call 2 outside the same fenced example or close/reopen the fence explicitly.
  - From Cursor-Innovation: Close Call 1 with `)` on its own line immediately after the `'SKILL Step 5 must load finalize-step5 immediately after invariant'` argument.
  - From Cursor-Pragmatic: Close Call 1 with `)'` after the count/label line and end the ```bash fence before Call 2 prose.
  - From Cursor-Requirements: Close Call 1 with `)` after the label line; keep Call 2 outside the bash fence or close the fence before Call 2 prose.


### FINDING_4: Design `assert_line_precedes` Call 2 omits finalize entry-read needle
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Codex-Generic
- **Severity**: blocking
- **Concern**: The planned `assert_line_precedes` example passes only the prepare-fence string (and label) as operands. The helper contract requires two line needles (first index `<` second index). Without the `finalize-step5.md` MANDATORY READ line as the early needle, the check cannot prove finalize loads before `design-step5b-prepare.sh` and may be a no-op or compare wrong tokens.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add the helper signature to the plan (copy-paste-safe awk body) and call it with finalize read as the first needle and the prepare fence as the second: `assert_line_precedes "$SKILL_MD" '<finalize MANDATORY READ line>' '"$HOME/.cache/larch/sessions/design-run-$PPID.sh" design-step5b-prepare.sh' '...'`.
  - From Cursor-Innovation: Give `assert_line_precedes` three needles after `"$SKILL_MD"`: the exact finalize entry-read line, then the prepare-fence line, then the label; document helper signature as `file early_line late_line label`.
  - From Cursor-Pragmatic: Use `assert_line_precedes "$SKILL_MD" '<finalize-step5 MANDATORY READ line>' '"$HOME/.cache/larch/sessions/design-run-$PPID.sh" design-step5b-prepare.sh' 'SKILL Step 5 must load finalize-step5 before prepare fence'`.
  - From Cursor-Requirements: Add the missing first needle and label, e.g. `assert_line_precedes "$SKILL_MD" '**MANDATORY — READ ENTIRE FILE**: Read \`${CLAUDE_PLUGIN_ROOT}/skills/design/references/finalize-step5.md\` completely.' '"$HOME/.cache/larch/sessions/design-run-$PPID.sh" design-step5b-prepare.sh' 'SKILL Step 5 must load finalize-step5 before prepare fence'`, and document the new helper’s exact arity in the plan.
  - From Codex-Generic: Add the finalize-step5 mandatory-read string as the first needle and the prepare fence as the second needle, for example assert_line_precedes "$SKILL_MD" '<finalize-step5 read line>' '"$HOME/.cache/larch/sessions/design-run-$PPID.sh" design-step5b-prepare.sh' 'SKILL Step 5 must load finalize-step5 before prepare fence'.


