### FINDING_1: [OUT_OF_SCOPE] Branch bundles unrelated ship-driver, design, and aggregation changes
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-scope-anchor-output.txt
- **Severity**: important
- **Concern**: The branch/PR mixes the Python ship-driver default flip with large unrelated design scope-anchor and aggregate-findings changes, making review, bisection, rollback, and default-path regression isolation difficult.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-scope-anchor-output.txt: Address the concern above.

### FINDING_2: Terminal stall/finalize metadata has competing writers
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `python/ship.py` can write terminal stall/finalize disk state from in-run helpers and again from `_persist_stall_metadata_if_needed`, allowing partial or divergent terminal metadata in `ship-pr-state.sh` / `finalize-state.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_3: Step 8+ Python-vs-bash routing prose is too fragile
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `skills/implement/SKILL.md` describes Python default routing and bash opt-in in a dense mixed paragraph with repeated qualifiers, increasing the chance of orchestrator misrouting and doc drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_4: Ship state KV parsing and merge logic is duplicated
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Ship state KV files are parsed and merged through multiple code paths, so preserve/merge behavior can diverge between readers and writers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_5: Success path writes `phase=done` twice
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, dyn-scope-anchor-output.txt
- **Severity**: important
- **Concern**: `run_postmerge_phase` already writes terminal success state, but the merge loop writes `phase=done` again without the same terminal context, risking drift between `ship-pr-state.sh` and `finalize-state.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From dyn-scope-anchor-output.txt: Address the concern above.

### FINDING_6: Python test gating requires a `python3.12` binary instead of the Step 8+ `python3 >= 3.12` contract
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, dyn-runtime-versioning-output.txt
- **Severity**: latent
- **Concern**: `make py-test` / `relevant-checks.sh` can fail or skip tests on hosts where `python3` is 3.12+ but no `python3.12` executable exists, diverging from the production Step 8+ guard.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From dyn-runtime-versioning-output.txt: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] Optional structure pins for stall-recovery/conflict-resolution Python qualifiers are missing
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Optional grep/awk pins for Python qualifiers in `stall-recovery.md` and `conflict-resolution.md` were not added, so those reference docs can drift without failing the structure harness.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] Report-tokens still advertises or enforces Python 3.11 after the shared Python floor moved to 3.12
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-runtime-versioning-output.txt
- **Severity**: latent
- **Concern**: `/report-tokens` docs and wrapper checks still mention Python 3.11 while the shared `python/` package and ship driver now require Python 3.12+, creating inconsistent operator prerequisites.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From dyn-runtime-versioning-output.txt: Address the concern above.

### FINDING_9: PrePushConflictHandoff writes handoff keys without stall metadata
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-state-machine-output.txt
- **Severity**: important
- **Concern**: On pre-push conflict handoff, `python/ship.py` writes resume/conflict keys but leaves or rewrites disk state as `STALL_TRACKING=false` and skips finalize metadata, so Step 18/classification can miss a real stalled handoff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-state-machine-output.txt: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] Python default flip ships before documented soak/parity blockers close
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-state-machine-output.txt, dyn-prompt-contracts-output.txt, dyn-scope-anchor-output.txt, dyn-finding-aggregation-output.txt, dyn-runtime-versioning-output.txt
- **Severity**: important
- **Concern**: The default Step 8+ path moves to `python/ship.py` while documented parity gaps remain open; some reviewers treat this as release/product risk rather than a code defect, but operators may still hit less-soaked conflict, CI, and finalize paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-state-machine-output.txt: Address the concern above.
  - From dyn-prompt-contracts-output.txt: Address the concern above.
  - From dyn-scope-anchor-output.txt: Address the concern above.
  - From dyn-finding-aggregation-output.txt: Address the concern above.
  - From dyn-runtime-versioning-output.txt: Address the concern above.

### FINDING_11: [OUT_OF_SCOPE] Exit-matrix prose still permits bash-style state parsing on Python returns
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-prompt-contracts-output.txt
- **Severity**: latent
- **Concern**: The exit-matrix section mixes a bash-only `ship-pr-state.sh` parsing gate with per-exit bullets that also apply to Python, allowing orchestrators to either skip the bullets or route Python exit 0 through stale/missing `PHASE` values.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-prompt-contracts-output.txt: Address the concern above.

