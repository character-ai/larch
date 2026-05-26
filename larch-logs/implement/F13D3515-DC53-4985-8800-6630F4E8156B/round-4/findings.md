### FINDING_1: code-quality: scripts/implement-bootstrap.sh:648-674
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] main() only skips phase 3/4 stubs on bail or STALL_TRACKING, not DEFERRED --up-to-phase plan|all after POSTED=false sets DEFERRED=true then phase_plan_materialize overwrites with not-yet-implemented-phase-3 Skip stub bail when DEFERRED=true or add B4-plan/B4-all harness guards
- **Suggested revision**: Address the concern above.

### FINDING_2: code-quality: scripts/implement-bootstrap.sh:648-674
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Repeated identical if-guard for later phases Future guard changes may be applied incompletely Extract tracking_allows_later_phases helper
- **Suggested revision**: Address the concern above.

### FINDING_3: code-quality: scripts/implement-bootstrap.sh:449
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Silent success when tracking has no issue and no sentinel Unexpected empty BRANCH_SELECTED/ISSUE_NUMBER tail if a caller omits --issue-number Document in implement-bootstrap.md or fail usage
- **Suggested revision**: Address the concern above.

### FINDING_4: code-quality: skills/implement/scripts/test-implement-bootstrap.sh:395-441
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Duplicated repo-unavailable session-setup stubs Harness edits must be made in two places Extract write_repo_unavailable_session_setup helper
- **Suggested revision**: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] code-quality: scripts/write-session-env.sh
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] [[ bashisms predate this branch Unrelated to phase_tracking tracking adoption No change required for this PR
- **Suggested revision**: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] correctness: scripts/implement-bootstrap.md
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 1. **correctness** `skills/implement/scripts/test-implement-bootstrap.sh` — No harness case drives `get-issue-state.sh` to return a non-`OPEN`/non-`CLOSED` `STATE` (e.g. unexpected enum) to assert the `STEP_FAILED=get-issue-state` exit-2 path documented in [`scripts/implement-bootstrap.md`](scripts/implement-bootstrap.md) and SKILL.md. **Why out of scope:** the production branch at `implement-bootstrap.sh:469-471` matches the plan; this is a test-completeness gap, not a demonstrated runtime defect in the shipped script.
- **Suggested revision**: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] architecture
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 2. **architecture** `scripts/lint-foreground-markers.sh` — `implement-bootstrap.sh` is not on the Family B denylist yet; SKILL already marks the call foreground. **Why out of scope:** plan lists denylist enrollment as conditional on lint policy, not part of this phase’s required behavior.
- **Suggested revision**: Address the concern above.

### FINDING_8: risk-integration: skills/implement/scripts/test-post-tracking-issue.sh:41-63
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] post-tracking-issue.sh gained --run-id and new RUN_ID precedence but its harness was not updated A regression in --run-id validation or precedence could ship while make test-post-tracking-issue and make lint still pass Extend test-post-tracking-issue.sh with override invalid-flag and fallback-chain cases per post-tracking-issue.md
- **Suggested revision**: Address the concern above.

### FINDING_9: risk-integration: skills/implement/scripts/test-implement-bootstrap.sh:337-352
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] GP-adopt always passes --run-id so session-id to RUN_ID derivation is untested on the happy path Bootstrap could break default RUN_ID derivation for runs without a pre-set RUN_ID while GP-adopt still passes Add GP-adopt-session-id without --run-id asserting RUN_ID from session-id file
- **Suggested revision**: Address the concern above.

### FINDING_10: risk-integration: skills/implement/scripts/test-implement-bootstrap.sh:488-504
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] B4 does not assert rename is skipped when POSTED=false A rename regression on the deferred path could still exit 0 with DEFERRED=true Assert tracking-issue-write.sh rename was not invoked in B4
- **Suggested revision**: Address the concern above.

### FINDING_11: risk-integration: skills/implement/scripts/test-implement-bootstrap.sh:94-249
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Bootstrap stubs post-tracking-issue.sh so real script changes are not exercised in test-implement-bootstrap Real post-tracking-issue.sh --run-id bugs would only surface in live /implement not in the main bootstrap harness Add or extend test-post-tracking-issue.sh for the real script
- **Suggested revision**: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] risk-integration: docs/linting.md:238
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] make test-implement-bootstrap docs still describe calls 1-5 only Maintainers may under-run or mis-scope harness expectations Update the linting.md table row to calls 1-9 and the expanded case list
- **Suggested revision**: Address the concern above.

