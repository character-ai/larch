### [rejected] FINDING_1

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_1: correctness: .claude/rules/python-test-monkeypatch-lambdas.md:1-18
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Pyright lambda guidance is only in path-triggered Claude rules; external Codex/Cursor implementers never receive it during /implement. Codex implements a test-only plan adding monkeypatch.setattr lambdas without the suppression; make py-lint fails at ship with the same reportUnknownLambdaType class as the original escalation. Add a design-reachable note (readability-style or plan template) for python/test_* monkeypatch plans, or document in AGENTS.md / external implementer agent prompts.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0

### [rejected] FINDING_11

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_11: **correctness** `skills/design/references/readability-style.md:37-38` — The new fence-harness reminder is scoped to “`/design` Step 2b”, but implement-plan edits can also land during Gate B apply-all and other post-2b revision paths that still require reading this file (`skills/design/references/approval-gates.md:3`). Step-2b-only wording can let designers skip listing `scripts/test-implement-fence-shape.sh` on revised plans that add implement fences outside Step 2b. **Suggested fix:** Broaden the condition to any `/design` plan draft or revision that adds, removes, or converts Bash fences in `skills/implement/SKILL.md`, not only Step 2b.
- **Reviewer**: dyn-prompt-drift-output.txt
- **Concern**: - **correctness** `skills/design/references/readability-style.md:37-38` — The new fence-harness reminder is scoped to “`/design` Step 2b”, but implement-plan edits can also land during Gate B apply-all and other post-2b revision paths that still require reading this file (`skills/design/references/approval-gates.md:3`). Step-2b-only wording can let designers skip listing `scripts/test-implement-fence-shape.sh` on revised plans that add implement fences outside Step 2b. **Suggested fix:** Broaden the condition to any `/design` plan draft or revision that adds, removes, or converts Bash fences in `skills/implement/SKILL.md`, not only Step 2b.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_12: **correctness** `.claude/rules/python-test-monkeypatch-lambdas.md:1-18` — Pyright lambda guidance is injected only via Claude Code path-triggered rules (`AGENTS.md` Tier 1c) when `python/test_*.py` is read or edited. External implementers (Codex/Cursor) do not load `.claude/rules/`, and unlike the fence case there is no matching plan-drafting note in `skills/design/references/readability-style.md`. The original escalation failure was Codex-authored `python/test_oos_filer.py`; that author surface remains uncovered, so `reportUnknownLambdaType` can recur on new monkeypatch lambdas. **Suggested fix:** Add a design-side plan-drafting reminder (parallel to the fence-harness bullets) for plans that add or modify strict-mode `monkeypatch.setattr(..., lambda ...)` tests, or document the pattern in a surface external implementers actually consume (for example plan templates or implementer prompts).
- **Reviewer**: dyn-prompt-drift-output.txt
- **Concern**: - **correctness** `.claude/rules/python-test-monkeypatch-lambdas.md:1-18` — Pyright lambda guidance is injected only via Claude Code path-triggered rules (`AGENTS.md` Tier 1c) when `python/test_*.py` is read or edited. External implementers (Codex/Cursor) do not load `.claude/rules/`, and unlike the fence case there is no matching plan-drafting note in `skills/design/references/readability-style.md`. The original escalation failure was Codex-authored `python/test_oos_filer.py`; that author surface remains uncovered, so `reportUnknownLambdaType` can recur on new monkeypatch lambdas. **Suggested fix:** Add a design-side plan-drafting reminder (parallel to the fence-harness bullets) for plans that add or modify strict-mode `monkeypatch.setattr(..., lambda ...)` tests, or document the pattern in a surface external implementers actually consume (for example plan templates or implementer prompts).
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0

### [rejected] FINDING_15

**Rejected subtype:** dismissed (0 YES)

