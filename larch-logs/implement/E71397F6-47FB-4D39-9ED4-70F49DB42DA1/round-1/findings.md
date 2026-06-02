### FINDING_1: `compose_pr_body` builds `parts`, joins to `body`, then calls `tracking_issue.link_pr_closes` before `sanitize_fragment` / `redact` — correct ordering preserved.
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: - `compose_pr_body` builds `parts`, joins to `body`, then calls `tracking_issue.link_pr_closes` before `sanitize_fragment` / `redact` — correct ordering preserved.
- **Suggested revision**: Address the concern above.

### FINDING_2: `link_pr_closes` uses `re.search(rf"Closes #{issue_number}(?!\d)", body)` — fixes `#4` / `#42` / `#421` prefix collision without changing append format.
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: - `link_pr_closes` uses `re.search(rf"Closes #{issue_number}(?!\d)", body)` — fixes `#4` / `#42` / `#421` prefix collision without changing append format.
- **Suggested revision**: Address the concern above.

### FINDING_3: `import tracking_issue` in `pr_body.py` does not create a cycle (`tracking_issue` does not import `pr_body`).
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: - `import tracking_issue` in `pr_body.py` does not create a cycle (`tracking_issue` does not import `pr_body`).
- **Suggested revision**: Address the concern above.

### FINDING_4: `grep PrBodyParts python/` — no matches outside run-log artifacts.
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: - `grep PrBodyParts python/` — no matches outside run-log artifacts.
- **Suggested revision**: Address the concern above.

### FINDING_5: Duplicate `Closes #N` composition in `python/` is gone; only `tracking_issue.link_pr_closes` formats the line.
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: - Duplicate `Closes #N` composition in `python/` is gone; only `tracking_issue.link_pr_closes` formats the line.
- **Suggested revision**: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] architecture
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: 1. **architecture** `scripts/ship-pr.sh:1535` — Bash still composes `Closes #$(read_state ISSUE_NUMBER)` inline while the Python tree now centralizes on `link_pr_closes`; the plan explicitly deferred bash parity. **Why out of scope:** pre-existing cross-surface asymmetry, not introduced by this diff.
- **Suggested revision**: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] code-quality
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: 2. **code-quality** `python/test_tracking_issue.py:49-52` — `test_link_pr_closes_appends` only asserts `"Closes #42" in linked`, not exact trailing layout (`\n\nCloses #42\n`). **Why out of scope:** test predates this branch; new tests add stronger coverage for idempotency and collision.
- **Suggested revision**: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] architecture
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: 3. **architecture** (branch composition) — Branch vs `main` also carries the #3300 Step 18 bash refactor and a `larch-logs` flush; only `c4b8b5a10` is `python/`-only. **Why out of scope:** unrelated commits, not regressions from the reconcile diff.
- **Suggested revision**: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] code-quality
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 1. **code-quality** `python/test_tracking_issue.py:61-65` — The plan’s edge-case list also calls out leading-prefix collision (`Closes #4` vs issue `42`), which the regex fix addresses but only the trailing case (`#421` vs `#42`) is regression-tested. **Suggested fix:** Add `test_link_pr_closes_no_leading_prefix_collision` with body `"Summary\n\nCloses #421\n"` and `issue_number=42` swapped to body containing `Closes #42` and `issue_number=4` if you want parity with the documented edge cases (not required by acceptance).
- **Suggested revision**: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 2. **risk-integration** (branch-level) — `merge-base..HEAD` vs main includes large non-`python/` changes from `57c30c487` and run logs from `a4c6aa527`; only `c4b8b5a10` satisfies the plan’s “no files outside `python/`” acceptance. **Suggested fix:** Split or rebase so the Phase 5 PR contains only the reconcile commit if acceptance is evaluated at PR scope. Out of scope for correctness of the Python diff itself.
- **Suggested revision**: Address the concern above.