### FINDING_13: **Argv hardening** in `scripts/implement-bootstrap.sh`: `--issue-number` (digits only), `--run-id` (`^[A-Za-z0-9._-]+$`), `--upstream-repo` (`OWNER/REPO` charset), `--forked-target` (`true|false` only).
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Argv hardening** in `scripts/implement-bootstrap.sh`: `--issue-number` (digits only), `--run-id` (`^[A-Za-z0-9._-]+$`), `--upstream-repo` (`OWNER/REPO` charset), `--forked-target` (`true|false` only).
- **Suggested revision**: Address the concern above.

### FINDING_14: **Sentinel fail-closed resume** (Branch 1): requires `valid_issue_number` / `valid_run_id`, `ADOPTED=true`, and argv `--issue-number` before resume; mismatch/malformed sentinel is removed and falls through to Branch 2.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Sentinel fail-closed resume** (Branch 1): requires `valid_issue_number` / `valid_run_id`, `ADOPTED=true`, and argv `--issue-number` before resume; mismatch/malformed sentinel is removed and falls through to Branch 2.
- **Suggested revision**: Address the concern above.

### FINDING_15: **Shell/GitHub boundaries**: issue/repo/run-id values are passed quoted to `get-issue-state.sh`, `get-issue-context.sh`, `larch-log.sh`, `tracking-issue-write.sh`, and `post-tracking-issue.sh`; no `eval` or unquoted expansion on untrusted fields.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Shell/GitHub boundaries**: issue/repo/run-id values are passed quoted to `get-issue-state.sh`, `get-issue-context.sh`, `larch-log.sh`, `tracking-issue-write.sh`, and `post-tracking-issue.sh`; no `eval` or unquoted expansion on untrusted fields.
- **Suggested revision**: Address the concern above.

### FINDING_16: **Fork upstream failure** (round 3): non-zero `get-issue-context.sh` is recorded via `append-tool-failure.sh` with `--redact` on `upstream-context.log`, instead of leaving raw `gh` stderr only in a tmp log.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Fork upstream failure** (round 3): non-zero `get-issue-context.sh` is recorded via `append-tool-failure.sh` with `--redact` on `upstream-context.log`, instead of leaving raw `gh` stderr only in a tmp log.
- **Suggested revision**: Address the concern above.

### FINDING_17: **`post-tracking-issue.sh`**: `--run-id` validated before marker/sentinel write; sentinel written only after successful `POSTED=true`.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **`post-tracking-issue.sh`**: `--run-id` validated before marker/sentinel write; sentinel written only after successful `POSTED=true`.
- **Suggested revision**: Address the concern above.

### FINDING_18: **`write-session-env.sh`**: `FORKED_TARGET` restricted to `true|false` before writing `session-env.sh`.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **`write-session-env.sh`**: `FORKED_TARGET` restricted to `true|false` before writing `session-env.sh`. No new secret literals, command-injection sinks, or path-traversal escapes were identified on the modified code paths. ---
- **Suggested revision**: Address the concern above.

### FINDING_19: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 1. **security** `scripts/write-session-env.sh:155-157` — `REPO=` is still written without the same charset/length validation applied to `--token-session-id` and path args. That predates this branch; `phase_infra` continues to forward session-setup’s `REPO` unchanged. **Suggested fix:** (separate change) add `OWNER/REPO` validation mirroring `implement-bootstrap.sh` / `get-issue-context.sh`.
- **Suggested revision**: Address the concern above.

### FINDING_20: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 2. **risk-integration** `scripts/get-issue-context.sh:60-63` — upstream issue title/body land in `upstream-issue-*.txt` without the data-not-instructions envelope used by `tracking-issue-read.sh` for GitHub content. Fork-mode fetch is now centralized in `phase_tracking` but uses the same helper semantics as before (F4 best-effort binding). **Suggested fix:** wrap upstream files at write time or document mandatory sanitization before any model reads them.
- **Suggested revision**: Address the concern above.

### FINDING_21: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 3. **security** `scripts/implement-bootstrap.sh:248-250` — `--caller-env` is forwarded/read without path confinement (Phase 1 surface). Not introduced here. **Suggested fix:** require absolute paths under an allowlisted session-cache prefix before `read-session-env-key.sh`. --- **Summary:** Phase 2/4 tracking adoption is security-sound for the stated trust model (session tmpdir from `session-setup.sh`, validated argv, quoted subprocess args). Prior review rounds already closed the main gaps (sentinel numeric/`RUN_ID` validation, resume `--issue-number` requirement, fork `--upstream-repo` + `--issue-number` coupling, redacted fork-context failures). No blocking or important security regressions remain in the diff.
- **Suggested revision**: Address the concern above.

