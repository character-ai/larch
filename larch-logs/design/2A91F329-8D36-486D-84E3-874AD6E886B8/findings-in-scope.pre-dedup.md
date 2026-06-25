### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: plan.txt:185-196
- **Concern**: Step 8+ `require_near` harness example is still syntactically invalid (prior round-4 fix incomplete).. Scenario: The plan shows one closed `require_near(...)` call then two orphan string literals for the pre-driver fence. Copy-pasting into `scripts/test-implement-structure.sh` fails at parse time, so the second Step 8+ adjacency pin is never enforced.
- **Proposed resolution**: Replace the block with two complete calls: first `require_near(skill, matrix_read, route-exit fence, ..., 1200)`, second `require_near(skill, matrix_read, pre-driver fence, ..., <limit>)`, each with balanced parentheses.



### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: plan.txt:200-204
- **Concern**: Step 18 entry-read harness snippet is not valid Python.. Scenario: Lines 202-204 are bare string literals with no `require_near(` wrapper, so implementers following the plan cannot add the Step 18 gate adjacency check.
- **Proposed resolution**: Wrap in a full `require_near(skill, '**MANDATORY — READ ENTIRE FILE**: Read ...step18-cleanup.md` completely.', 'bash "$IMPLEMENT_TMPDIR/larch-run.sh" skills/implement/scripts/step-18.sh --phase gate', 'Step 18 cleanup read before gate fence', 1200)` call matching the Step 8+ pattern.



### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: plan.txt:263-267
- **Concern**: Design `assert_followed_count_at_least` Call 1 example is still missing its closing `)`.. Scenario: The snippet ends after the label argument without `)`, so `scripts/test-design-structure.sh` fails at parse time and the invariant→finalize-read adjacency pin is not enforced.
- **Proposed resolution**: Close Call 1 with `)` before Call 2; keep Call 2 outside the same fenced example or close/reopen the fence explicitly.



### FINDING_4:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: plan.txt:269-273
- **Concern**: Design `assert_line_precedes` Call 2 omits the finalize entry-read needle and only names the prepare fence.. Scenario: A helper comparing one line cannot prove finalize-step5 loads before `design-step5b-prepare.sh`; the check would be a no-op or wrong operand.
- **Proposed resolution**: Add the helper signature to the plan (copy-paste-safe awk body) and call it with finalize read as the first needle and the prepare fence as the second: `assert_line_precedes "$SKILL_MD" '<finalize MANDATORY READ line>' '"$HOME/.cache/larch/sessions/design-run-$PPID.sh" design-step5b-prepare.sh' '...'`.



### FINDING_5:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:183-198
- **Concern**: Step 8+ second `require_near` uses a 1200-char window from the section-top entry read, but retained inline skeleton prose sits between that read and `ship pre-driver`.. Scenario: After relocation the entry read is first; handoff rules, `route-exit`, discriminators, and pre-driver predicate remain inline (~1500+ chars). `require_near` only searches ±limit around the anchor, so the pre-driver fence will not be found even when ordering is correct and `make lint` fails on a valid SKILL layout.
- **Proposed resolution**: Switch the pre-driver pin to `assert_line_precedes`-style ordering (add a Python equivalent to `test-implement-structure.sh`) or chain anchors (`require_near` from read→route-exit, then route-exit→pre-driver) with limits sized to the retained skeleton.



### FINDING_6:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: plan.txt:269-273
- **Concern**: Plan mandates a new `assert_line_precedes` bash helper but does not ship a copy-paste-safe definition.. Scenario: Edge cases require harness examples to be copy-paste safe; without the awk function body implementers may invent incompatible semantics (windowed vs global, first vs last match) and still pass review.
- **Proposed resolution**: Include the full helper in the plan (mirroring `assert_followed_count_at_least` style) plus one worked example showing first-line-index `<` second-line-index across the Step 5b skeleton gap.



### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: plan.txt:185-195
- **Concern**: [Prior round FINDING_4/9 incomplete] Step 8+ `require_near` plan embed is still not copy-paste-safe Python. Scenario: The first `require_near(...)` closes at line 193; lines 194-195 are orphan string literals. Pasting verbatim breaks `scripts/test-implement-structure.sh` at import time or omits the pre-driver adjacency pin while route-exit may be the only enforced fence.
- **Proposed resolution**: Show two complete calls: `require_near(skill, matrix_read, '... ship route-exit', ..., 1200)` and `require_near(skill, matrix_read, '... ship pre-driver', ..., 1200)` with balanced parentheses and no dangling arguments.



### FINDING_8:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: plan.txt:200-204
- **Concern**: Step 18 entry-read `require_near` plan embed omits the function invocation. Scenario: The block lists only three string arguments with no `require_near(skill,` opener or closing `)`. Implementers cannot paste it; Step 18 read-before-gate ordering stays unenforced.
- **Proposed resolution**: Replace with one complete `require_near(skill, '<cleanup MANDATORY READ line>', 'bash "$IMPLEMENT_TMPDIR/larch-run.sh" skills/implement/scripts/step-18.sh --phase gate', 'Step 18 cleanup read before gate fence', 1200)`.