### FINDING_11: risk-integration: python/test_tracking_issue.py:61
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Missing unit test for shorter-issue substring false positive (Closes #42 vs append #4). Reverting to `needle in body` would pass current tests but skip appending Closes #4 when body already has Closes #42. Add test_link_pr_closes_no_suffix_collision: body with Closes #42, link_pr_closes(body, 4) must append Closes #4.
- **Suggested revision**: Address the concern above.

### FINDING_12: risk-integration: python/test_pr.py:126
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] No ensure_pr integration test for digit-boundary guard on link_pr_closes. ensure_pr could stop updating PR bodies when only a longer issue number is present (e.g. #421 vs wanted #42) without test_pr.py failing. Add/extend ensure_pr test: body with Closes #421, issue 42, assert linked body includes Closes #42 and update/create is invoked.
- **Suggested revision**: Address the concern above.

### FINDING_13: risk-integration: python/test_tracking_issue.py:49
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] test_link_pr_closes_appends uses weak substring assertion. Append formatting regressions (\n\n prefix, trailing newline) would not be caught. Assert linked.endswith("\n\nCloses #42\n") or compare to a golden string.
- **Suggested revision**: Address the concern above.

### FINDING_14: [OUT_OF_SCOPE] risk-integration: python/test_pr_body.py
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] No test for issue_number=None omitting Closes. Pre-existing; not introduced by this branch. Add test_compose_pr_body_omits_closes_when_no_issue if desired later.
- **Suggested revision**: Address the concern above.

### FINDING_15: [OUT_OF_SCOPE] risk-integration: branch:57c30c487
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Branch diff exceeds python/-only plan acceptance. Unrelated harness/skill changes increase CI surface on merge; not a defect of the Python commit itself. Split PRs or document stacked commits for reviewers.
- **Suggested revision**: Address the concern above.

### FINDING_16: **`link_pr_closes` regex** (`python/tracking_issue.py:181`): `issue_number` is typed and called as `int` (`compose_pr_body`, `pr._issue_number` digit-only parse). Embedding it in `rf"Closes #{issue_number}(?!\d)"` does not introduce regex injection or meaningful ReDoS; the pattern is linear.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **`link_pr_closes` regex** (`python/tracking_issue.py:181`): `issue_number` is typed and called as `int` (`compose_pr_body`, `pr._issue_number` digit-only parse). Embedding it in `rf"Closes #{issue_number}(?!\d)"` does not introduce regex injection or meaningful ReDoS; the pattern is linear.
- **Suggested revision**: Address the concern above.

### FINDING_17: **Trust boundaries unchanged**: PR body still flows through existing `sanitize_fragment` and `redact.redact` after composition; no new shell, network, deserialization, or secret-handling paths.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Trust boundaries unchanged**: PR body still flows through existing `sanitize_fragment` and `redact.redact` after composition; no new shell, network, deserialization, or secret-handling paths.
- **Suggested revision**: Address the concern above.

### FINDING_18: **Delegation to `tracking_issue.link_pr_closes`**: Does not weaken auth or expand attack surface; it centralizes string assembly/idempotency only.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Delegation to `tracking_issue.link_pr_closes`**: Does not weaken auth or expand attack surface; it centralizes string assembly/idempotency only.
- **Suggested revision**: Address the concern above.

### FINDING_19: **No secrets, injection, or boundary regressions** in the added tests.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **No secrets, injection, or boundary regressions** in the added tests. **Stall-recovery diff (commit `57c30c487`, security pass)**
- **Suggested revision**: Address the concern above.

### FINDING_20: New `clear-stall` / `seed-terminal-state` paths use **symlink / non-regular-file guards** on `ship-pr-state.sh`, which hardens TOCTOU-style issues vs blind writes.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - New `clear-stall` / `seed-terminal-state` paths use **symlink / non-regular-file guards** on `ship-pr-state.sh`, which hardens TOCTOU-style issues vs blind writes.
- **Suggested revision**: Address the concern above.

### FINDING_21: `rewrite_ship_pr_state_keys` uses script-supplied keys and `safe_step_value` / `safe_phase_value` on CLI/disk-derived phase/step values; values passed to `awk -v` get backslash escaping. No new command-injection or path-traversal surface beyond the existing “orchestrator supplies `--implement-tmpdir`” trust model (same as other subcommands that only require `[ -d "$tmpdir" ]`).
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - `rewrite_ship_pr_state_keys` uses script-supplied keys and `safe_step_value` / `safe_phase_value` on CLI/disk-derived phase/step values; values passed to `awk -v` get backslash escaping. No new command-injection or path-traversal surface beyond the existing “orchestrator supplies `--implement-tmpdir`” trust model (same as other subcommands that only require `[ -d "$tmpdir" ]`). ---
- **Suggested revision**: Address the concern above.