### FINDING_22: architecture: scripts/implement-bootstrap.sh:648-674
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] main() runs phase_plan_materialize/coder stubs when DEFERRED=true because guards only check IMPLEMENT_BAIL_REASON and STALL_TRACKING --up-to-phase plan|all after POSTED=false (DEFERRED=true) overwrites empty bail with not-yet-implemented-phase-3 Skip stubs when DEFERRED=true until Phase 3 is real; add B4-plan harness case
- **Suggested revision**: Address the concern above.

### FINDING_23: risk-integration: scripts/implement-bootstrap.sh:493-499
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Branch 2 post failure clears sentinel and leaves branch-2-adopt without parent-issue.md Re-bootstrap in same tmpdir re-runs full Branch 2 instead of resume; duplicate post attempts possible Document; optional metadata-only retry when DEFERRED and branch-2-adopt
- **Suggested revision**: Address the concern above.

### FINDING_24: architecture: scripts/implement-bootstrap.sh:380-412
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] DEFERRED=true used for metadata defer fork skip and repo-unavailable skip KV-only readers may misinterpret fork/repo skip as metadata failure Disambiguate in docs or add a separate skip flag in a later phase
- **Suggested revision**: Address the concern above.

### FINDING_25: [OUT_OF_SCOPE] architecture: skills/implement/scripts/step2-implement.md:62-63
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] session-env presence alone marks issue-anchored without parent-issue ISSUE_NUMBER Deferred post failure leaves no sentinel; step2 anchoring still follows session-env file Pre-existing; not introduced by this branch
- **Suggested revision**: Address the concern above.

### FINDING_26: `fc4d783b` Implement phase tracking bootstrap adoption
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - `fc4d783b` Implement phase tracking bootstrap adoption
- **Suggested revision**: Address the concern above.

### FINDING_27: `6d635cd2` chore(larch-logs): flush (out of scope per review rules)
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - `6d635cd2` chore(larch-logs): flush (out of scope per review rules)
- **Suggested revision**: Address the concern above.

### FINDING_28: `438ab338` / `5a435db1` / `b0d211a5` Address code review feedback (rounds 1–3)
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - `438ab338` / `5a435db1` / `b0d211a5` Address code review feedback (rounds 1–3) Walked the implementation plan requirement-by-requirement against the diff and current sources. Core deliverables are present and match the voted dialectic bindings. ### Traceability summary | Plan requirement | Status | |------------------|--------| | Full `phase_tracking` state machine (carve-outs, Branch 1 fail-closed, Branch 2 adopt) | Implemented in `scripts/implement-bootstrap.sh` | | New argv: `--forked-target`, `--upstream-repo`, `--run-id`, `--issue-number` | Parsed/validated in `main()` | | DECISION_1: `POSTED!=true` → `DEFERRED=true`, exit 0, no sentinel/rename | Implemented; B4 harness | | DECISION_2: `get-issue-state` failure → `STEP_FAILED=get-issue-state`, exit 2 | Implemented; B6 harness | | `emit_final_tail` branch-aware `ISSUE_NUMBER`, explicit booleans | Implemented | | F7: skip Phase 3/4 stubs on bail / `STALL_TRACKING` | Implemented; B2-plan, B5-all/plan guards | | F6: `write-session-env.sh` `--forked-target` + `FORKED_TARGET=` | Implemented | | F5: `post-tracking-issue.sh` `--run-id` + sentinel `RUN_ID` | Implemented | | F20: `tracking-issue-read.md` documents `RUN_ID=` | Updated | | F3: single SKILL `implement-bootstrap.sh --up-to-phase tracking` | Collapsed; no duplicate infra call in SKILL | | F4: fork hard-bail → best-effort upstream context | Old abort prose removed; bootstrap + SKILL table | | F26: drop uuidgen fallback prose | Removed from SKILL | | Harness: GP/B cases + stubs | 13+ planned cases; extras (rename-fail, empty-run-id, B7, etc.) exceed minimum | | Contract doc `implement-bootstrap.md` | argv, KV keys, bail table, behavior mapping updated | NO_ISSUES_FOUND.
- **Suggested revision**: Address the concern above.

