# Review Round 1

- Mode: `diff`
- 4 accepted, 1 rejected (1 neutral)

## Accepted Findings

### FINDING_10: `fetch_url()` does not handle malformed URL ports
- **Reviewer(s)**: codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `python/research.py` `fetch_url()` reads `parsed.port` without handling `ValueError` for malformed URL ports. A malformed citation like `https://example.com:bad/` can send `validate_citations()` to the broad unexpected-error sidecar path and drop valid citation rows.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing-output.txt: Catch ValueError around URL parsing and port access, return a per-claim invalid-url result, and add a mixed malformed-plus-valid citation regression in python/test_research.py.


### FINDING_5: Pre-draft pause inside drafter fence is not a terminal halt in SKILL routing
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-step2b-router-output.txt, dyn-pause-contract-output.txt
- **Severity**: important
- **Concern**: Step 2b routing documents pause via postplan `POSTPLAN_RC=11` after `DRAFTER_STATUS=succeeded`, but pre-draft pause at `design-step2b-drafter.sh:111` still `exec`s `design-pause-save.sh` without wrapper delimiter rows or `POSTPLAN_*` output. The fence can return exit 0 with only `PAUSE_OK=true`. Nothing in the routing block clearly halts Step 2b on that outcome before inline drafting, POSTPLAN parsing, or the incomplete-postplan fail-safe, so an orchestrator can incorrectly continue after a successful pause.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Add explicit PAUSE_OK=true / pause-save-complete branch before POSTPLAN parsing and fail-safe; treat as terminal pause, not missing postplan.
  - From dyn-step2b-router-output.txt: Add an explicit post-drafter-fence branch: when output contains `PAUSE_OK=true` and there is no `DRAFTER_STATUS=fallback` / dirty-tree env / wrapper delimiter success path, stop `/design` for resume and do not run inline drafting, postplan parsing, or fail-safe recovery.
  - From dyn-pause-contract-output.txt: Either emit the same `POSTPLAN_RC=11` / `POSTPLAN_STATUS=pause-save` rows at `design-step2b-drafter.sh:111` before `exec`, or add explicit `SKILL.md` prose to halt on `PAUSE_OK=true` (or equivalent) when the drafter fence pauses before launch and must not continue to inline drafting or fail-safe postplan.


### FINDING_8: Completion-only pause arms lack POSTPLAN_RC=11 contract assertions in pause-resume harness
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-pause-contract-output.txt
- **Severity**: important
- **Concern**: New `POSTPLAN_RC=11` / `POSTPLAN_STATUS=pause-save` rows on completion-only pause branches in `design-step2b-postplan.sh` are not guarded by `test-design-pause-resume.sh`, which still asserts only `PAUSE_OK=true`. Removing the new printf lines from `--write-step2b-completion-only` or `--write-completion-only` pause arms could pass pause-resume tests and break orchestrator routing that expects rc 11 on every pause-save path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Extend test-design-pause-resume.sh completion-only pause loop (lines 1455-1483) or add a case to test-design-step2b-drafter.sh asserting whole-line POSTPLAN_RC=11 and POSTPLAN_STATUS=pause-save for each completion-only mode
  - From dyn-pause-contract-output.txt: Extend the completion-only and normal postplan pause loops in `test-design-pause-resume.sh` to require whole-line `POSTPLAN_RC=11` and `POSTPLAN_STATUS=pause-save` before `PAUSE_OK=true`.


### FINDING_9: Retired-script lint prefilter skips non-.sh/.md manifest paths
- **Reviewer(s)**: codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `python/migration_lint.py` now skips every line that lacks `.sh` or `.md` even though the manifest contains retired `.py`, `.awk`, `.jq`, `.json`, and `.inc.bash` paths. A new reference to `python/ci_cli.py` or `skills/design/scripts/parse-plan-commands.awk` would no longer be reported by `make lint-retired-scripts`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing-output.txt: Remove the .sh/.md prefilter and gate only on actual retired basenames; add a non-.sh retired-path regression in python/test_migration_lint.py.