### FINDING_22: correctness: python/pr_body.py:265-267
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] compose_pr_body now uses whole-body link_pr_closes idempotency instead of always appending a footer Closes line Summary or test plan contains a literal Closes #42 inside a code fence or non-closing prose; regex treats it as present and skips footer append; old compose always added footer — possible GitHub auto-close miss if only the non-parsing mention remains Restrict idempotency to footer/tail segment or document and test; add compose regression for fenced Closes #42 with required footer
- **Suggested revision**: Address the concern above.

### FINDING_23: risk-integration: branch vs main (skills/implement/, Makefile, larch-logs/, .claude-plugin/)
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Branch mixes Phase 5 python-only plan with unrelated #3360 and larch-logs commits Plan acceptance No files outside python/ is violated; review and bisect span unrelated stall-recovery and run-log churn Split PR or rebase to land c4b8b5a10 alone on a clean branch
- **Suggested revision**: Address the concern above.

### FINDING_24: code-quality: python/test_tracking_issue.py:61-65
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Missing leading-digit prefix-collision test (#4 vs Closes #42) despite plan edge-case list Regression could reintroduce substring-style false idempotency on the leading side without CI failure Add test_link_pr_closes_no_leading_prefix_collision for issue_number=4 with body containing Closes #42
- **Suggested revision**: Address the concern above.

### FINDING_25: [OUT_OF_SCOPE] architecture: python/pr.py:48-56
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] ensure_pr update path skips compose_pr_body sanitization/redact stack Phase 7 caller could publish via update_pr_body what compose_pr_body would reject Address in Phase 7 wiring; not introduced here
- **Suggested revision**: Address the concern above.

### FINDING_26: [OUT_OF_SCOPE] correctness: python/tracking_issue.py:181
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Case-sensitive Closes detection Body with closes #42 gets duplicate closing lines when link_pr_closes(42) runs Future: case-insensitive guard aligned with GitHub keywords
- **Suggested revision**: Address the concern above.

### FINDING_27: [OUT_OF_SCOPE] risk-integration: 57c30c487
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Large stall-recovery refactor bundled on branch Unrelated review burden and regression risk for a SIMPLE python change Separate PR from Phase 5 work
- **Suggested revision**: Address the concern above.

