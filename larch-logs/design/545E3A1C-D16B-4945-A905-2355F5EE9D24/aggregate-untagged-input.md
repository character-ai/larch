### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: python/larch/issue/learn_from_bugs.py:252-260
- **Concern**: Approach does not pin the G-Md-3 ratchet shape pre-commit enforces. Scenario: If the rewrite uses per-line `_HEADING_RE.match` with an inline fence boolean (or without a `set[int]` helper), `python/cli.py lint markdown-heading-fence-state` fails per `test_unrelated_boolean_does_not_count_as_fence_guard`
- **Proposed resolution**: Name the contract in the plan: local `*fence*` helper returns fenced interior `set[int]`; gate with `if index not in fenced and _HEADING_RE.match(line)` (or keep `finditer` filtering and skip per-line `.match` entirely)

### FINDING_3:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/issue/learn_from_bugs.py:246-249; plan.txt:19-25,56-57
- **Concern**: The planned fence handling covers `_split_sections` but leaves `diagnostic_prefix` boundary matching fence-unaware.. Scenario: A bug body containing a fenced example with `## Plan`, `## Approach`, or `### UPDATED:` will be cut at that line before `_split_sections` runs, so later real `#### Root cause` or `#### Suggested fix(es)` sections are lost. This violates the stated rule that heading-shaped lines inside fences must not affect parsing.
- **Proposed resolution**: Make boundary detection ignore fenced lines too, or use one shared fence-aware line scan for both `_BOUNDARY_PATTERNS` and `_split_sections`; retain the existing boundary behavior for headings outside fences.

### FINDING_4:
- **Reviewer(s)**: Cursor-dyn-Markdown Parser Correctness
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/issue/learn_from_bugs.py:252-260
- **Concern**: Plan line-scan rewrite risks wrong character offsets if offsets are rebuilt from splitlines() lengths. Scenario: The current splitter slices with finditer absolute indices (head.end(), next head.start()). A typical splitlines() loop that adds len(line)+1 per row misaligns on CRLF bodies and can shift section boundaries, truncating summary/root-cause text while h2/h3 tests still pass substring checks
- **Proposed resolution**: Track offsets in the original prefix (splitlines(keepends=True), or map fenced line indices to char ranges) and assert slice bounds match today's finditer output; add a golden assert of full digest.sections for STRUCTURED_BODY

### FINDING_5:
- **Reviewer(s)**: Cursor-dyn-Markdown Parser Correctness
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/tests/issue/test_learn_from_bugs.py:75-81
- **Concern**: [ALREADY_ADDRESSED partially] No unit test for unclosed-fence EOF suppression. Scenario: Plan edge cases require unclosed fences to suppress headings through EOF, but issue_create._balanced_fence_line_indices (python/larch/issue/issue_create.py:200-219) only fences balanced spans. Copying it verbatim leaves post-opener headings as phantom boundaries, recreating the bug on bodies with truncated fences
- **Proposed resolution**: Add an explicit fixture: summary text, unclosed opening fence, then a ## Root cause line; assert structured mapping ignores the fenced line and does not split summary early

### FINDING_6:
- **Reviewer(s)**: Cursor-dyn-Markdown Parser Correctness
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/tests/issue/test_learn_from_bugs.py:75-81
- **Concern**: h2/h3 regression pin is too weak for offset-preservation contract. Scenario: Plan requires pinning established h2/h3 names and content, but test_build_digest_structured only checks key set and one root-cause substring, so offset regressions in summary or suggested-fix bodies can slip through
- **Proposed resolution**: In the pin test, assert full digest.sections (or serialized golden) for STRUCTURED_BODY equals pre-change output, not just key membership

### FINDING_7:
- **Reviewer(s)**: Cursor-dyn-Markdown Parser Correctness
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/tests/issue/test_learn_from_bugs.py:25-43
- **Concern**: No test for closing-fence info-string rejection. Scenario: Plan edge cases allow info strings on openers but forbid them on closers; a closer like ``````python`````` that wrongly closes an opener would expose a phantom ## Root cause inside the following summary
- **Proposed resolution**: Add a fixture with an opener info string and a closing line carrying a non-empty suffix; assert the interior heading-shaped line stays in summary and does not open root cause

### FINDING_8:
- **Reviewer(s)**: Codex-dyn-Markdown Parser Correctness
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/tests/issue/test_learn_from_bugs.py:27-30; plan.txt:32-37
- **Concern**: The planned tests do not verify every stated fence-closing rule.. Scenario: An implementation could close a backtick fence with a tilde fence, accept a shorter closing marker, accept trailing text on a closing marker, or resume heading recognition after an unclosed fence while still passing the listed h4, fence-form, and shorter-marker checks. That could create a phantom heading or truncate the canonical section.
- **Proposed resolution**: Add focused parameterized cases for mismatched marker characters, closing markers with trailing info strings, unclosed fences, and each shorter-than-opener case. Assert that headings after an unclosed fence remain unrecognized.

### FINDING_9:
- **Reviewer(s)**: Codex-dyn-Markdown Parser Correctness
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/tests/issue/test_learn_from_bugs.py:27-30; plan.txt:19,44-46
- **Concern**: The planned tests do not directly prove that absolute source offsets remain correct after scanning fenced lines.. Scenario: A line scanner that rebuilds or miscounts the prefix can pass the phantom-heading assertion but slice a real `Root cause` or `Suggested fix(es)` section at the wrong position, dropping its first or last lines.
- **Proposed resolution**: Add a fixture with a multi-line fenced block followed by real canonical headings, and assert the exact complete section contents, including the first line after the fence and the final line before the next heading. Keep the existing h2/h3 byte-stability assertion.