### FINDING_15: **code-quality** `.claude/rules/python-test-monkeypatch-lambdas.md:17` — The rule says “See the existing pattern in `python/test_pr_body.py`” without a line anchor, but that file mixes unrelated `# type: ignore[arg-type]` uses (`python/test_pr_body.py:41-60`, `python/test_pr_body.py:163` on `_NoopRunner()` call sites) with the one relevant `monkeypatch.setattr(..., lambda ...)` example at `python/test_pr_body.py:218`. That weakens the discoverability goal this branch is meant to fix and can push authors toward broad `arg-type` suppressions on non-monkeypatch lines. **Suggested fix:** Cite `python/test_pr_body.py:218` explicitly (as the design outline specified) and state that other `arg-type` ignores in that file are unrelated stub-object call-site suppressions, not monkeypatch-lambda guidance.
- **Reviewer**: dyn-pyright-tests-output.txt
- **Concern**: - **code-quality** `.claude/rules/python-test-monkeypatch-lambdas.md:17` — The rule says “See the existing pattern in `python/test_pr_body.py`” without a line anchor, but that file mixes unrelated `# type: ignore[arg-type]` uses (`python/test_pr_body.py:41-60`, `python/test_pr_body.py:163` on `_NoopRunner()` call sites) with the one relevant `monkeypatch.setattr(..., lambda ...)` example at `python/test_pr_body.py:218`. That weakens the discoverability goal this branch is meant to fix and can push authors toward broad `arg-type` suppressions on non-monkeypatch lines. **Suggested fix:** Cite `python/test_pr_body.py:218` explicitly (as the design outline specified) and state that other `arg-type` ignores in that file are unrelated stub-object call-site suppressions, not monkeypatch-lambda guidance.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** dismissed (0 YES)

### FINDING_16: **code-quality** `.claude/rules/python-test-monkeypatch-lambdas.md:12-14` — The rule prescribes only `# type: ignore[arg-type]` but does not name the pyright diagnostics that actually fire (`reportUnknownLambdaType`, `reportUnknownArgumentType`), nor mention the stricter alternative already used in `python/test_collect_results.py:267-268` (`# type: ignore[reportUnknownArgumentType, reportUnknownLambdaType]`). If `arg-type` ever fails to cover both codes under strict pyright, authors get no signal to widen the suppression while still keeping it lambda-scoped. **Suggested fix:** Add one sentence naming the two diagnostics and note that `arg-type` is the repo’s usual shorthand, with `python/test_collect_results.py:267-268` as the explicit-code fallback when pyright still reports `reportUnknownLambdaType`.
- **Reviewer**: dyn-pyright-tests-output.txt
- **Concern**: - **code-quality** `.claude/rules/python-test-monkeypatch-lambdas.md:12-14` — The rule prescribes only `# type: ignore[arg-type]` but does not name the pyright diagnostics that actually fire (`reportUnknownLambdaType`, `reportUnknownArgumentType`), nor mention the stricter alternative already used in `python/test_collect_results.py:267-268` (`# type: ignore[reportUnknownArgumentType, reportUnknownLambdaType]`). If `arg-type` ever fails to cover both codes under strict pyright, authors get no signal to widen the suppression while still keeping it lambda-scoped. **Suggested fix:** Add one sentence naming the two diagnostics and note that `arg-type` is the repo’s usual shorthand, with `python/test_collect_results.py:267-268` as the explicit-code fallback when pyright still reports `reportUnknownLambdaType`.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** dismissed (0 YES)

### FINDING_2: correctness: .claude/rules/skill-editing-trace.md:14-20
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Fence-harness prose is implement-specific but injected on every skills/**/SKILL.md edit via broad paths glob. Editing design or review SKILL.md surfaces implement fence-count guidance unrelated to the edit, reducing rule signal. Split into a dedicated implement-fence rule scoped to skills/implement/SKILL.md and scripts/test-implement-fence-shape.sh.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** dismissed (0 YES)

### FINDING_3: correctness: .claude/rules/python-test-monkeypatch-lambdas.md:17
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Reference to test_pr_body.py lacks line-level anchor and file has multiple unrelated arg-type suppressions. Implementers may apply type ignores on wrong lines or miss the setattr+lambda pattern. Cite python/test_pr_body.py:218 as the canonical monkeypatch setattr lambda example.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

