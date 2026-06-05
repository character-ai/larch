### FINDING_1: [OUT_OF_SCOPE] Unrelated #3506 PR-metrics work is bundled with the #3514 gate fix
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash32-output.txt, dyn-kv-streams-output.txt
- **Severity**: important
- **Concern**: The branch mixes the degraded-tools gate fix with unrelated PR line-count/final-report changes, increasing review and rollback coupling between independent workstreams.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash32-output.txt, dyn-kv-streams-output.txt: Address the concern above.

### FINDING_2: Implement gate plugin-root rehydration uses a weaker non-canonical fallback
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, dyn-bash32-output.txt
- **Severity**: important
- **Concern**: The `/implement` degraded-tools gate prelude uses an `if`/`elif` plugin-root recovery pattern that can skip the session-env fallback when `plugin-root.env` exists but does not set a usable `CLAUDE_PLUGIN_ROOT`, causing helper invocations to fail or use a bad path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, dyn-bash32-output.txt: Address the concern above.

### FINDING_3: Shared degraded-tools documentation/example can drift from durable rehydration requirements
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `skills/shared/external-reviewers.md` documents the separate-block rehydration rule and `PRESENCE_INPUT_EMPTY` symptom, but the example/pins may still allow maintainers to copy or regress guidance that reintroduces empty presence inputs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_4: `write-final-report.sh` duplicates KV parsing with weaker `awk -F=` behavior
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `read_lines_kv` duplicates an existing KV parser and can misparse values containing `=`, increasing maintenance risk in the bundled PR-metrics work.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_5: `degraded-tools-gate.sh` header omits conditional `PRESENCE_INPUT_EMPTY`
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-kv-streams-output.txt
- **Severity**: latent
- **Concern**: The script header’s stdout contract omits the newly emitted conditional `PRESENCE_INPUT_EMPTY=true` KV, creating drift from the markdown contract and from consumers expected to parse the signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, dyn-kv-streams-output.txt: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] Design gate lacks durable `CLAUDE_PLUGIN_ROOT` fallback/preservation
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The `/design` gate relies on `source-env.sh` containing `CLAUDE_PLUGIN_ROOT`; if that env file is partial, corrupt, or refreshed without the root, the separate Bash block can fail before degraded-tools logic runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] PR metrics helper lacks repo and numeric PR validation
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, dyn-pr-metrics-output.txt
- **Severity**: latent
- **Concern**: `compute-pr-line-counts.sh` interpolates `REPO` and `PR_NUMBER` into a `gh api` path without peer-style validation, so poisoned or malformed session state can produce unintended or opaque GitHub API calls instead of a clean skipped/unavailable result.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, dyn-pr-metrics-output.txt: Address the concern above.

### FINDING_8: `PRESENCE_INPUT_EMPTY` warning breadcrumbs are not structurally pinned
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `/implement` and `/design` prose requires logging warnings when `PRESENCE_INPUT_EMPTY=true`, but structure tests do not pin the warning/execution-issues handling, so future edits could silently remove the operator-visible signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_9: Design env partial-override test does not assert binary-found key preservation
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `test-write-design-current-env.sh` case 14 does not verify `CODEX_BINARY_FOUND` and `CURSOR_BINARY_FOUND` survive partial override recovery, leaving resume-path gate rehydration regressions untested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_10: `PRESENCE_INPUT_EMPTY` stdout order is not tested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: No degraded-tools gate test asserts that `BOTH_DOWN` precedes `PRESENCE_INPUT_EMPTY`, so consumers depending on the documented KV order could break without CI catching it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_11: Design gate bootstrap/test pins omit the durable current-design symlink path
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash32-output.txt
- **Severity**: latent
- **Concern**: The `/design` gate and structure tests center on `$DESIGN_TMPDIR/source-env.sh` and do not fully accept or bootstrap from `current-design-env-$PPID.sh`, so a fresh Bash block can abort before reading durable env, or a valid symlink-based implementation can fail structure tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash32-output.txt: Address the concern above.

### FINDING_12: Missing unreadable `session-env.sh` is converted into explicit false values
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The `/implement` gate reads presence keys with `--default false`, so a missing or unreadable `session-env.sh` can look like four legitimate `false` inputs, suppress `PRESENCE_INPUT_EMPTY`, and trigger a misleading degraded-tools prompt instead of a loud infrastructure error.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_13: Empty-presence bug path can still fall through to normal BOTH_DOWN prompting
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `PRESENCE_INPUT_EMPTY=true` is only treated as a warning signal; callers that pass empty presence flags may still run the normal BOTH_DOWN interactive prompt, preserving the original blocking behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_14: Shared `PRESENCE_INPUT_EMPTY` contract is not reconciled across review/research
- **Reviewer(s)**: dyn-kv-streams-output.txt
- **Severity**: latent
- **Concern**: The shared degraded-tools contract now describes `PRESENCE_INPUT_EMPTY` handling, but `/review` and `/research` gate paragraphs were left unchanged, creating ambiguity about whether those skills must log the same rehydration warning.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-kv-streams-output.txt: Address the concern above.

### FINDING_15: [OUT_OF_SCOPE] Design false defaults suppress the new empty-input diagnostic
- **Reviewer(s)**: dyn-kv-streams-output.txt
- **Severity**: latent
- **Concern**: The `/design` path converts missing or empty sourced keys to explicit `false`, so `PRESENCE_INPUT_EMPTY` will not fire there, trading away the diagnostic signal on that caller path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-kv-streams-output.txt: Address the concern above.

### FINDING_16: PR line-count failures are rendered as `N/A` without execution-issues breadcrumbs
- **Reviewer(s)**: dyn-pr-metrics-output.txt
- **Severity**: latent
- **Concern**: `write-final-report.sh` collapses helper failures, missing helpers, malformed KV, auth outages, and no-PR cases into `Lines (PR diff): N/A` without recording a warning, weakening post-run diagnosis.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-pr-metrics-output.txt: Address the concern above.

### FINDING_17: `compute-pr-line-counts.sh` discards GitHub API stderr
- **Reviewer(s)**: dyn-pr-metrics-output.txt
- **Severity**: latent
- **Concern**: When `gh api` fails, stderr is redirected to `/dev/null`, so operators cannot distinguish auth, rate-limit, 404, or network failures behind `LINES_STATUS=unavailable` / `REASON=gh-failed`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-pr-metrics-output.txt: Address the concern above.

### FINDING_18: [OUT_OF_SCOPE] PR line-count pagination is not asserted by tests
- **Reviewer(s)**: dyn-pr-metrics-output.txt
- **Severity**: latent
- **Concern**: The offline `gh` shim tests only a single-page response and does not assert `gh api --paginate`, so pagination regressions for very large PRs could escape CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-pr-metrics-output.txt: Address the concern above.

### FINDING_19: [OUT_OF_SCOPE] Final-report fallback parity for happy PR metrics is untested
- **Reviewer(s)**: dyn-pr-metrics-output.txt
- **Severity**: latent
- **Concern**: The degraded-renderer fallback is tested only on a no-PR fixture, leaving the happy path where `LINES_DATA_OK=true` and fallback rendering must emit bucketed line counts unproven.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-pr-metrics-output.txt: Address the concern above.