### FINDING_9:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: plan.txt:264-267
- **Concern**: [Prior round FINDING_1 incomplete] Design Call 1 `assert_followed_count_at_least` example still lacks closing `)`. Scenario: The bash snippet ends after the label argument on line 267 with no `)` before Call 2. Copy-paste leaves an unclosed function call and `make lint` fails before any Step 5 entry-read adjacency is enforced.
- **Proposed resolution**: Close Call 1 with `)` on its own line immediately after the `'SKILL Step 5 must load finalize-step5 immediately after invariant'` argument.



### FINDING_10:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: plan.txt:271-273
- **Concern**: Design Call 2 `assert_line_precedes` omits the finalize entry-read needle and cannot enforce read-before-prepare. Scenario: Call 2 passes only the prepare-fence string plus a label; the proposed helper compares two line needles, but the early needle (`finalize-step5.md` MANDATORY READ) is absent. Even with a new helper, the check would not prove finalize loads before `design-step5b-prepare.sh`.
- **Proposed resolution**: Give `assert_line_precedes` three needles after `"$SKILL_MD"`: the exact finalize entry-read line, then the prepare-fence line, then the label; document helper signature as `file early_line late_line label`.



### FINDING_11:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: scripts/test-implement-structure.sh:185-196
- **Concern**: Step 8+ harness example is still not copy-paste-safe: second `require_near` is missing after the first call closes.. Scenario: The plan claims two complete `require_near` calls, but lines 194-195 are orphan string literals. Pasting verbatim leaves pre-driver adjacency unenforced or breaks the Python heredoc at import time.
- **Proposed resolution**: Add a second full `require_near(skill, matrix_read, 'bash "$IMPLEMENT_TMPDIR/larch-run.sh" python/cli.py ship pre-driver', 'Step 8+ matrix read before pre-driver fence', 1200)` call; delete the dangling literals.



### FINDING_12:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: scripts/test-implement-structure.sh:200-204
- **Concern**: Step 18 entry-read harness snippet omits the `require_near(` opener and `skill` anchor argument.. Scenario: The block is only three string literals plus a label. Implementers cannot paste it into `test-implement-structure.sh` without reconstructing the call, so Step 18 cleanup read-before-gate ordering may never be pinned.
- **Proposed resolution**: Replace the fragment with one complete call: `require_near(skill, '<MANDATORY READ step18-cleanup.md line>', 'bash "$IMPLEMENT_TMPDIR/larch-run.sh" skills/implement/scripts/step-18.sh --phase gate', 'Step 18 cleanup read before gate fence', <limit>)`.



