# Review Round 2

- Mode: `diff`
- 11 accepted, 11 rejected (10 exonerated)

## Accepted Findings

### FINDING_1: Broad `main()` exception handling hides internal failures
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `python/ship.py` catches broad `Exception` and maps unexpected bugs to `STALLED` JSON/exit 4 with `str(exc)`, losing traceback context, encouraging operational retries, and potentially exposing sensitive exception text.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_10: Scrubbed volatile sidecars can still be committed
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `python/run_logs.py` requires `violations == 0` for volatile-only skip; scrubbed refresh sidecars can set violations and then get committed instead of restored/cleaned, reviving PR-head divergence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_11: Missing regression test for Python 3.11 selector guard
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: No automated test pins the Python 3.11 ship-driver selector/version-probe behavior, so docs may say 3.11 while `/implement` invokes `ship.py` under Python 3.10 until runtime failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_13: Breadcrumb tests do not exercise real `run_ship` phase call sites
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Breadcrumb coverage only exercises `_breadcrumb` via stubbed paths, so removing breadcrumbs from real `run_ship` branches could leave tests green.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_15: Transcript refresh sidecar volatile skip is untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `session-transcript-refresh.txt` is allowlisted for volatile-only skip but lacks a regression test.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_16: PR URL recovery can bind the wrong PR without validation
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-pr-create-resilience-output.txt
- **Severity**: important
- **Concern**: `python/gh.py` parses PR URLs from `gh` output and fabricates a `PullRequest` without confirming repo, branch/head ref, or open state, so misleading output can target the wrong PR.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From dyn-pr-create-resilience-output.txt: Address the concern above.


### FINDING_19: Python breadcrumbs ignore quiet-mode routing
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `python/ship.py` and `python/ci_monitor.py` write breadcrumbs directly to stderr, while bash progress honors quiet FD3 routing, causing stderr spam in quiet `/implement` runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_20: `pr_view_current` fallback is insufficiently corroborated
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-pr-create-resilience-output.txt
- **Severity**: latent
- **Concern**: `python/gh.py` accepts `pr_view_current` fallback results based on matching head ref without enough corroboration, including no explicit `--head` retry and no `OPEN` state requirement.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-pr-create-resilience-output.txt: Address the concern above.


### FINDING_24: Volatile cleanup misclassifies combined `A*` porcelain states
- **Reviewer(s)**: dyn-git-porcelain-cleanup-output.txt
- **Severity**: important
- **Concern**: `_cleanup_volatile_run_tree` uses `"A" in line[:2]` as an index-added proxy; combined states like `AM`, `AU`, and `AD` can be routed incorrectly, leaving tracked modifications after reset/clean and stalling volatile-only cleanup.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-git-porcelain-cleanup-output.txt: Address the concern above.


### FINDING_29: PR success recovery can prefer stderr URL over stdout URL
- **Reviewer(s)**: dyn-pr-create-resilience-output.txt
- **Severity**: important
- **Concern**: `python/gh.py` combines stdout and stderr for post-success URL recovery and selects the last PR URL, so a stderr URL can override the newly created PR URL from stdout.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-pr-create-resilience-output.txt: Address the concern above.


### FINDING_7: Python 3.11 ship-driver guard is prose-only
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: `skills/implement/SKILL.md` documents the Python 3.11 guard in prose but not in the executable Invoke fence, so an orchestrator may skip the version probe on the Python ship path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


