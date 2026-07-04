### FINDING_1: Preserve CI-grepped focus-area enum line
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation
- **Severity**: important
- **Concern**: Shortening the focus-area walk in `render_plan_review_main()` can break the CI guard that greps `python/larch/rendering/rendering.py` for the exact slash-separated focus-area enumeration, including `security`, on one line. Rewording it into bullets, backticks, or a renamed label risks failing CI even if the TSV allowlist prose still looks correct.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add an edge-case bullet: render_plan_review_main must keep that exact slash-separated focus-area enumeration (including security) on one grep-visible line, or list .github/workflows/ci.yaml as a coordinated update surface
  - From Cursor-Innovation: Add an explicit preserve rule: keep that exact slash-separated enum substring on one line in render_plan_review_main (prefix text may shorten). Add a test_rendering.py assertion or document the ci.yaml dependency in Edge cases.


### FINDING_2: Keep harness-pinned prompt prose in scope
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The testing strategy allows compressing prompt prose that is also pinned by `scripts/test-prompt-template-invariants.sh`. That means an implementer can pass the listed pytest targets while still breaking CI on harness checks for the response-start wording and other exact substrings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add make test-prompt-template-invariants to Testing strategy and note that compressed prose must preserve harness pins or update scripts/test-prompt-template-invariants.sh in the same change
  - From Cursor-Innovation: Add make test-prompt-template-invariants to Testing strategy, or extend the plan invariant list with every harness-pinned substring from test-prompt-template-invariants.sh lines 248-263 and keep them byte-identical during compression.
  - From Cursor-Pragmatic: Keep that opening sentence verbatim (compress only later sentences in the block), or update the harness and add make test-prompt-template-invariants to the Testing strategy alongside the listed pytest targets.


