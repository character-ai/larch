# Review Round 1

- Mode: `diff`
- 21 accepted, 6 rejected (5 exonerated)

## Accepted Findings

### FINDING_1: Auto-fix prompt can leak raw validator logs when redaction fails
- **Reviewer(s)**: codex-specialist-security-output.txt, codex-specialist-correctness-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `auto-fix-plan-commands.sh` falls back to including the raw validator log in the external Codex/Cursor prompt if `redact-secrets.sh` fails, which can expose sensitive validator output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-security-output.txt, codex-specialist-correctness-output.txt, codex-specialist-testing-output.txt: Address the concern above.


### FINDING_11: Auto-fix success warning can lose original validator evidence
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Auto-fix revalidation overwrites the validator log before the success warning is recorded, so the warning can contain the final passing log instead of the original defect evidence/count.
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


### FINDING_19: Public command signatures omit `--approve`
- **Reviewer(s)**: codex-specialist-testing-output.txt, dyn-docs-contract-output.txt
- **Severity**: nit
- **Concern**: README/docs command synopses omit the new `[--approve]` flag even though surrounding prose describes it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing-output.txt, dyn-docs-contract-output.txt: Address the concern above.


### FINDING_2: Auto-fix accepts plan files outside the intended session target
- **Reviewer(s)**: codex-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `auto-fix-plan-commands.sh` accepts any existing `PLAN_FILE` instead of requiring a non-symlink, session-local plan target under `DESIGN_TMPDIR`, so a bad caller binding or symlink could let an external agent read/edit outside the intended plan file.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-security-output.txt: Address the concern above.


### FINDING_23: Auto-fix orchestration has no durable cycle cap
- **Reviewer(s)**: dyn-agent-dispatch-output.txt
- **Severity**: important
- **Concern**: After `AUTOFIX_STATUS=ok`, the handler can re-enter postplan/publish validation and dispatch auto-fix again with no per-site durable attempt budget, risking repeated external calls if validation still fails.
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


### FINDING_3: Stale Gate B prose can force explicit prompts despite default auto-apply
- **Reviewer(s)**: codex-specialist-security-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt, dyn-design-flow-output.txt, dyn-docs-contract-output.txt
- **Severity**: important
- **Concern**: `skills/design/references/approval-gates.md` and `skills/design/SKILL.md` still contain normative Step 3/Gate B wording that says complete review outcomes use the full explicit prompt or that Gate B is always explicit. That contradicts the new `approve_requested=false` default auto-apply path and can cause orchestrators to halt for the old Apply all / Go through each / Switch prompt on default runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-security-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt, dyn-design-flow-output.txt, dyn-docs-contract-output.txt: Address the concern above.


### FINDING_30: Duplicate `--approve` is silently accepted
- **Reviewer(s)**: dyn-bash-portability-output.txt
- **Severity**: nit
- **Concern**: `parse-design-argv.sh` accepts duplicate `--approve` tokens, unlike `--hard`, which fails closed on duplicates.
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


### FINDING_7: Revert does not reconcile accepted findings and review artifacts
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-design-flow-output.txt, dyn-state-persistence-output.txt
- **Severity**: important
- **Concern**: Successful Revert restores `plan.txt` and some counters but leaves accepted findings, tallies, OOS/rejected artifacts, and assessor verdict files intact, so Gate C or run logs can reflect accepted/applied edits no longer present in the reverted plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, dyn-design-flow-output.txt, dyn-state-persistence-output.txt: Address the concern above.


### FINDING_9: SECURITY.md assessor boundary omits the new Revert branch
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-docs-contract-output.txt
- **Severity**: nit
- **Concern**: `SECURITY.md` still describes Step 3.6 assessor control as Continue/Stop only, omitting the new Revert option and rollback trust boundary.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, dyn-docs-contract-output.txt: Address the concern above.


