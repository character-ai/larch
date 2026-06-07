### FINDING_1: Auto-fix prompt can leak raw validator logs when redaction fails
- **Reviewer(s)**: codex-specialist-security-output.txt, codex-specialist-correctness-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `auto-fix-plan-commands.sh` falls back to including the raw validator log in the external Codex/Cursor prompt if `redact-secrets.sh` fails, which can expose sensitive validator output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-security-output.txt, codex-specialist-correctness-output.txt, codex-specialist-testing-output.txt: Address the concern above.

### FINDING_2: Auto-fix accepts plan files outside the intended session target
- **Reviewer(s)**: codex-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `auto-fix-plan-commands.sh` accepts any existing `PLAN_FILE` instead of requiring a non-symlink, session-local plan target under `DESIGN_TMPDIR`, so a bad caller binding or symlink could let an external agent read/edit outside the intended plan file.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-security-output.txt: Address the concern above.

### FINDING_3: Stale Gate B prose can force explicit prompts despite default auto-apply
- **Reviewer(s)**: codex-specialist-security-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt, dyn-design-flow-output.txt, dyn-docs-contract-output.txt
- **Severity**: important
- **Concern**: `skills/design/references/approval-gates.md` and `skills/design/SKILL.md` still contain normative Step 3/Gate B wording that says complete review outcomes use the full explicit prompt or that Gate B is always explicit. That contradicts the new `approve_requested=false` default auto-apply path and can cause orchestrators to halt for the old Apply all / Go through each / Switch prompt on default runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-security-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt, dyn-design-flow-output.txt, dyn-docs-contract-output.txt: Address the concern above.

### FINDING_4: Auto-fix handler ignores nonzero helper exits or unknown status
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, dyn-agent-dispatch-output.txt
- **Severity**: important
- **Concern**: The shared validator auto-fix handler captures `_autofix_rc` but only branches on `AUTOFIX_STATUS`, leaving missing/unknown status or helper exit failures without a deterministic warning and fallback path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, dyn-agent-dispatch-output.txt: Address the concern above.

### FINDING_5: Auto-fix revalidation can use a different repo root than initial validation
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-design-flow-output.txt, dyn-agent-dispatch-output.txt
- **Severity**: important
- **Concern**: `auto-fix-plan-commands.sh` derives `--repo-root` from the plan file/session tmpdir during revalidation, while the initial validator path uses a different root. This can produce false success, repeated validator failures, or inconsistent Tier 3 command resolution.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, dyn-design-flow-output.txt, dyn-agent-dispatch-output.txt: Address the concern above.

### FINDING_6: Revert failure can silently proceed with the degraded plan
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: If the operator chooses Revert after a WORSE assessor verdict, a failed or partially failed `revert-round` path can fall through to Continue semantics and proceed with the worsened/applied plan instead of failing closed or re-prompting.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_7: Revert does not reconcile accepted findings and review artifacts
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-design-flow-output.txt, dyn-state-persistence-output.txt
- **Severity**: important
- **Concern**: Successful Revert restores `plan.txt` and some counters but leaves accepted findings, tallies, OOS/rejected artifacts, and assessor verdict files intact, so Gate C or run logs can reflect accepted/applied edits no longer present in the reverted plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, dyn-design-flow-output.txt, dyn-state-persistence-output.txt: Address the concern above.

### FINDING_8: Single-vendor auto-fix attempts are duplicated without real alternation
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: When only one vendor is available, the auto-fix loop can run two identical attempts rather than true cross-vendor alternation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_9: SECURITY.md assessor boundary omits the new Revert branch
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-docs-contract-output.txt
- **Severity**: nit
- **Concern**: `SECURITY.md` still describes Step 3.6 assessor control as Continue/Stop only, omitting the new Revert option and rollback trust boundary.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, dyn-docs-contract-output.txt: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] Broader validator default repo-root ambiguity
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-agent-dispatch-output.txt
- **Severity**: nit
- **Concern**: `validate-plan.sh`’s default `REPO_ROOT` behavior is broader than the auto-fix change and may affect all plan-command validation, not only the new revalidation path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, dyn-agent-dispatch-output.txt: Address the concern above.

### FINDING_11: Auto-fix success warning can lose original validator evidence
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Auto-fix revalidation overwrites the validator log before the success warning is recorded, so the warning can contain the final passing log instead of the original defect evidence/count.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_12: Ruff target remains py312 after advertised Python floor moves to 3.11
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `python/ruff.toml` still targets `py312`, so 3.12-only syntax may be less consistently flagged despite the project promising Python 3.11 support.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_13: Plan-required integration regression coverage is incomplete
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The plan-required regression tests for default auto-apply, `--approve`, Revert, size brakes under auto-apply, and validator auto-fix are mostly missing beyond prose pins and helper-level tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_14: Structure harness lacks pins for key auto-fix and Revert orchestration text
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `scripts/test-design-structure.sh` does not pin the auto-fix helper invocation, Step 3.6 revert fence, or Continue/Revert/Stop WORSE prompt strings, so core orchestration text could regress while structure tests pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_15: [OUT_OF_SCOPE] Assessor/Revert handoff coverage is missing
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-design-flow-output.txt, dyn-state-persistence-output.txt
- **Severity**: latent
- **Concern**: Revert is covered at helper level, but the Step 3.6 WORSE → Revert orchestration handoff is not tested end-to-end for plan rollback and cursor/count state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, dyn-design-flow-output.txt, dyn-state-persistence-output.txt: Address the concern above.