### FINDING_28: architecture: plan:acceptance (python-only scope)
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Branch diff vs main includes non-python/bash changes from commits 57c30c487 and a4c6aa527 while plan acceptance requires python/ only and no bash changes. Phase 5 acceptance and SIMPLE-tier scope cannot be satisfied for the branch-as-PR even though c4b8b5a10 is correct; reviewers conflate unrelated Step 18 (#3360) work with the Closes reconcile feature. Ship c4b8b5a10 alone on a clean branch/PR, or split/rebase so the Phase 5 PR contains only the four python/ files from the reconcile commit.
- **Suggested revision**: Address the concern above.

### FINDING_29: **risk-integration** `skills/implement/scripts/step-18b-final-report.sh:98-108` — When `.step17-emitted` is present and the pre-write snapshot copy fails (`SNAPSHOT_OK=false`), the wrapper never promotes `emit_body` even if `write-final-report.sh` refreshes `summary-final.md` and `.step18-prebody` was removed after the failed `cp`. The retired inline Step 18 block deleted `.step18-prebody` on copy failure and then treated a missing snapshot as “changed” via `! cmp -s …`, so a post–Step 18 cost/token refresh could still reach top chat. The new `SNAPSHOT_OK=false` branch is a no-op, so operators can get a stale Step 17 summary in chat while disk artifacts update—exactly the “suppressed final summary” failure mode the wrapper is meant to prevent. **Suggested fix:** On `SNAPSHOT_OK=false`, either fall back to the old behavior when `.step18-prebody` is absent after the failed copy (promote when `wfr_rc=0`, body non-empty, and `cmp` differs or prebody missing), or re-run the emit decision using only post-write `cmp` without treating a failed snapshot as a hard veto; add a harness case where `cp` fails, `rm` succeeds, and WFR changes the body to lock the intended behavior.
- **Reviewer**: dyn-report-gates-output.txt
- **Concern**: - **risk-integration** `skills/implement/scripts/step-18b-final-report.sh:98-108` — When `.step17-emitted` is present and the pre-write snapshot copy fails (`SNAPSHOT_OK=false`), the wrapper never promotes `emit_body` even if `write-final-report.sh` refreshes `summary-final.md` and `.step18-prebody` was removed after the failed `cp`. The retired inline Step 18 block deleted `.step18-prebody` on copy failure and then treated a missing snapshot as “changed” via `! cmp -s …`, so a post–Step 18 cost/token refresh could still reach top chat. The new `SNAPSHOT_OK=false` branch is a no-op, so operators can get a stale Step 17 summary in chat while disk artifacts update—exactly the “suppressed final summary” failure mode the wrapper is meant to prevent. **Suggested fix:** On `SNAPSHOT_OK=false`, either fall back to the old behavior when `.step18-prebody` is absent after the failed copy (promote when `wfr_rc=0`, body non-empty, and `cmp` differs or prebody missing), or re-run the emit decision using only post-write `cmp` without treating a failed snapshot as a hard veto; add a harness case where `cp` fails, `rm` succeeds, and WFR changes the body to lock the intended behavior.
- **Suggested revision**: Address the concern above.

### FINDING_30: **risk-integration** `skills/implement/scripts/step-18b-final-report.sh:69-76,117-120` and `skills/implement/SKILL.md:1234-1241` — `token-report.sh` failures are logged best-effort to `execution-issues.md` but are not surfaced in the `EMIT_BODY` / `WFR_RC` contract, so the orchestrator cannot distinguish “fresh summary with updated costs” from “summary rendered from stale `token-report-rendered.json` after refresh failed.” Step 18 still sets `EMIT_BODY=true` when the write path succeeds, which can mislead operators during token-ingest outages. **Suggested fix:** Emit a `TOKEN_RC` (or `TOKEN_OK`) KV from the wrapper and extend the SKILL gate (or a mandatory warning block) so non-zero token refresh forces either a visible warning in the emitted body or `EMIT_BODY=false` when refreshed costs are required.
- **Reviewer**: dyn-report-gates-output.txt
- **Concern**: - **risk-integration** `skills/implement/scripts/step-18b-final-report.sh:69-76,117-120` and `skills/implement/SKILL.md:1234-1241` — `token-report.sh` failures are logged best-effort to `execution-issues.md` but are not surfaced in the `EMIT_BODY` / `WFR_RC` contract, so the orchestrator cannot distinguish “fresh summary with updated costs” from “summary rendered from stale `token-report-rendered.json` after refresh failed.” Step 18 still sets `EMIT_BODY=true` when the write path succeeds, which can mislead operators during token-ingest outages. **Suggested fix:** Emit a `TOKEN_RC` (or `TOKEN_OK`) KV from the wrapper and extend the SKILL gate (or a mandatory warning block) so non-zero token refresh forces either a visible warning in the emitted body or `EMIT_BODY=false` when refreshed costs are required.
- **Suggested revision**: Address the concern above.

### FINDING_31: **risk-integration** `python/pr_body.py:265-272` — `compose_pr_body` now appends `Closes #N` via `tracking_issue.link_pr_closes` before `sanitize_fragment(…, from_md=True)` and `redact.redact`, so the closes line is validated for mermaid safety but not passed through the same redaction path ordering as the rest of the assembled body if future redaction rules become position-sensitive. Today this matches prior “append then sanitize/redact whole body” ordering, but it couples PR-body composition to `tracking_issue` at a point where downstream ship/tracking paths may assume independent modules until Phase 7 cutover. **Suggested fix:** Document in `python/README.md` (or a one-line comment at the call site) that `link_pr_closes` is the single canonical composer for both `compose_pr_body` and `pr.ensure_pr`, and add an integration test that runs `compose_pr_body(…, issue_number=N)` through redact with a fixture summary containing secret-like tokens adjacent to a `Closes #421` / `Closes #42` pair to guard prefix-collision + redaction interaction.
- **Reviewer**: dyn-report-gates-output.txt
- **Concern**: - **risk-integration** `python/pr_body.py:265-272` — `compose_pr_body` now appends `Closes #N` via `tracking_issue.link_pr_closes` before `sanitize_fragment(…, from_md=True)` and `redact.redact`, so the closes line is validated for mermaid safety but not passed through the same redaction path ordering as the rest of the assembled body if future redaction rules become position-sensitive. Today this matches prior “append then sanitize/redact whole body” ordering, but it couples PR-body composition to `tracking_issue` at a point where downstream ship/tracking paths may assume independent modules until Phase 7 cutover. **Suggested fix:** Document in `python/README.md` (or a one-line comment at the call site) that `link_pr_closes` is the single canonical composer for both `compose_pr_body` and `pr.ensure_pr`, and add an integration test that runs `compose_pr_body(…, issue_number=N)` through redact with a fixture summary containing secret-like tokens adjacent to a `Closes #421` / `Closes #42` pair to guard prefix-collision + redaction interaction.
- **Suggested revision**: Address the concern above.

### FINDING_32: [OUT_OF_SCOPE] The branch bundles three commits: Python `Closes` reconciliation (`c4b8b5a10`), Step 18b plumbing from #3360 (`57c30c487`), and an implement run-log flush (`a4c6aa527`). The feature plan’s “`python/`-only” acceptance criteria do not match the full diff (Makefile, `skills/implement/*`, harnesses)—worth noting for release notes, not a defect in the Python change itself.
- **Reviewer**: dyn-report-gates-output.txt
- **Concern**: - The branch bundles three commits: Python `Closes` reconciliation (`c4b8b5a10`), Step 18b plumbing from #3360 (`57c30c487`), and an implement run-log flush (`a4c6aa527`). The feature plan’s “`python/`-only” acceptance criteria do not match the full diff (Makefile, `skills/implement/*`, harnesses)—worth noting for release notes, not a defect in the Python change itself.
- **Suggested revision**: Address the concern above.

### FINDING_33: [OUT_OF_SCOPE] `step-18b-final-report.sh` + `test-step-18b-final-report.sh` provide solid offline coverage (emit absent/changed/unchanged, WFR fail, empty body, token fail, cp-fail, real `write-final-report` integration). The cp-fail case encodes the conservative no-emit behavior rather than the pre-wrapper inline semantics.
- **Reviewer**: dyn-report-gates-output.txt
- **Concern**: - `step-18b-final-report.sh` + `test-step-18b-final-report.sh` provide solid offline coverage (emit absent/changed/unchanged, WFR fail, empty body, token fail, cp-fail, real `write-final-report` integration). The cp-fail case encodes the conservative no-emit behavior rather than the pre-wrapper inline semantics.
- **Suggested revision**: Address the concern above.

### FINDING_34: [OUT_OF_SCOPE] Python changes (`tracking_issue.link_pr_closes` digit-boundary guard, `compose_pr_body` delegation, dead `PrBodyParts` removal, new unit tests) align with the plan and do not introduce circular imports; no additional in-scope defects found there beyond the redaction-order note above.
- **Reviewer**: dyn-report-gates-output.txt
- **Concern**: - Python changes (`tracking_issue.link_pr_closes` digit-boundary guard, `compose_pr_body` delegation, dead `PrBodyParts` removal, new unit tests) align with the plan and do not introduce circular imports; no additional in-scope defects found there beyond the redaction-order note above.
- **Suggested revision**: Address the concern above.

### FINDING_35: **correctness** `python/pr_body.py:265-267` — `compose_pr_body` now delegates to `tracking_issue.link_pr_closes`, which treats a `Closes #N` match anywhere in the assembled body as idempotent. Before this branch, `compose_pr_body` always appended a footer `Closes #N` after the test-plan section regardless of earlier content. If the same token appears only inside a fenced ` ```mermaid ` block (or elsewhere GitHub does not treat as a closing keyword), `link_pr_closes` skips the footer line while `ensure_pr` in `python/pr.py:48-66` applies the same helper on the same body, so auto-close can be lost end-to-end. Bash `scripts/ship-pr.sh:1535-1545` always emits a dedicated footer `closes` line and does not whole-body-scan for idempotency. **Suggested fix:** Keep `link_pr_closes` for `ensure_pr` updates, but in `compose_pr_body` either always append the footer when `issue_number is not None` (old behavior), or narrow idempotency to non-fenced / trailing-footer text (e.g. ignore matches inside mermaid fences, or only inspect the last non-empty lines) so a decorative in-diagram `Closes #N` cannot suppress the real footer.
- **Reviewer**: dyn-pr-linkage-output.txt
- **Concern**: - **correctness** `python/pr_body.py:265-267` — `compose_pr_body` now delegates to `tracking_issue.link_pr_closes`, which treats a `Closes #N` match anywhere in the assembled body as idempotent. Before this branch, `compose_pr_body` always appended a footer `Closes #N` after the test-plan section regardless of earlier content. If the same token appears only inside a fenced ` ```mermaid ` block (or elsewhere GitHub does not treat as a closing keyword), `link_pr_closes` skips the footer line while `ensure_pr` in `python/pr.py:48-66` applies the same helper on the same body, so auto-close can be lost end-to-end. Bash `scripts/ship-pr.sh:1535-1545` always emits a dedicated footer `closes` line and does not whole-body-scan for idempotency. **Suggested fix:** Keep `link_pr_closes` for `ensure_pr` updates, but in `compose_pr_body` either always append the footer when `issue_number is not None` (old behavior), or narrow idempotency to non-fenced / trailing-footer text (e.g. ignore matches inside mermaid fences, or only inspect the last non-empty lines) so a decorative in-diagram `Closes #N` cannot suppress the real footer.
- **Suggested revision**: Address the concern above.

### FINDING_36: [OUT_OF_SCOPE] The Phase 5 reconcile commit (`c4b8b5a10`) is `python/`-only and matches the plan; the full branch diff vs `main` also includes unrelated implement stall-recovery work (`57c30c487`), run-log flush (`a4c6aa527`), and `.claude-plugin/plugin.json` churn — outside this feature’s stated acceptance scope but not introduced by the reconcile hunks.
- **Reviewer**: dyn-pr-linkage-output.txt
- **Concern**: - The Phase 5 reconcile commit (`c4b8b5a10`) is `python/`-only and matches the plan; the full branch diff vs `main` also includes unrelated implement stall-recovery work (`57c30c487`), run-log flush (`a4c6aa527`), and `.claude-plugin/plugin.json` churn — outside this feature’s stated acceptance scope but not introduced by the reconcile hunks.
- **Suggested revision**: Address the concern above.

### FINDING_37: [OUT_OF_SCOPE] `link_pr_closes` remains case-sensitive (`Closes` only); a body with `closes #42` still gets a canonical `Closes #42` footer. That behavior predates this branch and is consistent with `scripts/extract-closes-issue-from-pr.sh`’s `Closes #[0-9]+` grep.
- **Reviewer**: dyn-pr-linkage-output.txt
- **Concern**: - `link_pr_closes` remains case-sensitive (`Closes` only); a body with `closes #42` still gets a canonical `Closes #42` footer. That behavior predates this branch and is consistent with `scripts/extract-closes-issue-from-pr.sh`’s `Closes #[0-9]+` grep.
- **Suggested revision**: Address the concern above.

### FINDING_38: [OUT_OF_SCOPE] New tests cover append, idempotency, and `#42` vs `#421` for `link_pr_closes` and a happy-path `compose_pr_body` closes line; they do not exercise the fenced-mermaid false-idempotency case above.
- **Reviewer**: dyn-pr-linkage-output.txt
- **Concern**: - New tests cover append, idempotency, and `#42` vs `#421` for `link_pr_closes` and a happy-path `compose_pr_body` closes line; they do not exercise the fenced-mermaid false-idempotency case above.
- **Suggested revision**: Address the concern above.

### FINDING_39: **architecture** Branch vs `main` (commits `57c30c487`, `c4b8b5a10`, `a4c6aa527`) — The branch stacks three unrelated workstreams: merged #3360 Step 18 runtime/bash surface (`skills/implement/`, `Makefile`, `scripts/test-implement-structure.sh`, plugin version), the #3326 Python-only reconcile (`python/*` in `c4c8b5a10`), and additional `larch-logs/` flushes. That violates the #3326 plan acceptance line “No files outside `python/` are modified” and mixes dev/CI Python rework with shipped `/implement` orchestration in one review unit, which makes architecture review and rollback boundaries unclear. **Suggested fix:** Split into separate PRs (or rebase onto `main` so this branch contains only `c4c8b5a10`’s four `python/` files plus its tests) before merge; keep runtime Step 18 work on its own branch/PR.
- **Reviewer**: dyn-surface-sync-output.txt
- **Concern**: - **architecture** Branch vs `main` (commits `57c30c487`, `c4b8b5a10`, `a4c6aa527`) — The branch stacks three unrelated workstreams: merged #3360 Step 18 runtime/bash surface (`skills/implement/`, `Makefile`, `scripts/test-implement-structure.sh`, plugin version), the #3326 Python-only reconcile (`python/*` in `c4c8b5a10`), and additional `larch-logs/` flushes. That violates the #3326 plan acceptance line “No files outside `python/` are modified” and mixes dev/CI Python rework with shipped `/implement` orchestration in one review unit, which makes architecture review and rollback boundaries unclear. **Suggested fix:** Split into separate PRs (or rebase onto `main` so this branch contains only `c4c8b5a10`’s four `python/` files plus its tests) before merge; keep runtime Step 18 work on its own branch/PR.
- **Suggested revision**: Address the concern above.

### FINDING_40: **architecture** `larch-logs/implement/5243990C-210B-4AA1-B141-9F1F3B13CD20/` (introduced in `57c30c487`) — Roughly 427 paths under that run id land in the full branch diff vs `main` (mostly `breadcrumbs/larch-quiet-*.log` and full round artifacts from a prior implement run), while the precomputed review diff covers only 19 non-log paths. That pollutes the repository surface with an unrelated run’s committed breadcrumbs and dwarfs the intended #3326 delta (~33 plan lines). **Suggested fix:** Drop the `5243990C` tree from this branch (revert or interactive rebase of `57c30c487`’s log payload); if a run log is required, commit only the run tied to #3326 (`E71397F6` per `a4c6aa527`) or follow `docs/run-logs.md` publication rules without importing another run’s breadcrumb tree.
- **Reviewer**: dyn-surface-sync-output.txt
- **Concern**: - **architecture** `larch-logs/implement/5243990C-210B-4AA1-B141-9F1F3B13CD20/` (introduced in `57c30c487`) — Roughly 427 paths under that run id land in the full branch diff vs `main` (mostly `breadcrumbs/larch-quiet-*.log` and full round artifacts from a prior implement run), while the precomputed review diff covers only 19 non-log paths. That pollutes the repository surface with an unrelated run’s committed breadcrumbs and dwarfs the intended #3326 delta (~33 plan lines). **Suggested fix:** Drop the `5243990C` tree from this branch (revert or interactive rebase of `57c30c487`’s log payload); if a run log is required, commit only the run tied to #3326 (`E71397F6` per `a4c6aa527`) or follow `docs/run-logs.md` publication rules without importing another run’s breadcrumb tree.
- **Suggested revision**: Address the concern above.

### FINDING_41: **architecture** `docs/linting.md:212` — `make test-step-18b-final-report` is registered in `Makefile` (`.PHONY`, target block, `test-harnesses-6`) but has no harness table row in `docs/linting.md`, unlike neighboring `make test-stall-recovery-report` (whose shard note was updated). Discoverability and surface-sync drift for the new Step 18b contract wrapper. **Suggested fix:** Add a `docs/linting.md` row for `make test-step-18b-final-report` describing the offline harness, script path, and `test-harnesses-6` shard, mirroring the `test-stall-recovery-report` entry format.
- **Reviewer**: dyn-surface-sync-output.txt
- **Concern**: - **architecture** `docs/linting.md:212` — `make test-step-18b-final-report` is registered in `Makefile` (`.PHONY`, target block, `test-harnesses-6`) but has no harness table row in `docs/linting.md`, unlike neighboring `make test-stall-recovery-report` (whose shard note was updated). Discoverability and surface-sync drift for the new Step 18b contract wrapper. **Suggested fix:** Add a `docs/linting.md` row for `make test-step-18b-final-report` describing the offline harness, script path, and `test-harnesses-6` shard, mirroring the `test-stall-recovery-report` entry format.
- **Suggested revision**: Address the concern above.

