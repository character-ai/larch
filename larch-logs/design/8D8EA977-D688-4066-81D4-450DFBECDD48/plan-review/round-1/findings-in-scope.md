Merged the 16 reviewer slots into nine findings by behavioral risk (waterfall source, Python lint roots, tier rotation, `gh` retries, stdlib AST, redaction wiring, streaming PEM, pyright/Node in tests, ship-pr CI job names). Verbatim suggested revisions are preserved per slot unless wording was literally identical.

### FINDING_1: CI-fix waterfall attributed to wrong script (review dispatcher vs ship-pr)
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic
- **Severity**: important
- **Concern**: The plan names `scripts/dispatch-with-waterfall.sh` as the CI-fix waterfall source for `agents.py`, but that script is the review dispatcher. The actual CI-fix waterfall (tier loop, `run_ci_fix_vendor`, `first-fixer-non-health`, rollback, launcher failure class handling, local verification, staging/push, conflict recovery, etc.) lives in `scripts/ship-pr.sh` (e.g. ~1994–2128, recovery ~2690–2765). Porting or testing against the wrong contract risks baking review-dispatch semantics into the Python foundation while missing ship-pr CI-fix behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch, Codex-Arch: Revise the agents.py plan to use scripts/ship-pr.sh run_ci_fix_vendor as the CI-fix waterfall source. Remove scripts/dispatch-with-waterfall.sh from this phase unless review dispatch is intentionally in scope.
  - From Cursor-Innovation, Codex-Innovation: Keep Phase 1 agents.py scoped to launcher failure classification and the actual ship-pr CI-fix/recovery tier semantics, or defer waterfall modeling until the ship-pr migration phase
  - From Cursor-Pragmatic: Retarget agents.py waterfall spec/tests to ship-pr.sh run_ci_fix_vendor; drop dispatch-with-waterfall.sh as a parity source unless explicitly scoping a later phase
  - From Codex-Pragmatic: Retarget the Phase 1 parity surface to `run_ci_fix_vendor` and `run_recovery_waterfall`, or narrow `agents.py` now to launcher argv/classification primitives and leave waterfall porting to the phase that touches `ship-pr.sh`.

