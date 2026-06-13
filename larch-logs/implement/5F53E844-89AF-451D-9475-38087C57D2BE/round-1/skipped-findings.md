### OOS_3: C1b review modules are bash shims, not planned Python ports
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt, dyn-review-and-fix-handoff-output.txt
- **Severity**: important
- **Concern**: `python/review_pipeline.py`, `python/review_aggregate.py`, `python/review_tally.py`, and `python/compose_review.py` delegate to relocated bash under `python/legacy_review_shell/` via `run_legacy()` instead of providing importable Python implementations. Callers using `python3 python/cli.py review …` or importing tally helpers still execute legacy shell. Plan acceptance requiring deleted bash, direct CLI ownership, and testable Python logic is not met; runtime authority visible to operators (`python/cli.py review …`) diverges from the code that actually runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Implement planned Python stages or rescope; do not treat C1b as complete
  - From codex-specialist-correctness-output.txt: Port the listed shell bodies into the Python modules, keep only approved retained bash subprocess boundaries, and delete the legacy moved C1b shell entrypoints.
  - From codex-specialist-edge-cases-output.txt: Implement the C1b surfaces in Python, or keep the Bash scripts as explicit retained dependencies.
  - From codex-specialist-testing-output.txt: Implement the review pipeline surfaces in Python and delete the absorbed legacy shell runtime copies.
  - From dyn-review-and-fix-handoff-output.txt: Either finish the native port so `review core`/`compose-findings` are real Python implementations, or document and test the legacy delegation as the explicit contract (including a review-and-fix integration test that never stubs `REVIEW_CORE_CMD`).



