### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:8,30-31
- **Concern**: [SCOPE-REDUCTION] Plan mandates new local regexes in design_oos.py while file_oos._count_non_security_markdown already implements awk-parity counting with coverage in python/test_file_oos.py. Scenario: Re-implementing the awk loop creates a fourth counter alongside file_oos, oos_disposition, and the retiring awk script; design prepare skip-all-security can diverge from python/cli.py oos disposition-gate counts in file_oos.py
- **Proposed resolution**: Replace the subprocess/regex plan with _count_non_security_blocks(text) delegating to file_oos._count_non_security_markdown(text); drop the Do not add a shared counter abstraction and Add local regexes bullets

### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/design_oos.py:81-89
- **Concern**: [SCOPE-REDUCTION] Plan adds a new local regex counter in design_oos instead of reusing the existing Python port in file_oos.py. Scenario: There are already parallel counters in python/file_oos.py (_count_non_security_markdown, exercised by python/test_file_oos.py) and python/oos_disposition.py (count_non_security_oos_blocks). Adding another copy in design_oos creates a fourth implementation of the same awk semantics and increases the chance design Step 5b skip-all-security decisions diverge from implement disposition-gate counts on identical markdown.
- **Proposed resolution**: Replace _count_non_security_blocks with a thin wrapper around file_oos._count_non_security_markdown(text). Drop the planned duplicate regex/helpers and most counter fixture tests; keep one prepare-flow test for skip-all-security.

### FINDING_4:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/design_oos.py:81-89
- **Concern**: [SCOPE-REDUCTION] Plan adds a third independent regex port in design_oos instead of reusing file_oos._count_non_security_markdown. Scenario: Implement disposition already counts the same accepted-OOS markdown via file_oos.count_non_security in disposition_gate; a fresh port in design_oos can diverge on skip-all-security vs gate non_security_oos for the same oos-accepted-design.md text despite duplicated test vectors
- **Proposed resolution**: Replace _count_non_security_blocks body with a call to file_oos._count_non_security_markdown after the empty-input guard; drop the plan step to add local regexes/helpers; keep one prepare-flow skip-all-security test plus optional thin wrapper test

### FINDING_5:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/design_oos.py:81-89
- **Concern**: [SCOPE-REDUCTION] Plan adds a new local regex counter in design_oos.py plus a large duplicate unit matrix in python/test_design_oos.py even though python/file_oos.py:84-106 already implements the same non-security block counting with awk-parity coverage in python/test_file_oos.py.. Scenario: Re-porting the awk loop creates a fourth counter copy (alongside file_oos and oos_disposition) and removes the only harness parity check at skills/implement/scripts/test-oos-disposition-gate.sh:219-225 without substituting a design_oos↔gate check; regex drift could change /design prepare skip-all-security vs current awk-backed behavior.
- **Proposed resolution**: Have _count_non_security_blocks delegate to file_oos._count_non_security_markdown(text) (preserve the existing empty-input early return if desired), delete only the awk subprocess call, and limit new tests to one prepare-flow skip-all-security integration case instead of re-copying the full counter fixture set.

### FINDING_7:
- **Reviewer(s)**: Cursor-dyn-Oos Counter Parity
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:12-24 / python/design_oos.py:28-34 (proposed)
- **Concern**: [SCOPE-REDUCTION] Plan mandates a third inline regex counter in design_oos instead of reusing file_oos._count_non_security_markdown. Scenario: A fresh port duplicates logic already hardened in python/file_oos.py:48-106 with coverage in python/test_file_oos.py:16-126 (backtick/bold focus-area, unbulleted fields, legacy FINDING tags, Description prose exclusion). Repo history already saw awk/Python counter drift on these surfaces; a new copy raises skip-all-security vs implement disposition-gate mismatch risk on identical markdown
- **Proposed resolution**: Change ### UPDATED: python/design_oos.py to implement _count_non_security_blocks as return file_oos._count_non_security_markdown(text) (one import); drop the new local regex/helpers bullet; keep only the skip-all-security prepare-flow test plus optional one-line delegation smoke test ## Findings ### 1. architecture — `[SCOPE-REDUCTION]` inline regex duplicate (`plan.txt:12-24`, proposed `python/design_oos.py:28-34`) The plan tells the implementer to add new local regexes in `design_oos.py` while forbidding a shared abstraction. That still adds a third counter beside `python/file_oos.py:84-106` (implement disposition gate) and `python/oos_disposition.py:47-68` (audit scan). `file_oos._count_non_security_markdown(text)` already matches the retired awk contract the plan lists: legacy tagged `### FINDING_N:` only with `[OUT_OF_SCOPE]`/`[OOS]`, header `[security]`/`<security>` exclusion, backtick/bold stripping before focus-area match, unbulleted `focus-area = security`, and no Description-prose false positives (`python/test_file_oos.py:84-101`; gate fixture `skills/implement/scripts/test-oos-disposition-gate.sh:316-332`). **Suggested revision:** delegate `_count_non_security_blocks` to `file_oos._count_non_security_markdown(text)`. Keep the planned `skip-all-security` prepare assertion; drop the large duplicated unit-test matrix unless you keep an inline port. ## Verified (no finding) - **Orphan awk deletion is safe:** `oos-accumulated-seq-seed.awk` and `oos-has-legacy-finding-block-opener.awk` have no `.sh`/`.py` callers; only stale prose in `skills/implement/SKILL.md:830`. `review_tally._seed_oos_seq` (`python/review_tally.py:258-273`) is already pure Python with the accumulated-seq semantics. - **Active awk removal is in scope:** only `python/design_oos.py:81-89` still shells out; the gate wrapper is already Python (`skills/implement/scripts/oos-disposition-gate.sh:8`). - **Semantics the plan must preserve are documented:** awk source `skills/implement/scripts/oos-non-security-block-count.awk:12-30`; plan edge cases and proposed tests cover the review emphasis (Description prose, backtick/bold focus-area, legacy FINDING gating).