### FINDING_2: Python lint/CI commands not bound to `python/` configs and tree
- **Reviewer(s)**: Cursor-Edge, Codex-Edge, Cursor-Innovation, Codex-Innovation, Cursor-Requirements, Codex-Requirements, Cursor-dyn-ci-toolchain, Codex-dyn-ci-toolchain
- **Severity**: important
- **Concern**: Planned CI/Makefile recipes run bare `ruff check`, `pylint`, and `pyright` (and related tooling) from the repo root while configs live under `python/`. Ruff/pyright may not pick up child configs from root; bare `pylint` can exit with no targets; jobs may scan unrelated repo Python or fail without exercising the intended tree—so the Python Lint acceptance gate may not validate the proposed modules.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge, Codex-Edge: Run the lint job from working-directory: python, or pass explicit config/project/targets: ruff check python --config python/ruff.toml, pylint python/*.py --rcfile=python/.pylintrc, pyright -p python/pyrightconfig.json. Mirror the same explicit commands in make py-lint.
  - From Cursor-Innovation, Codex-Innovation: Run tool-specific commands against the new tree and config, e.g. ruff check --config python/ruff.toml python, pylint --rcfile=python/.pylintrc python, pyright -p python/pyrightconfig.json
  - From Cursor-Requirements, Codex-Requirements: Spell out exact commands in both CI and make py-lint, for example ruff check --config python/ruff.toml python, pylint --rcfile=python/.pylintrc python/*.py, and pyright -p python/pyrightconfig.json.
  - From Cursor-dyn-ci-toolchain: One contract everywhere: cd python && ruff check . && pylint … && pyright && pytest (single-line recipes per Makefile convention), or equivalent explicit flags (-c python/pyproject.toml, pyright --project python, pylint --rcfile=python/.pylintrc, ruff check python/ with paths scoped to python/). Mirror the subdirectory cd pattern at Makefile:1039-1042
  - From Codex-dyn-ci-toolchain: Pick one execution root. Either set CI working-directory: python and make py-lint/py-test cd python with config-relative paths like include "."; or keep repo root and pass explicit --config/--rcfile/--project arguments with paths that are correct relative to each config file.

### FINDING_3: Agents waterfall drops rotated first-tier / first-fixer-non-health contract
- **Reviewer(s)**: Cursor-Edge, Codex-Edge
- **Severity**: latent
- **Concern**: The plan pins a fixed `cursor,codex,claude` order and tests against that order, but ship-pr’s CI-fix path rotates the starting tier via `start_attempt % 3` and applies `first-fixer-non-health` relative to the rotated first tier. A fixed first tier can let repeated outer attempts keep short-circuiting on the same Cursor non-health failure without giving Codex or Claude the first-fixer slot.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge, Codex-Edge: Add a start_attempt/offset input to the agents waterfall, rotate the base tier tuple per invocation, and test that first-fixer-non-health applies to the rotated first tier.

### FINDING_4: Generic `gh` retry must not wrap non-idempotent mutating calls
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Concern**: The plan retry-wraps every `gh` call, including mutating operations. Existing issue-create paths avoid retry because create is not idempotent after server-side success with a lost response. A transient after a successful `gh pr create`, `gh issue comment`, `gh pr merge`, or `gh run rerun` can be retried and create duplicate side effects or turn a successful write into a confusing failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Limit generic retry to idempotent read/list/view operations. Give each mutating operation an explicit policy: no retry, or operation-specific recovery such as existing-PR lookup after PR-create conflict.

### FINDING_5: Stdlib-only check may miss nested imports
- **Reviewer(s)**: Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Concern**: Planned stdlib-only enforcement only checks top-level imports. A runtime module could add a function-local `import` of `requests`, `pytest`, or another non-stdlib package and still pass the AST check, violating the runtime dependency acceptance rule.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements, Codex-Requirements: Walk every ast.Import and ast.ImportFrom node in each runtime module, not only top-level statements, while still allowing stdlib and sibling python/ modules.

### FINDING_6: Outbound redaction not wired into `gh` bodies and logging
- **Reviewer(s)**: Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Concern**: The feature requires outbound `gh` bodies and logs to pass through `python/redact.py`, but the plan only creates `redact.py` and leaves `gh` issue edit/comment plus JSONL/breadcrumb text silent on redaction—allowing future issue comments or journals to leak secrets or operator paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements, Codex-Requirements: Add an explicit contract that free-text gh body/comment fields and logging_util message/detail fields are passed through redact.redact before subprocess or journal output, with focused tests covering a token and tmpdir path.

### FINDING_7: Python redactor lacks stateful streaming PEM parity with shell
- **Reviewer(s)**: Cursor-dyn-redaction-parity, Codex-dyn-redaction-parity
- **Severity**: important
- **Concern**: The proposed Python redactor only specifies `redact(text: str)`, but the current contract includes stateful streaming PEM redaction used by operator diagnostics and breadcrumb publication. A PEM private key split across logging calls can lose persisted `in_pem` state; future Python `logging_util` output could surface key body lines that the shell path currently swallows.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-redaction-parity, Codex-dyn-redaction-parity: Add a minimal stateful streaming primitive and parity tests for complete/split/fresh-END PEM cases, or narrow the plan so this phase does not claim to replace the streaming side and logging_util cannot publish unredacted user-visible text.

### FINDING_8: Python Tests job may install pyright without Node handling
- **Reviewer(s)**: Codex-dyn-ci-toolchain
- **Severity**: important
- **Concern**: `requirements-dev` includes pyright and Python Tests installs that file, but only Python Lint adds `setup-node` under the plan’s assumption that pyright’s pip package needs Node. The test job can fail during dependency install before pytest runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-ci-toolchain: Minimum-change fix: do not install the lint stack in Python Tests. Use a pytest-only pinned test requirements file or install the pinned pytest version there. If one shared requirements-dev.txt is retained, mirror setup-node in Python Tests and document that it exists only because pyright is in the shared file.

### FINDING_9: New Python CI jobs vs ship-pr failed-job recognition (strangler boundary)
- **Reviewer(s)**: Cursor-dyn-migration-boundary, Codex-dyn-migration-boundary
- **Severity**: important
- **Concern**: The plan adds pull_request/push Python CI jobs while claiming zero live `/implement` impact, but `ship-pr` consumes failed CI job names and only recognizes the current job set. A failing Python Lint/Python Tests job becomes observable to `/implement` CI handling; display names with spaces or ids like `python-lint`/`python-tests` may be malformed or unknown, so ship-pr classifies the failure unfixable and exits via `ci-local-unfixable`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-migration-boundary, Codex-dyn-migration-boundary: To preserve the strangler boundary, defer PR/push Python CI to the cutover phase or make it manual/non-required for now. If these jobs must be blocking now, update ci-failed-jobs.sh, ship-pr.sh per-job argv, docs, and harnesses, and remove the no-.sh/zero-live-impact claim.
