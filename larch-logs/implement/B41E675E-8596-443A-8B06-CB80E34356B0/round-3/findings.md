### FINDING_1: [OUT_OF_SCOPE] Document run-external-agent stderr-only progress contract
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `run-external-agent.sh` now routes default-mode progress, timeout, completion, and diagnostic chatter to stderr so callers can redirect wrapper stdout to JSONL event files safely. The sibling `run-external-agent.md` contract does not document that stream split, which can mislead callers and allow future stdout regressions that corrupt `*.events.jsonl`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_2: Triplicated Codex JSONL telemetry dispatch logic
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `scripts/lint-fix-loop.sh`, `skills/review-and-fix/scripts/review-and-fix.sh`, and `scripts/run-negotiation-round.sh` duplicate the Codex JSONL telemetry dispatch block, so future argv, cleanup, or exit-code changes can drift across sites.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_3: Breadcrumb round-entry test accepts missing breadcrumb
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `skills/review-and-fix/scripts/test-review-and-fix.sh` allows the round-entry breadcrumb assertion to pass when the breadcrumb is absent, so quiet/breadcrumb routing regressions can stop being caught by CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_4: Duplicated flag validation in get-issue-state
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `scripts/get-issue-state.sh` duplicates `--issue` and `--repo` value guard logic with inconsistent `emit_kv` formatting, creating drift risk for future error-envelope changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_5: round_artifact_included test probes function body indirectly
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-larch-log.sh` uses `awk` plus `eval` against a function body to test `round_artifact_included`, which can silently break if the implementation is refactored.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_6: Redundant serial lock assignment in review-and-fix
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `skills/review-and-fix/scripts/review-and-fix.sh` assigns `_SERIAL_LOCK=""` redundantly before acquiring the Codex lock, adding minor noise to the dispatch flow.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] run-negotiation-round path resolution differs under symlinks
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `scripts/run-negotiation-round.sh` computes `SCRIPT_DIR` without `pwd -P` while `PLUGIN_ROOT` uses `pwd -P`, so symlinked script paths can resolve the script directory and plugin root differently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] Document telemetry sidecar exclusion explicitly
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `scripts/larch-log.md` relies on the generic `*.sidecar` exclusion rather than explicitly mentioning `*.telemetry.sidecar`, so operators may not understand why parse spill files are absent from committed logs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] Empty --issue value reports less specific error
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: `scripts/get-issue-state.sh` reports `ERROR=--issue is required` for `--issue ""` instead of `ERROR=--issue requires a value`; behavior remains safe, but message consistency differs from the new guard paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_10: Compose-fail harness leaks inherited breadcrumb stream
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `skills/review-and-fix/scripts/test-review-and-fix.sh` uses `LARCH_QUIET_DISABLE=1` without clearing inherited `LARCH_BREADCRUMB_STREAM`, causing the compose-fail test to fail when run inside an `/implement` session with stream env set.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_11: Flush-warning coverage no longer asserts user-visible channel
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The flush-warning stdout breadcrumb assertion was replaced by a stub stderr assertion, so warning coverage can stay green if warnings move back to breadcrumb-only channels and stop appearing where users or execution issue tracking expect them.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_12: run-external-agent stderr routing lacks regression test
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `scripts/test-run-external-agent.sh` does not assert that wrapper diagnostics stay on stderr, so a future change could put diagnostics back on stdout and reintroduce JSONL bleed into `codex.events.jsonl`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_13: Codex argv forwarding tests are weaker outside negotiation
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The lint-fix and review-and-fix harnesses do not log and assert forwarded `--json`, `--output-last-message`, and `--` argv the way the negotiation test does, so dropped production flags could slip through if stubs only enforce flags internally.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_14: [OUT_OF_SCOPE] Raw scout manifests remain allowlisted
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: `scripts/larch-log.sh` still allowlists `scout-round*-manifest.json.raw`, which can contain full dynamic-archetype `prompt_body` text. The reviewer marked this as pre-existing and not introduced by the branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_15: [OUT_OF_SCOPE] Negotiation sidecar reuse could become sensitive if exclusions broaden
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `scripts/run-negotiation-round.sh` reuses one `${OUTPUT_FILE%.txt}.sidecar` for Codex stderr and telemetry parse append. This is safe while `*.sidecar` remains excluded, but a future allowlist broadening would make the pre-existing pattern higher impact.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_16: Empty or unparsable Codex events skip token-ledger row
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `scripts/lib-external-launcher-common.sh` skips token-ledger recording when `events.jsonl` is empty or unparsable, even on failed Codex runs. Operators may mistake a missing `codex_*` ledger row for missing telemetry rather than an early crash or parse failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_17: Telemetry sidecar filenames drift from plan literals
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: `scripts/lint-fix-loop.sh` and `skills/review-and-fix/scripts/review-and-fix.sh` use `codex.telemetry.sidecar` and `coder-codex.telemetry.sidecar` rather than the plan’s `codex.sidecar` and `coder-codex.sidecar`, so operators or tooling following the plan may not find parse-diagnostic files.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_18: Pre-run cleanup omits legacy Codex log files
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: `scripts/lint-fix-loop.sh` and `skills/review-and-fix/scripts/review-and-fix.sh` do not remove legacy `codex.log` / `coder-codex.log` files before dispatch, so repeated runs could briefly expose stale final-message output from `--output-last-message`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