### FINDING_12: Structure test version-guard probe uses an inconsistent Python stub
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The runtime probe test uses a 3.11 stub against a 3.12 floor, making the harness fail on 3.12+ CI or pass without testing the intended below-floor path on 3.11 machines.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_13: Checks-phase stall test does not assert terminal finalize state
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Tests for checks-phase stalls can pass even if terminal `finalize-state.sh` stops being written with `STALL_TRACKING=true` and `EXIT_CODE=4`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_14: Planned anti-halt / NEVER structure pins are absent
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Structure tests do not pin planned anti-halt and NEVER #11 default-Python routing language, so prompt regressions to bash-default or unqualified state parsing may not fail CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_15: Step 18 conditional restore behavior lacks executable coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The stale-finalize versus skip-restore branches in Step 18 are pinned only by prose/substrings, leaving `_restore_finalize` branch behavior without fixture-level tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_16: [OUT_OF_SCOPE] Python 3.11 removal from CI matrix needs release-note clarity
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-runtime-versioning-output.txt
- **Severity**: nit
- **Concern**: CI’s move to Python 3.12-only is consistent with the runtime flip, but operators may need explicit release-note/doc clarity that 3.11 coverage/support is gone.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From dyn-runtime-versioning-output.txt: Address the concern above.

### FINDING_17: `finalize-state.sh` writers lack symlink-safe atomic hardening
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-prompt-safety-output.txt
- **Severity**: important
- **Concern**: `finalize-state.sh` is written with plain write/replace patterns while `ship-pr-state.sh` gained symlink and `O_NOFOLLOW` hardening, leaving terminal finalize writes vulnerable to same-UID symlink/TOCTOU redirection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From dyn-prompt-safety-output.txt: Address the concern above.

### FINDING_18: `merge_replace_state_keys` can rewrite a symlinked `ship-pr-state.sh`
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `write-final-report.sh` rewrites `ship-pr-state.sh` without rejecting symlinks or non-regular files, so Step 18 report generation could write through a swapped symlink.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_19: State overlay accepts unvalidated PR URL and branch name from disk
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `_context_with_state_overlay` applies `PR_URL` and `BRANCH_NAME` from seeded disk state without existing validators, allowing poisoned state to influence terminal stall writes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_20: Stall-recovery classifier evidence reads lack symlink/size validation
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `stall-recovery-report.sh classify` still concatenates `session-env.sh` and `ship-pr-state.sh` into evidence without the hardened optional-state-file validation used elsewhere.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_21: Exit 6 fourth-transient stall persistence is prompt-only
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-state-machine-output.txt
- **Severity**: important
- **Concern**: Python returns `Outcome.TRANSIENT` without mechanically persisting stall keys on the fourth transient failure; if the orchestrator misses the prompt-side rewrite, disk/JSON routing diverges.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-state-machine-output.txt: Address the concern above.

### FINDING_22: `ship-pr-state.sh.tmp` can permanently block state writes after a crash
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `_write_ship_state` uses an exclusive fixed temp path but does not recover from an orphaned stale temp file, so a crash can block subsequent state writes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_23: Routine state writes can erase seeded stall metadata
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-state-machine-output.txt
- **Severity**: latent
- **Concern**: `RunContext.from_env` hydrates some fields from state but not `STALL_TRACKING` / `STALL_STEP`; the first healthy `_write_ship_state` can clear pre-seeded stall metadata before terminal resolution.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-state-machine-output.txt: Address the concern above.

### FINDING_24: Corrupt state-file reads map to internal error instead of a stall path
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Corrupt or unreadable `ship-pr-state.sh` maps to `INTERNAL_ERROR`/exit 1 rather than a bash-like stalled exit 4, which may bypass operator repair and teardown expectations.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_25: [OUT_OF_SCOPE] Phantom probe registry still names `ship-pr.sh` instead of the active Step 8+ driver
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt, dyn-prompt-contracts-output.txt
- **Severity**: important
- **Concern**: The phantom untracked probe registry still describes running before `ship-pr.sh` first invocation, so default-Python orchestrators may treat the probe as bash-only or miss the active-driver handoff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-prompt-contracts-output.txt: Address the concern above.

### FINDING_26: Done-resume fast path can return success without refreshing finalize state
- **Reviewer(s)**: dyn-state-machine-output.txt
- **Severity**: latent
- **Concern**: When `_resume_plan` returns `start=="done"`, `run_ship` can emit success JSON without verifying or recreating `finalize-state.sh`, leaving success JSON and teardown disk state inconsistent after partial writes/crashes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-state-machine-output.txt: Address the concern above.

