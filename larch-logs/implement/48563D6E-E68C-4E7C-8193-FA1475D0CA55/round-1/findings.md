### FINDING_1: code-quality: scripts/launch-codex-ci.sh:138-152
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Subprocess discipline is a third prose copy (abbreviated) beside base Hard guard #9 and generated codex-implementer.md. Future edits can update the implementer guard and schema token but leave the CI fixer with weaker or stale wording; grep pins only partially overlap (CI uses persistent interactive subprocess without sessions). Extract a shared fragment later, or add a stronger cross-file pin if drift appears in practice.
- **Suggested revision**: Address the concern above.

### FINDING_2: code-quality: scripts/test-launch-codex-ci.sh:83-87
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Rendered-prompt assertion runs only for fix role though PROMPT is shared across all roles. A refactor that moves the paragraph into a role-specific branch could drop it for resolve-conflict/bump-classify while fix-role grep still passes. Mirror the topology.tsv loop with a subprocess grep for non-fix roles, or document fix-only coverage in launch-codex-ci.md.
- **Suggested revision**: Address the concern above.

### FINDING_3: `0216ea34` — Prohibit Codex interactive subprocess sessions (**feature**)
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - `0216ea34` — Prohibit Codex interactive subprocess sessions (**feature**)
- **Suggested revision**: Address the concern above.

### FINDING_4: `1be5f1ff` — chore(larch-logs) implement flush
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - `1be5f1ff` — chore(larch-logs) implement flush
- **Suggested revision**: Address the concern above.

### FINDING_5: `45186750`, `f35b2ff8` — chore(larch-logs) design flushes
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - `45186750`, `f35b2ff8` — chore(larch-logs) design flushes Feature commit touches 14 files (+43 lines). `agents/cursor-implementer.md` is intentionally absent from the diff: adding Hard guard #9 to the base plus the new Cursor generator `sed` deletion reproduces the same Cursor artifact (rules 1–8 only), which matches plan acceptance. ---
- **Suggested revision**: Address the concern above.

### FINDING_6: The Cursor `sed` range `/^9\.\s\*\*NEVER…\*\*/,/^$/d` depends on a blank line after rule #9; that blank line exists today, and `check-generators.sh` (in `test-harnesses-13`) would catch generator drift if spacing regressed.
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - The Cursor `sed` range `/^9\.\s\*\*NEVER…\*\*/,/^$/d` depends on a blank line after rule #9; that blank line exists today, and `check-generators.sh` (in `test-harnesses-13`) would catch generator drift if spacing regressed.
- **Suggested revision**: Address the concern above.

### FINDING_7: The CI subprocess clause lives in the shared `PROMPT` for **all** roles, not only `fix`; the harness only pins `fix` per plan, which is sufficient for the committed layout (paragraph is outside the `LOCAL_REPRO` `if` block).
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - The CI subprocess clause lives in the shared `PROMPT` for **all** roles, not only `fix`; the harness only pins `fix` per plan, which is sufficient for the committed layout (paragraph is outside the `LOCAL_REPRO` `if` block).
- **Suggested revision**: Address the concern above.

### FINDING_8: Prompt-only guidance cannot **guarantee** Codex never calls `write_stdin` again; that is the accepted tradeoff for #2991 (recovery and TTY launcher explicitly out of scope).
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - Prompt-only guidance cannot **guarantee** Codex never calls `write_stdin` again; that is the accepted tradeoff for #2991 (recovery and TTY launcher explicitly out of scope). ---
- **Suggested revision**: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] **Residual runtime risk (requirements, by design)** — Even with Hard guard #9, a Codex implementer can still hit the original `write_stdin failed: stdin is closed` crash if it ignores the prompt; `step2-implement.sh` has no new recovery branch and `launch-codex-implement.sh` is unchanged. #2973’s parent-shell stdin fix is a separate failure class. Operators should not treat this PR as fully closing #2991’s stall mode, only reducing likelihood via prompt discipline.
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 1. **Residual runtime risk (requirements, by design)** — Even with Hard guard #9, a Codex implementer can still hit the original `write_stdin failed: stdin is closed` crash if it ignores the prompt; `step2-implement.sh` has no new recovery branch and `launch-codex-implement.sh` is unchanged. #2973’s parent-shell stdin fix is a separate failure class. Operators should not treat this PR as fully closing #2991’s stall mode, only reducing likelihood via prompt discipline.
- **Suggested revision**: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] **`larch-logs/` bulk** — Large design/implement log commits on the branch are intentional run artifacts per project convention; not reviewed for functional correctness.
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 2. **`larch-logs/` bulk** — Large design/implement log commits on the branch are intentional run artifacts per project convention; not reviewed for functional correctness.
- **Suggested revision**: Address the concern above.