### FINDING_16: Cursor auto-fix timing kind is registered but not emitted
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `cursor-plan-autofix` exists in timing kinds but the Cursor dispatch path in `auto-fix-plan-commands.sh` does not emit it, undercounting Component D work.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_17: Auto-fix tests do not cover shared-handler warning and prompt behavior
- **Reviewer(s)**: cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `test-auto-fix-plan-commands.sh` focuses on helper status, not the shared handler’s mandatory warning logging or prompt suppression/escalation behavior after ok/exhausted/unavailable outcomes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt: Address the concern above.

### FINDING_18: [OUT_OF_SCOPE] Structure-test comment still references always-explicit Gate B
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-docs-contract-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-design-structure.sh` retains a stale comment about always-explicit Gate B.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, dyn-docs-contract-output.txt: Address the concern above.

### FINDING_19: Public command signatures omit `--approve`
- **Reviewer(s)**: codex-specialist-testing-output.txt, dyn-docs-contract-output.txt
- **Severity**: nit
- **Concern**: README/docs command synopses omit the new `[--approve]` flag even though surrounding prose describes it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing-output.txt, dyn-docs-contract-output.txt: Address the concern above.

### FINDING_20: Auto-fix vendors run in the session tmpdir instead of the consumer repo
- **Reviewer(s)**: dyn-design-flow-output.txt
- **Severity**: latent
- **Concern**: Codex/Cursor auto-fix agents are launched with the design tmpdir as workdir/workspace, so plans referencing repo scripts, Makefile targets, or paths outside the tmpdir may be unfixable even for syntactic defects.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-design-flow-output.txt: Address the concern above.

### FINDING_21: [OUT_OF_SCOPE] Gate B header still says “explicit operator apply point”
- **Reviewer(s)**: dyn-design-flow-output.txt, dyn-docs-contract-output.txt
- **Severity**: nit
- **Concern**: `approval-gates.md` line 61 still describes Gate B as “the explicit operator apply point,” which conflicts with default auto-apply wording elsewhere.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-design-flow-output.txt, dyn-docs-contract-output.txt: Address the concern above.

### FINDING_22: [OUT_OF_SCOPE] Gate C timing prose omits default auto-apply path
- **Reviewer(s)**: dyn-design-flow-output.txt
- **Severity**: nit
- **Concern**: Gate C “When” prose lists explicit-apply paths but does not mention default auto-apply.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-design-flow-output.txt: Address the concern above.

### FINDING_23: Auto-fix orchestration has no durable cycle cap
- **Reviewer(s)**: dyn-agent-dispatch-output.txt
- **Severity**: important
- **Concern**: After `AUTOFIX_STATUS=ok`, the handler can re-enter postplan/publish validation and dispatch auto-fix again with no per-site durable attempt budget, risking repeated external calls if validation still fails.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-agent-dispatch-output.txt: Address the concern above.

### FINDING_24: Auto-fix failures and validator stderr lack durable telemetry
- **Reviewer(s)**: dyn-agent-dispatch-output.txt, dyn-bash-portability-output.txt
- **Severity**: latent
- **Concern**: Vendor dispatch failures are only emitted transiently, validator stderr is swallowed during revalidation, and exhausted/error states may lack durable execution-issue or warning evidence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-agent-dispatch-output.txt, dyn-bash-portability-output.txt: Address the concern above.

### FINDING_25: [OUT_OF_SCOPE] Auto-fix offline coverage excludes live launcher/root/cycle behavior
- **Reviewer(s)**: dyn-agent-dispatch-output.txt
- **Severity**: latent
- **Concern**: Offline auto-fix tests do not cover live Codex/Cursor launcher exit parsing, repo-root parity with caller sites, or orchestrator cycle limits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-agent-dispatch-output.txt: Address the concern above.

### FINDING_26: Revert fence may lose the durable assessor round anchor
- **Reviewer(s)**: dyn-state-persistence-output.txt
- **Severity**: important
- **Concern**: The Revert fence calls `revert-round --round "$ASSESSOR_ROUND_NUM"` even though that variable is not persisted/exported into the fresh Bash subshell, so Revert can exit 2 and fall through despite the operator choosing Revert.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-state-persistence-output.txt: Address the concern above.

### FINDING_27: Router flag recovery harness omits `approve_requested` merge coverage
- **Reviewer(s)**: dyn-state-persistence-output.txt
- **Severity**: latent
- **Concern**: `test-step0b-router-flag-recovery.sh` mirrors only `partition_requested` and `brainstorm_requested`, so it cannot catch regressions preserving stored `approve_requested=true`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-state-persistence-output.txt: Address the concern above.

### FINDING_28: [OUT_OF_SCOPE] Run-params re-init can overwrite stored router flags
- **Reviewer(s)**: dyn-state-persistence-output.txt
- **Severity**: latent
- **Concern**: The broader run-params merge behavior can overwrite stored true router flags on re-init when argv flags are false; this predates `--approve` but now also affects it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-state-persistence-output.txt: Address the concern above.

### FINDING_29: Auto-fix timeout argument lacks numeric validation
- **Reviewer(s)**: dyn-bash-portability-output.txt
- **Severity**: latent
- **Concern**: `auto-fix-plan-commands.sh` validates `--max-attempts` but forwards raw `--timeout` values without the numeric/positive guard used by peer dispatch scripts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-portability-output.txt: Address the concern above.

### FINDING_30: Duplicate `--approve` is silently accepted
- **Reviewer(s)**: dyn-bash-portability-output.txt
- **Severity**: nit
- **Concern**: `parse-design-argv.sh` accepts duplicate `--approve` tokens, unlike `--hard`, which fails closed on duplicates.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-portability-output.txt: Address the concern above.

### FINDING_31: [OUT_OF_SCOPE] Python floor change belongs to another commit
- **Reviewer(s)**: dyn-bash-portability-output.txt
- **Severity**: nit
- **Concern**: `scripts/implement-bootstrap.sh` lowers the Python ship-driver floor from 3.12 to 3.11, but that belongs to another branch commit and is unrelated to the `/design` auto-apply work.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-portability-output.txt: Address the concern above.

### FINDING_32: [OUT_OF_SCOPE] Direct rollback write pattern is inherited
- **Reviewer(s)**: dyn-bash-portability-output.txt
- **Severity**: nit
- **Concern**: `snapshot-plan-round.sh` writes `review-round-count.txt` via direct redirect, but this matches a pre-existing rollback pattern rather than a new regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-portability-output.txt: Address the concern above.

### FINDING_33: [OUT_OF_SCOPE] Bash 3.2 portability check passed
- **Reviewer(s)**: dyn-bash-portability-output.txt
- **Severity**: nit
- **Concern**: The reviewed shell surface introduced no Bash 4+ constructs and `make lint-bash32` passed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-portability-output.txt: Address the concern above.

### FINDING_34: Installation docs still say SIMPLE applies findings only by explicit Gate B choices
- **Reviewer(s)**: dyn-docs-contract-output.txt
- **Severity**: nit
- **Concern**: `docs/installation-and-setup.md` still describes SIMPLE-tier accepted findings as applied only through explicit Gate B choices, contradicting default auto-apply.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-docs-contract-output.txt: Address the concern above.

### FINDING_35: SECURITY.md plan review boundary still requires explicit Gate B choice
- **Reviewer(s)**: dyn-docs-contract-output.txt
- **Severity**: important
- **Concern**: `SECURITY.md` says accepted findings touch `plan.txt` only after an explicit Gate B operator choice, which is false for default `/design` auto-apply.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-docs-contract-output.txt: Address the concern above.

### FINDING_36: Accepted-finding template still encodes explicit operator approval
- **Reviewer(s)**: dyn-docs-contract-output.txt
- **Severity**: latent
- **Concern**: `skills/design/references/plan-review.md` still says accepted findings are surfaced for application after explicit operator approval, so generated tally output can preserve the old UX wording.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-docs-contract-output.txt: Address the concern above.

### FINDING_37: parse-design-argv docs still say successful output has seven KVs
- **Reviewer(s)**: dyn-docs-contract-output.txt
- **Severity**: nit
- **Concern**: `parse-design-argv.md` exit-code docs say exit 0 yields seven KVs, but the parser now emits eight including `APPROVE_REQUESTED`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-docs-contract-output.txt: Address the concern above.

### FINDING_38: [OUT_OF_SCOPE] Linting docs have harness-catalog drift
- **Reviewer(s)**: dyn-docs-contract-output.txt
- **Severity**: nit
- **Concern**: `docs/linting.md` does not reflect `approve_requested` coverage in `test-write-run-params` and lacks a row for the new auto-fix test target.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-docs-contract-output.txt: Address the concern above.

### FINDING_39: [OUT_OF_SCOPE] SECURITY.md Tier 3 validator section omits auto-fix-first cross-reference
- **Reviewer(s)**: dyn-docs-contract-output.txt
- **Severity**: nit
- **Concern**: `SECURITY.md` Tier 3 validator prose still mentions only operator Override logging and does not cross-reference the new auto-fix-first path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-docs-contract-output.txt: Address the concern above.

### FINDING_40: [OUT_OF_SCOPE] Workflow docs omit SIMPLE auto-apply and size-brake nuance
- **Reviewer(s)**: dyn-docs-contract-output.txt
- **Severity**: nit
- **Concern**: `docs/workflow-lifecycle.md` and `docs/skills.md` mention HARD assessor Continue/Revert/Stop but do not explain SIMPLE auto-apply/no-assessor behavior or size-brake prompts under auto-apply.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-docs-contract-output.txt: Address the concern above.