### FINDING_27: [OUT_OF_SCOPE] Pre-push no-finalize behavior and postmerge/classify positives
- **Reviewer(s)**: dyn-state-machine-output.txt
- **Severity**: nit
- **Concern**: The absence of finalize on `PrePushConflictHandoff` is intentional for immediate conflict-resolution re-entry; postmerge success/stall gating and four-layer classify behavior otherwise appear aligned with the plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-state-machine-output.txt: Address the concern above.

### FINDING_28: Run-log refresh triggers still name bash-only `ship-pr.sh` semantics
- **Reviewer(s)**: dyn-prompt-contracts-output.txt
- **Severity**: latent
- **Concern**: `refresh-run-logs.sh` trigger prose is still framed around `ship-pr.sh` internals and exit parsing, risking missed refreshes or wrong semantics on Python JSON/state-file paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-prompt-contracts-output.txt: Address the concern above.

### FINDING_29: Active-driver completion paragraph still uses bash `PHASE` mechanics
- **Reviewer(s)**: dyn-prompt-contracts-output.txt
- **Severity**: latent
- **Concern**: The Step 8+ completion paragraph describes `ship-pr.sh` phase transitions and `PHASE=done`, while Python completion should route from JSON exit 0 / `outcome=OK`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-prompt-contracts-output.txt: Address the concern above.

### FINDING_30: Branch alignment guard prose names only `ship-pr.sh`
- **Reviewer(s)**: dyn-prompt-contracts-output.txt
- **Severity**: latent
- **Concern**: The post-dispatch branch guard names `scripts/ship-pr.sh` as the canonical backstop, omitting the default Python driver’s branch validation path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-prompt-contracts-output.txt: Address the concern above.

### FINDING_31: State seeding and MANIFEST hard-fail prose remains bash-framed
- **Reviewer(s)**: dyn-prompt-contracts-output.txt
- **Severity**: latent
- **Concern**: Step 8+ state seeding and `MANIFEST` failure text describes `ship-pr.sh` argv-init / bash exit 4 rather than Python’s orchestrator seeding plus `--state-file` merge and JSON failure shapes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-prompt-contracts-output.txt: Address the concern above.

### FINDING_32: Exit 4 `STALL_STEP=6` prose names only bash lint-fix loop
- **Reviewer(s)**: dyn-prompt-contracts-output.txt
- **Severity**: latent
- **Concern**: Exit 4 stall prose describes `ship-pr.sh` attempting the lint-fix loop, which can misclassify or confuse Python checks-phase / pre-push stall recovery.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-prompt-contracts-output.txt: Address the concern above.

### FINDING_33: Conflict-resolution reference says control returns to `ship-pr.sh`
- **Reviewer(s)**: dyn-prompt-contracts-output.txt
- **Severity**: latent
- **Concern**: `conflict-resolution.md` starts by saying conflict resolution returns to `scripts/ship-pr.sh`, contradicting the active-driver selector and risking bash resume invocation on the default Python path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-prompt-contracts-output.txt: Address the concern above.

### FINDING_34: [OUT_OF_SCOPE] Core selector and related prompt updates appear aligned
- **Reviewer(s)**: dyn-prompt-contracts-output.txt, dyn-runtime-versioning-output.txt
- **Severity**: nit
- **Concern**: Several reviewed areas—the core Python selector, anti-halt split, Step 18 restore gate, stall-recovery refs, and bare `python3` production invocation with version guards—appear aligned; remaining issues are narrower wording/config gaps.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-prompt-contracts-output.txt: Address the concern above.
  - From dyn-runtime-versioning-output.txt: Address the concern above.

### FINDING_35: Python selector underdocuments pre-push conflict handoff routing
- **Reviewer(s)**: dyn-scope-anchor-output.txt
- **Severity**: important
- **Concern**: The Python selector collapses exit 4 into generic stall handling and does not surface the required `ship_pr_pre_push` conflict-resolution branch before Step 16/18.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-scope-anchor-output.txt: Address the concern above.

### FINDING_36: Plan-review aggregator does not receive the scope anchor
- **Reviewer(s)**: dyn-scope-anchor-output.txt
- **Severity**: important
- **Concern**: Plan-review scout, panel, revise, and voter prompts receive `plan-review-scope-anchor.txt`, but the aggregator is invoked only with findings and plan text, so merge/dedupe lacks binding issue-scope evidence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-scope-anchor-output.txt: Address the concern above.

