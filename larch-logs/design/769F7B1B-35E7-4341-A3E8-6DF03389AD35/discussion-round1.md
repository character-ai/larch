## Decision 1: Blocker scope for add-blocked-by
- **Question**: Port both add-blocked-by.sh variants into one Python function or leave for F3c?
- **Resolution**: Absorb both `skills/issue/scripts/add-blocked-by.sh` and `skills/block-issue/scripts/add-blocked-by.sh` into a single Python function with full retry/idempotency semantics. F3c's "blocker-helpers" covers prose-parsing, not the write API.
- **Source**: user

## Decision 2: Harness scope
- **Question**: Which bash harnesses become pytest? Only the three named in the issue body, or all?
- **Resolution**: All Makefile-wired bash harnesses for absorbed scripts become pytest: test-parse-input, test-allocate-candidates, test-add-blocked-by, test-list-issues, test-sentinel-write, test-cleanup, test-upgrade-larch-retention, test-setup-forked-open-source-repo, plus the structural harnesses test-body-file-title, test-intra-batch-deps, test-blocked-by-issue that are wired into the same Makefile targets.
- **Source**: codebase (Makefile target scan; DoD says "pytest replaces harness coverage")

## Decision 3: lib-larch-dev-clone.sh and lib-sparse-dirs.sh scope
- **Question**: These are in scripts/ (not skills/upgrade-larch/scripts/); are they in scope?
- **Resolution**: Yes. The issue explicitly lists both under "Absorbs". They are sourced only by upgrade-larch.sh and release-step7-root.sh, so their logic folds into the Python upgrade module.
- **Source**: codebase (scripts/ scan; issue body)

## Decision 4: test-redact-secrets.sh references create-one.sh
- **Question**: scripts/test-redact-secrets.sh directly invokes create-one.sh. Must it be updated?
- **Resolution**: Yes. After create-one.sh is retired, test-redact-secrets.sh must be updated to test redact-secrets.sh integration via the new Python CLI verb (or stub the gh call path directly). This is a call-site cutover required by the DoD.
- **Source**: codebase (scripts/test-redact-secrets.sh scan)
