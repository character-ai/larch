### FINDING_1:
- **Reviewer(s)**: Cursor-Arch, Codex-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: <TMPDIR>/plan.txt:89-98
- **Concern**: agents.py names scripts/dispatch-with-waterfall.sh as the CI-fix waterfall source, but that script is the review dispatcher; the CI-fix waterfall lives in scripts/ship-pr.sh:1994-2084.. Scenario: The implementer may port or test the wrong waterfall contract, adding review-dispatch complexity while missing run_ci_fix_vendor behavior such as first-fixer-non-health routing, rollback, launcher class handling, and tier rotation.
- **Proposed resolution**: Revise the agents.py plan to use scripts/ship-pr.sh run_ci_fix_vendor as the CI-fix waterfall source. Remove scripts/dispatch-with-waterfall.sh from this phase unless review dispatch is intentionally in scope.

### FINDING_2:
- **Reviewer(s)**: Cursor-Edge, Codex-Edge
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: plan.txt:134-146
- **Concern**: Python lint commands do not bind to the new python-scoped configs. Scenario: The proposed CI job runs ruff check, pylint, and pyright from repo root while the configs live under python/. Ruff/pyright will not discover child configs from the root, and pylint with no target can fail before checking the new tree. The job can either scan unrelated repo Python files or fail without exercising the intended modules.
- **Proposed resolution**: Run the lint job from working-directory: python, or pass explicit config/project/targets: ruff check python --config python/ruff.toml, pylint python/*.py --rcfile=python/.pylintrc, pyright -p python/pyrightconfig.json. Mirror the same explicit commands in make py-lint.

### FINDING_3:
- **Reviewer(s)**: Cursor-Edge, Codex-Edge
- **Severity**: latent
- **Focus area**: correctness
- **Location**: plan.txt:18-23,89-98
- **Concern**: Agents waterfall drops the current rotated first-tier contract. Scenario: The plan pins a fixed cursor,codex,claude order and tests waterfall behavior against that order, but the existing ship-pr CI-fix path rotates the starting tier by start_attempt % 3 and keys first-fixer-non-health off that rotated first tier. With a fixed first tier, repeated outer attempts can keep short-circuiting on the same Cursor non-health failure and never give Codex or Claude the first-fixer slot.
- **Proposed resolution**: Add a start_attempt/offset input to the agents waterfall, rotate the base tier tuple per invocation, and test that first-fixer-non-health applies to the rotated first tier.

### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation, Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: .github/workflows/ci.yaml:planned Python Lint job; Makefile:planned py-lint target (plan.txt:134-146)
- **Concern**: Planned lint commands are bare ruff check pylint pyright while configs live under python/. Scenario: Bare pylint has no files and exits; ruff/pyright may ignore python-local config or scan unrelated repo Python files, so the new CI gate can fail before testing the proposed tree
- **Proposed resolution**: Run tool-specific commands against the new tree and config, e.g. ruff check --config python/ruff.toml python, pylint --rcfile=python/.pylintrc python, pyright -p python/pyrightconfig.json

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation, Codex-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/agents.py:planned (plan.txt:89-98); scripts/ship-pr.sh:1994-2085; scripts/dispatch-with-waterfall.sh:1-2
- **Concern**: Plan targets dispatch-with-waterfall.sh as the CI-fix waterfall, but that script is the reviewer dispatcher. Scenario: Porting that surface locks review-dispatch concepts into the ship-pr Python foundation while missing ship-pr's actual CI-fix tier loop and first-fixer-non-health behavior
- **Proposed resolution**: Keep Phase 1 agents.py scoped to launcher failure classification and the actual ship-pr CI-fix/recovery tier semantics, or defer waterfall modeling until the ship-pr migration phase

### FINDING_6:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:89-98; scripts/dispatch-with-waterfall.sh; scripts/ship-pr.sh:1994-2086
- **Concern**: agents.py attributes CI-fix waterfall to dispatch-with-waterfall.sh. Scenario: dispatch-with-waterfall.sh is reviewer slot dispatch (jq slots, codex/cursor presence); ship-pr CI fix uses run_ci_fix_vendor with LAUNCHER_FAILURE_CLASS short-circuit, start_attempt%3 tier rotation, wrapper_rc=2 continue, and wrapper_rc=0 gate before other-class bail
- **Proposed resolution**: Retarget agents.py waterfall spec/tests to ship-pr.sh run_ci_fix_vendor; drop dispatch-with-waterfall.sh as a parity source unless explicitly scoping a later phase

### FINDING_7:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/gh.py planned from plan.txt:82-87; skills/issue/scripts/create-one.sh:72-74; scripts/tracking-issue-write.sh:4-6
- **Concern**: The plan retry-wraps every gh call, including mutating operations. Existing issue-create paths explicitly avoid retry because create is not idempotent after server-side success with a lost response.. Scenario: A transient after a successful `gh pr create`, `gh issue comment`, `gh pr merge`, or `gh run rerun` can be retried and create duplicate side effects or convert a successful write into a confusing failure.
- **Proposed resolution**: Limit generic retry to idempotent read/list/view operations. Give each mutating operation an explicit policy: no retry, or operation-specific recovery such as existing-PR lookup after PR-create conflict.

### FINDING_8:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/agents.py planned from plan.txt:89-98; scripts/dispatch-with-waterfall.sh:1-2; scripts/ship-pr.sh:1994-2128; scripts/ship-pr.sh:2690-2765
- **Concern**: The plan says `agents.py` replaces the CI-fix waterfall in `scripts/dispatch-with-waterfall.sh`, but that file is a reviewer dispatcher. The CI-fix waterfall contracts live in `ship-pr.sh`.. Scenario: Porting from the wrong source misses CI-fix behavior such as rollback, `first-fixer-non-health`, no-commit detection, local verification, staging/push, and conflict-recovery verification.
- **Proposed resolution**: Retarget the Phase 1 parity surface to `run_ci_fix_vendor` and `run_recovery_waterfall`, or narrow `agents.py` now to launcher argv/classification primitives and leave waterfall porting to the phase that touches `ship-pr.sh`.

### FINDING_9:
- **Reviewer(s)**: Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: .github/workflows/ci.yaml (planned); Makefile (planned)
- **Concern**: Python lint commands are under-specified for configs stored in python/. Scenario: Bare ruff check, pylint, and pyright from the repo root can ignore python/ruff.toml or python/pyrightconfig.json, scan the wrong tree, or fail with no pylint targets, so the new Python Lint acceptance gate may not go green.
- **Proposed resolution**: Spell out exact commands in both CI and make py-lint, for example ruff check --config python/ruff.toml python, pylint --rcfile=python/.pylintrc python/*.py, and pyright -p python/pyrightconfig.json.

### FINDING_10:
- **Reviewer(s)**: Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/test_stdlib_only.py (planned)
- **Concern**: Stdlib-only enforcement only checks top-level imports. Scenario: A runtime module could add a function-local import of requests, pytest, or another non-stdlib package and still pass the planned AST check, violating the runtime dependency acceptance rule.
- **Proposed resolution**: Walk every ast.Import and ast.ImportFrom node in each runtime module, not only top-level statements, while still allowing stdlib and sibling python/ modules.

### FINDING_11:
- **Reviewer(s)**: Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Focus area**: security
- **Location**: python/gh.py (planned); python/logging_util.py (planned)
- **Concern**: Outbound redaction requirement is not wired into gh bodies or logs. Scenario: The feature requires all outbound gh bodies and logs to pass through python/redact.py, but the plan only creates redact.py and leaves gh issue edit/comment plus JSONL/breadcrumb text silent on redaction, allowing future issue comments or journals to leak secrets or operator paths.
- **Proposed resolution**: Add an explicit contract that free-text gh body/comment fields and logging_util message/detail fields are passed through redact.redact before subprocess or journal output, with focused tests covering a token and tmpdir path.

### FINDING_12:
- **Reviewer(s)**: Cursor-dyn-redaction-parity, Codex-dyn-redaction-parity
- **Severity**: important
- **Focus area**: security
- **Location**: scripts/redact-secrets.sh:49-119; scripts/lib-quiet.sh:98-148; scripts/lib-larch-log.sh:386-394
- **Concern**: The proposed Python redactor only specifies redact(text: str), but the current contract includes stateful streaming PEM redaction used by operator diagnostics and breadcrumb publication.. Scenario: A PEM private key split across logging calls can lose the persisted in_pem state; future Python logging_util output could surface or publish key body lines that the shell path currently swallows.
- **Proposed resolution**: Add a minimal stateful streaming primitive and parity tests for complete/split/fresh-END PEM cases, or narrow the plan so this phase does not claim to replace the streaming side and logging_util cannot publish unredacted user-visible text.

### FINDING_13:
- **Reviewer(s)**: Cursor-dyn-ci-toolchain
- **Severity**: important
- **Focus area**: correctness
- **Location**: .github/workflows/ci.yaml (proposed Python Lint/Python Tests); Makefile (proposed py-lint/py-test)
- **Concern**: Tool commands are not anchored to python/ as the project root. Scenario: CI steps call bare ruff check / pylint / pyright / pytest from the repo root. ruff check with no path defaults to . and can lint the whole repo under default rules, not only python/. pylint and pyright discover config from CWD, so python/.pylintrc and python/pyrightconfig.json are skipped. pytest may not load python/pyproject.toml pythonpath, so flat import config and test_stdlib_only fail despite green-looking wiring
- **Proposed resolution**: One contract everywhere: cd python && ruff check . && pylint … && pyright && pytest (single-line recipes per Makefile convention), or equivalent explicit flags (-c python/pyproject.toml, pyright --project python, pylint --rcfile=python/.pylintrc, ruff check python/ with paths scoped to python/). Mirror the subdirectory cd pattern at Makefile:1039-1042

### FINDING_14:
- **Reviewer(s)**: Codex-dyn-ci-toolchain
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:111-146; .github/workflows/ci.yaml:60-73; Makefile:25-28
- **Concern**: Tool commands and colocated config roots do not line up. Scenario: The plan puts ruff.toml, .pylintrc, pyrightconfig.json, and pyproject.toml under python/ but specifies bare ruff check, pylint, and pyright from the workflow default repo root and Makefile targets. That can scan existing non-python/ scripts, miss python/.pylintrc and python/pyrightconfig.json, and make pyright include python/ from a config inside python/ point at python/python if loaded.
- **Proposed resolution**: Pick one execution root. Either set CI working-directory: python and make py-lint/py-test cd python with config-relative paths like include "."; or keep repo root and pass explicit --config/--rcfile/--project arguments with paths that are correct relative to each config file.

### FINDING_15:
- **Reviewer(s)**: Codex-dyn-ci-toolchain
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: <TMPDIR>/plan.txt:106-141; .github/workflows/ci.yaml:169-198
- **Concern**: Python Tests installs the pyright pin without carrying the plan's Node handling. Scenario: requirements-dev includes pyright, and Python Tests installs that same file, but only Python Lint adds setup-node. Under the plan's stated assumption that pyright's pip package needs Node, the test job can fail during dependency install before pytest. PyPI documents the wrapper's Node/nodeenv behavior at https://pypi.org/project/pyright/.
- **Proposed resolution**: Minimum-change fix: do not install the lint stack in Python Tests. Use a pytest-only pinned test requirements file or install the pinned pytest version there. If one shared requirements-dev.txt is retained, mirror setup-node in Python Tests and document that it exists only because pyright is in the shared file.

### FINDING_16:
- **Reviewer(s)**: Cursor-dyn-migration-boundary, Codex-dyn-migration-boundary
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: .github/workflows/ci.yaml:3-17; scripts/ci-failed-jobs.sh:29-40; scripts/ship-pr.sh:2134-2169,2291-2301
- **Concern**: The plan adds pull_request/push Python CI jobs while claiming zero live /implement impact, but ship-pr consumes failed CI job names and only recognizes the current job set.. Scenario: A failing Python Lint/Python Tests job becomes observable to /implement CI handling; with display names containing spaces it is malformed, and with job ids like python-lint/python-tests it is unknown, so ship-pr classifies it unfixable and exits through the ci-local-unfixable path.
- **Proposed resolution**: To preserve the strangler boundary, defer PR/push Python CI to the cutover phase or make it manual/non-required for now. If these jobs must be blocking now, update ci-failed-jobs.sh, ship-pr.sh per-job argv, docs, and harnesses, and remove the no-.sh/zero-live-impact claim.