### FINDING_37: Scope-reduction dedup can merge tagged findings with untagged findings
- **Reviewer(s)**: dyn-finding-aggregation-output.txt
- **Severity**: important
- **Concern**: Plan-review dedup can merge `[SCOPE-REDUCTION]` findings with in-scope untagged findings, causing a scope-cut finding to absorb and drop distinct in-scope concern text before aggregation/balloting.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-finding-aggregation-output.txt: Address the concern above.

### FINDING_38: Scope-marker normalization differs between marker, dedup, and parity checks
- **Reviewer(s)**: dyn-finding-aggregation-output.txt
- **Severity**: important
- **Concern**: Marker detection accepts plain `- Concern:` and `what:` forms, but dedup/aggregate comparison text only parses bold concern/description lines, breaking withhold/merge/parity behavior for some scope-reduction findings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-finding-aggregation-output.txt: Address the concern above.

### FINDING_39: Scope-reduction parity reads too few reviewer attribution formats
- **Reviewer(s)**: dyn-finding-aggregation-output.txt
- **Severity**: latent
- **Concern**: Plan-mode parity matching only reads bold reviewer lines, while validation accepts more reviewer-line shapes; valid aggregations can roll back when tagged findings use non-bold attribution.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-finding-aggregation-output.txt: Address the concern above.

### FINDING_40: Scope-marker split failure lacks execution-issues warning
- **Reviewer(s)**: dyn-finding-aggregation-output.txt
- **Severity**: latent
- **Concern**: If the plan-mode scope-marker split helper fails, aggregation returns `AGGREGATED=false` without appending the warning breadcrumb used by other failure paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-finding-aggregation-output.txt: Address the concern above.

### FINDING_41: Scope-anchor file renderer lacks local containment/symlink validation
- **Reviewer(s)**: dyn-prompt-safety-output.txt
- **Severity**: important
- **Concern**: `render-voter-prompt.sh --scope-anchor-file` only checks readability before inlining content, unlike callers/renderers that enforce non-symlink and tmpdir containment, creating an information-disclosure boundary gap if miswired or swapped.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-prompt-safety-output.txt: Address the concern above.

### FINDING_42: [OUT_OF_SCOPE] Scope-anchor prompt-safety improvements are positive
- **Reviewer(s)**: dyn-prompt-safety-output.txt
- **Severity**: nit
- **Concern**: Several new scope-anchor prompt paths redact and HTML-escape context, strip embedded plan blocks, and route main-agent adjudication through hardened renderers; a pre-existing scout `--description-text` path remains outside the new hot path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-prompt-safety-output.txt: Address the concern above.

### FINDING_43: Ruff target version still says Python 3.11
- **Reviewer(s)**: dyn-runtime-versioning-output.txt
- **Severity**: latent
- **Concern**: `python/ruff.toml` still targets `py311` even though the runtime floor and pyright config moved to 3.12, so linting may not apply 3.12-aware rules.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-runtime-versioning-output.txt: Address the concern above.

### FINDING_44: Pylint version still says Python 3.11
- **Reviewer(s)**: dyn-runtime-versioning-output.txt
- **Severity**: latent
- **Concern**: `python/.pylintrc` still sets `py-version=3.11`, diverging from the 3.12 production/runtime contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-runtime-versioning-output.txt: Address the concern above.

### FINDING_45: `py-lint` is not pinned to the configured Python interpreter
- **Reviewer(s)**: dyn-runtime-versioning-output.txt
- **Severity**: latent
- **Concern**: `make py-lint` invokes bare `ruff`, `pylint`, and `pyright` from `PATH`, so local lint can run under/tool against an interpreter/toolchain that diverges from Python 3.12 CI and production.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-runtime-versioning-output.txt: Address the concern above.

### FINDING_46: Linting docs are stale for relevant-checks Python behavior
- **Reviewer(s)**: dyn-runtime-versioning-output.txt
- **Severity**: latent
- **Concern**: `docs/linting.md` still says Python tests run only when `pytest` is on `PATH`, but `relevant-checks.sh` now probes for `python3.12 -m pytest`, so operators may misunderstand which checks ran.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-runtime-versioning-output.txt: Address the concern above.