### FINDING_13:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: scripts/test-design-structure.sh:263-267
- **Concern**: Design Step 5 `assert_followed_count_at_least` Call 1 still lacks the closing `)`.. Scenario: Round-4 accepted fix is incomplete. Copy-pasting Call 1 fails bash parse or drops the invariant→finalize-read adjacency check.
- **Proposed resolution**: Close Call 1 with `)'` after the count/label line and end the ```bash fence before Call 2 prose.



### FINDING_14:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: scripts/test-design-structure.sh:271-273
- **Concern**: `assert_line_precedes` Call 2 omits the finalize entry-read needle and only names the prepare fence.. Scenario: The plan requires finalize read before `design-step5b-prepare.sh`, but the snippet passes one path and a label. The helper cannot enforce ordering without both needles.
- **Proposed resolution**: Use `assert_line_precedes "$SKILL_MD" '<finalize-step5 MANDATORY READ line>' '"$HOME/.cache/larch/sessions/design-run-$PPID.sh" design-step5b-prepare.sh' 'SKILL Step 5 must load finalize-step5 before prepare fence'`.



### FINDING_15:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-implement-structure.sh:23-31
- **Concern**: `require_near` does not enforce read-before-fence ordering.. Scenario: It only checks that `after` appears anywhere within ±limit of the anchor. A `route-exit`, `pre-driver`, or `step-18.sh --phase gate` fence placed before the entry read but within the window can still pass, so relocated matrix/cleanup reads may be skipped on first entry while harness stays green.
- **Proposed resolution**: For Step 8+ and Step 18 entry reads, use an ordered helper (`assert_line_precedes` in the design harness, or add the same awk helper to the implement harness) instead of proximity-only `require_near`.



### FINDING_16:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-implement-structure.sh:192
- **Concern**: Step 8+ `require_near` limit 1200 may be too small for the retained inline skeleton.. Scenario: After relocation the plan still keeps handoff rules, pre-driver predicate, routing bullets, and discriminators between the entry read and `ship pre-driver`. That gap is plausibly >1200 characters, so a correct SKILL layout can fail `make lint` or force implementers to drop the second adjacency check.
- **Proposed resolution**: Raise the limit to match other immediate-background pins (1400–2000), split into ordered line-index checks, or shrink/count the inline skeleton bytes in the plan before fixing the limit.



### FINDING_17:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: scripts/test-implement-structure.sh:185-196
- **Concern**: Step 8+ `require_near` harness example is still not copy-paste safe despite the plan claiming two complete calls.. Scenario: The snippet closes the first `require_near(` at line 193, then leaves `'bash … ship pre-driver'` and a label string as orphan arguments with no second `require_near(` opener, limit, or closing `)`. Copy-pasting verbatim yields a Python syntax error or omits pre-driver adjacency while the plan text says both fences are pinned.
- **Proposed resolution**: Replace lines 185–196 with two full calls, e.g. reuse `matrix_read`, then `require_near(skill, matrix_read, 'bash "$IMPLEMENT_TMPDIR/larch-run.sh" python/cli.py ship route-exit', 'Step 8+ matrix read before route-exit fence', 1200)` and a second `require_near(skill, matrix_read, 'bash "$IMPLEMENT_TMPDIR/larch-run.sh" python/cli.py ship pre-driver', 'Step 8+ matrix read before pre-driver fence', 1200)`.



### FINDING_18:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: scripts/test-implement-structure.sh:200-204
- **Concern**: Step 18 entry-read adjacency block is an incomplete `require_near` invocation.. Scenario: The plan lists only two string literals (cleanup read line and gate fence) without `require_near(skill, …)`, label, or `limit`. Implementers have no valid Python to add, so Step 18 on-entry read ordering stays unenforced like the accepted FINDING_11 gap.
- **Proposed resolution**: Emit one complete call: `require_near(skill, '**MANDATORY — READ ENTIRE FILE**: Read \`${CLAUDE_PLUGIN_ROOT}/skills/implement/references/step18-cleanup.md\` completely.', 'bash "$IMPLEMENT_TMPDIR/larch-run.sh" skills/implement/scripts/step-18.sh --phase gate', 'Step 18 cleanup read before gate fence', 1200)` (adjust limit if post-banner skeleton exceeds 1200 chars).



### FINDING_19:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: scripts/test-design-structure.sh:263-267
- **Concern**: Design Step 5 `assert_followed_count_at_least` Call 1 example is missing its closing parenthesis.. Scenario: The bash example ends after the label argument with no `)`. Pasting into `scripts/test-design-structure.sh` fails at parse time, so invariant→finalize-read adjacency is never registered even though FINDING_1/6 were accepted to fix this area.
- **Proposed resolution**: Close Call 1 with `)` after the label line; keep Call 2 outside the bash fence or close the fence before Call 2 prose.



### FINDING_20:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: scripts/test-design-structure.sh:271-273
- **Concern**: `assert_line_precedes` example omits the finalize entry-read needle and misorders arguments.. Scenario: The helper contract is first-needle line index `<` second-needle line index. The example passes only the prepare-fence string and a label, not the `finalize-step5.md` MANDATORY READ line, so the check cannot enforce “entry read before prepare fence” and may compare the wrong tokens.
- **Proposed resolution**: Add the missing first needle and label, e.g. `assert_line_precedes "$SKILL_MD" '**MANDATORY — READ ENTIRE FILE**: Read \`${CLAUDE_PLUGIN_ROOT}/skills/design/references/finalize-step5.md\` completely.' '"$HOME/.cache/larch/sessions/design-run-$PPID.sh" design-step5b-prepare.sh' 'SKILL Step 5 must load finalize-step5 before prepare fence'`, and document the new helper’s exact arity in the plan.



### FINDING_21:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-implement-structure.sh:23-31
- **Concern**: Planned Step 8+/18 adjacency snippets are still not copy-paste safe. Scenario: The current helper requires require_near(path, before, after, label, limit=900). The plan's Step 8+ block closes after the route-exit call and leaves pre-driver as orphan strings, and the Step 18 block lists only three arguments. Copying either into the Python heredoc either breaks parsing or omits the entry-read pin, so make lint can fail or the relocated reference can be skipped on first entry.
- **Proposed resolution**: Replace the snippets with three complete calls: require_near(skill, matrix_read, route-exit fence, label, 1200), require_near(skill, matrix_read, pre-driver fence, label, 1200), and require_near(skill, cleanup_read, step-18 gate fence, label, explicit limit).



### FINDING_22:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-design-structure.sh:33-48
- **Concern**: Planned assert_line_precedes call omits the finalize-read needle. Scenario: The plan says the helper should verify first needle line index is before second needle line index, but the proposed call passes only SKILL_MD, the prepare fence, and the label. With a normal helper, the prepare fence becomes the first needle and the label becomes the second, or the call fails for missing arguments. The harness then does not prove finalize-step5.md is read before design-step5b-prepare.sh.
- **Proposed resolution**: Add the finalize-step5 mandatory-read string as the first needle and the prepare fence as the second needle, for example assert_line_precedes "$SKILL_MD" '<finalize-step5 read line>' '"$HOME/.cache/larch/sessions/design-run-$PPID.sh" design-step5b-prepare.sh' 'SKILL Step 5 must load finalize-step5 before prepare fence'.