### FINDING_11: risk-integration: agents/_implementer-base.md:36
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Prompt-only guard with no behavioral or Step 2 recovery test. Codex can still call write_stdin on a non-tty exec_command session; implementer dies with uncommitted edits and no manifest while CI grep pins stay green. Track residual risk; consider recovery branch or TTY launcher (#2973) if repeats; optional step2-dispatch golden for bail token if routing added.
- **Suggested revision**: Address the concern above.

### FINDING_12: risk-integration: scripts/test-launch-codex-ci.sh:83-105
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Subprocess prohibition asserted only for fix-role rendered prompt. Refactor gating the clause to fix-only (like topology.tsv) would drop protection on other CI roles without failing this harness. Mirror grep assertion on resolve-conflict bump-classify changelog-draft prompt files or document fix-only intent.
- **Suggested revision**: Address the concern above.

### FINDING_13: [OUT_OF_SCOPE] risk-integration: Makefile:22
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] lint-only path skips check-generators. Contributor runs make lint-only or pre-commit only; edits base or sed strip but not artifacts; drift ships until full test-harnesses-13 in CI. Run bash scripts/check-generators.sh after base or generator edits; consider pre-commit hook (follow-up).
- **Suggested revision**: Address the concern above.

### FINDING_14: [OUT_OF_SCOPE] risk-integration: skills/implement/references/codex-manifest-schema.md:90
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] No automated schema/digest bail-token sync test. Future PR updates schema but not digest (or vice versa); operators see inconsistent token docs. Add paired grep harness if this class of drift recurs (follow-up).
- **Suggested revision**: Address the concern above.

### FINDING_15: **Scope:** `0216ea34` adds Hard guard #9 to `agents/_implementer-base.md` / `agents/codex-implementer.md`, strips it in `scripts/generate-cursor-implementer.sh`, mirrors discipline in `scripts/launch-codex-ci.sh`’s static `PROMPT` paragraph, documents bail token `interactive-subprocess-unsupported`, and pins via grep harnesses. No new network surfaces, credential handling, or shell execution paths in repo scripts.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Scope:** `0216ea34` adds Hard guard #9 to `agents/_implementer-base.md` / `agents/codex-implementer.md`, strips it in `scripts/generate-cursor-implementer.sh`, mirrors discipline in `scripts/launch-codex-ci.sh`’s static `PROMPT` paragraph, documents bail token `interactive-subprocess-unsupported`, and pins via grep harnesses. No new network surfaces, credential handling, or shell execution paths in repo scripts.
- **Suggested revision**: Address the concern above.

### FINDING_16: **Injection / quoting:** The new `launch-codex-ci.sh` text is static and avoids inner `"` in the double-quoted `PROMPT=` assignment (plan FINDING_3). Existing expansion of `$FAILURE_CONTEXT` / `$PLAN_CONTEXT` into `PROMPT` remains a pre-existing prompt-construction pattern; this diff does not widen it.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Injection / quoting:** The new `launch-codex-ci.sh` text is static and avoids inner `"` in the double-quoted `PROMPT=` assignment (plan FINDING_3). Existing expansion of `$FAILURE_CONTEXT` / `$PLAN_CONTEXT` into `PROMPT` remains a pre-existing prompt-construction pattern; this diff does not widen it.
- **Suggested revision**: Address the concern above.

### FINDING_17: **Secrets:** Grep of `larch-logs/implement/48563D6E-E68C-4E7C-8193-FA1475D0CA55` found no credential-shaped literals. Hard guard #9’s heredoc/pipe/`/tmp/input` examples are agent guidance; the required escape hatch is `status=bailed` with `interactive-subprocess-unsupported`, which limits pushing secrets into one-shot command lines when true interactivity is required.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Secrets:** Grep of `larch-logs/implement/48563D6E-E68C-4E7C-8193-FA1475D0CA55` found no credential-shaped literals. Hard guard #9’s heredoc/pipe/`/tmp/input` examples are agent guidance; the required escape hatch is `status=bailed` with `interactive-subprocess-unsupported`, which limits pushing secrets into one-shot command lines when true interactivity is required.
- **Suggested revision**: Address the concern above.

### FINDING_18: **Trust boundaries:** `agents/cursor-implementer.md` correctly omits rule #9 (generator sed strip). Implement run log for this feature contains plan text only (expected for committed run-logs per repo policy).
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Trust boundaries:** `agents/cursor-implementer.md` correctly omits rule #9 (generator sed strip). Implement run log for this feature contains plan text only (expected for committed run-logs per repo policy). This change addresses **availability/integrity** of `/implement` (mid-run Codex death, uncommitted tree) rather than introducing new confidentiality or authz risks. Complementary infra fix for parent-shell stdin (`#2973` / `run-external-agent.sh`) is correctly out of scope here.
- **Suggested revision**: Address the concern above.

### FINDING_19: risk-integration: agents/_implementer-base.md:36
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Hard guard #9 is prompt-only; launchers and step2-implement.sh are unchanged. Codex can still call write_stdin after finishing edits/tests, crash without manifest, and leave breadcrumb-monitor timing out (exit 4) — the #2991 failure mode. Accept for Option 2 scope; consider Step 2.4 recovery or launcher TTY follow-ups if stalls recur; monitor implement logs for compliance.
- **Suggested revision**: Address the concern above.

### FINDING_20: correctness: agents/_implementer-base.md:36
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] bail_reason interactive-subprocess-unsupported is only reachable on proactive bail. Reactive write_stdin failure still kills Codex before manifest write; operators never see the new stable token for the original incident. Add post-crash classification in dispatcher/launcher if observability matters; otherwise document token as proactive-only.
- **Suggested revision**: Address the concern above.

### FINDING_21: correctness: agents/_implementer-base.md:36
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] read_stdout prohibition may be over-broad versus held-child sessions. Codex may bail on legitimate single-shot exec_command+read_stdout patterns not involving write_stdin. Scope read_stdout ban to held/persistent children in base and launch-codex-ci.sh inline prompt.
- **Suggested revision**: Address the concern above.

### FINDING_22: risk-integration: scripts/test-launch-codex-ci.sh:83-87
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Rendered-prompt subprocess assertion runs only for fix role. Future role-gated PROMPT edits could drop the clause for resolve-conflict/bump-classify/changelog-draft without failing CI. Assert persistent interactive subprocess in rendered prompts for all CI roles or add a comment if fix-only is intentional.
- **Suggested revision**: Address the concern above.

### FINDING_23: [OUT_OF_SCOPE] correctness
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: 1. **correctness** `implementation_plan` sed snippet — The plan body’s code block for `generate-cursor-implementer.sh` still shows `sessions\*\*/` without `\.`; only the committed generator and its sibling `.md` have the working pattern. **Suggested fix:** When editing the issue plan block later, align the plan snippet with the shipped `sessions\.\*\*/` form so future copy-paste does not regress the strip.
- **Suggested revision**: Address the concern above.

### FINDING_24: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: 2. **risk-integration** (process) Issue is blocked on #2973 per plan; this PR correctly does not touch `scripts/run-external-agent.sh`. Landing order remains an operator concern, not a plan-fidelity gap in this diff.
- **Suggested revision**: Address the concern above.

