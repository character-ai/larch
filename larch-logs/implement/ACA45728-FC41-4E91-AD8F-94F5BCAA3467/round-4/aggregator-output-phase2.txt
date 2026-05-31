Normalizing and merging the supplied reviewer findings into one structured list. Verifying a few merge candidates against the cited locations.
### FINDING_1: Legacy resolve-conflict path omits CI stderr-tail surfacing
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: Legacy resolve-conflict CI launcher path never calls `_surface_ci_stderr_tail`. Agent failure during rebase conflict resolution after waterfall exhaustion records failure but does not emit `${conflict_out}.stderr-tail` to chat, unlike fix-loop and recovery waterfall tiers. Parse `LAUNCHER_EXIT` from `fail_file` and call `_surface_ci_stderr_tail "$conflict_out"` on rc, launcher exit, or non-empty tail before `record_failure`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_2: Duplicated lint stderr-tail stem logic (Step 5 vs ship-pr RCC)
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `_surface_lint_fix_stderr_tail` duplicates `step5_surface_lint_stderr_tail` stem logic. Future KV or fallback changes must be edited in two places and can drift (Step 5 vs ship-pr RCC). Extract shared emit-from-KV helper in `lib-failed-agent-stderr-tail.sh` and call from both sites.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_3: Recovery waterfall failure gating split across branches
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Recovery waterfall uses two separate revert/continue blocks for `tier_rc` vs `launcher_exit`/tail. Harder to see that surfacing runs once before all failure exits; slightly higher risk of editing one branch only. Merge failure conditions into one revert/continue after `_surface_ci_stderr_tail`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_4: Repeated awk parsing in `run_lint_fix_loop_capture`
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `run_lint_fix_loop_capture` repeats awk parsing of tail KVs. Minor maintenance noise when extending lint-fix stdout contract. Parse `STDERR_TAIL_PATH` and `CODER_LOG_FILE` once into locals after subshell capture.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_5: `step5_surface_lint_stderr_tail` on lint-fix-attempt-cap success path
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: `step5_surface_lint_stderr_tail` is called on lint-fix-attempt-cap after `applied` status (e.g. `review-implement-step5-loop.sh` ~268–277). Misleading call site; usually a no-op because `STDERR_TAIL_PATH` is unset, but it suggests failure surfacing on a success-shaped terminal path. Harmless when last `LINT_FIX_STATUS` is `applied`; no wrong tail emitted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Restrict `step5_surface_lint_stderr_tail` to failure terminal arms only.
  - From cursor-specialist-correctness-output.txt: Optional comment only; no code change required.

### FINDING_6: Docs omit `cursor.preflight.log` artifact
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `scripts/lint-fix-loop.md` omits `cursor.preflight.log` from run_cursor preflight failures. Operators debugging cursor lint-fix preflight may not know where stderr was captured. Document `cursor.preflight.log` in the lint-fix-loop behavior section.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] #3229 cleanup bundled with #3227 stderr-tail work
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Branch bundles #3229 cleanup (retention/find-fail-safe, harness expansion) with #3227 stderr-tail surfacing. Increases PR blast radius and review surface unrelated to tail surfacing; unrelated cleanup failures or behavior could block merge of stderr-tail work; none required for #3227 fidelity. Consider splitting releases, commits, or PRs and tracking separately for review clarity.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] CHANGELOG 47.0.13 vs #3227 feature alignment
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: `CHANGELOG.md` 47.0.13 bullets describe cleanup while Unreleased Added describes #3227. Release readers or operators reading only 47.0.13 may think the release is cleanup-only and miss stderr-tail surfacing shipped on the same branch. Align version-section bullets with shipped features or reference both issues explicitly in `[47.0.13]` when cutting release.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_9: Cursor implement auth-retry can delete prior `.stderr-tail`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Cursor implement auth-retry clears sidecar/diag but not `.stderr-tail`; a later `run-external-agent` failure with empty stderr source can `rm` the tail via `write_failed_agent_stderr_tail`. First auth attempt writes `${TRANSCRIPT}.stderr-tail`; retry clears diag; second attempt has no source, lib `rm -f` tail; `step2` `emit_failed_agent_stderr_tail_larch_err` is a no-op while `SIDECAR_LOG` may still hold the error. On auth-retry `continue`, `rm` `${TRANSCRIPT_PATH}.stderr-tail` or avoid `rm` when new source empty; add final `write_failed_agent_stderr_tail` from sidecar/diag like codex-implement.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_10: Untested `wrapper_rc=2` CI stderr-tail surfacing in ship-pr
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `run_ci_fix_vendor` `wrapper_rc=2` surfacing is untested despite new `_surface_ci_stderr_tail` on that choke point. A regression removing the `wrapper_rc=2` emit would not fail CI; operators would lose stderr tails on CI launcher validation failures while the waterfall still advances. Add a ship-pr harness case: cursor stub exit 2, pre-seed `${tier_out}.stderr-tail`, assert probe on caller stderr before codex tier.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_11: Untested manifest `STATUS=bailed` stderr-tail surfacing (Step 2)
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Manifest `STATUS=bailed` consumer surfacing is untested; only cursor-runtime-failure (`emit_bailed`) is covered in Test 22. If the bailed-case emit is removed or broken, manifest-driven implement failures would stop surfacing tails while runtime-failure path still passes tests. Add a stub-bailed test with a pre-written `${TRANSCRIPT}.stderr-tail` and assert marker on dispatcher stderr.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_12: Untested `run_lint_fix_loop_capture` tail-only branch
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `run_lint_fix_loop_capture` empty `LINT_FIX_STATUS` + on-disk tail branch has no test. Malformed or partial lint-fix stdout could skip surfacing even when `${stem}.stderr-tail` exists, without failing existing RCC cases. Stub lint-fix-loop with `STDERR_TAIL_PATH` only (no `LINT_FIX_STATUS`), `rc=0`, seeded tail; assert caller stderr receives probe.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_13: Untested recovery waterfall `tier_rc`-only failure surfacing
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Recovery waterfall `tier_rc`-only failure path is not isolated in new tests. A change gating surfacing only on `LAUNCHER_EXIT` or `-s` tail could break `tier_rc`-triggered surfacing undetected. Stub launcher exit 1 without `LAUNCHER_EXIT` KV or tail file; assert waterfall continues and surface helper is safe to call.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_14: Overlapping cap/redaction tests across implementer harnesses
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Duplicate cap/redaction tests overlap `test-lib-failed-agent-stderr-tail.sh`. Future cap constant changes require updating multiple harnesses; risk of inconsistent assertions. Consolidate to one bounded/redaction check per implementer or rely on the lib harness only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_15: Expanded stderr-tail emit without emit-time re-redaction
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: New consumer stderr-tail emit sites read pre-redacted `.stderr-tail` files without re-running `redact-secrets` at emit time, expanding #3202 partial-redaction exposure to implement/CI/lint-fix/Step 5 chat paths. Codex/Cursor auth or API errors containing opaque bearer tokens or `CURSOR_API_KEY` values without matching `redact-secrets` patterns can reach operator chat on more failure lanes than before #3227. Treat as accepted operator diagnostic tradeoff if intentional; optionally re-redact at emit or restrict stems to session tmp roots.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_16: `_surface_lint_fix_stderr_tail` lacks session-root stem validation
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: `_surface_lint_fix_stderr_tail` trusts parsed `STDERR_TAIL_PATH`/`CODER_LOG_FILE` stems from capture stdout without session-root validation. A malformed capture file could direct emit at an arbitrary readable `${stem}.stderr-tail` outside the active implement tmpdir. Require stem prefix under `$IMPLEMENT_TMPDIR` (or accepted session roots) before calling `emit_failed_agent_stderr_tail_larch_err`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_17: [OUT_OF_SCOPE] Cleanup maxdepth-5 retention vs deeper session activity
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: #3229 bounded maxdepth-5 retention no longer protects directories with fresh activity deeper than five levels. Session secrets or `CMD_JSON` sidecars stored below depth 5 may be deleted while operators assume nested activity always retains the tree; stale session dirs with activity only below depth 5 may still be deleted. Already documented in `SECURITY.md` / #3229 cleanup tradeoff; operators should not rely on unbounded depth protection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_18: `run_codex` may clobber existing stderr-tail after `run-external-agent`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `run_codex` unconditionally rewrites stderr-tail after `run-external-agent` may have already written it. Redaction fails on the second `write_failed_agent_stderr_tail` call; lib `rm -f` removes an existing good tail; caller-scope surfacing is silent. Only write when `! -s ${run_dir}/codex.log.stderr-tail` or drop redundant post-external-agent write when sink matches.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Only write when ! -s ${run_dir}/codex.log.stderr-tail or drop redundant post-external-agent write when sink matches

### FINDING_19: `_lint_fix_set_stderr_tail_stem` first-wins vs last-failed-agent intent
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-stem-lifecycle-output.txt
- **Severity**: latent
- **Concern**: `_lint_fix_set_stderr_tail_stem` uses first-wins semantics: once `_LINT_FIX_STDERR_TAIL_STEM` points at a stem with a non-empty `${stem}.stderr-tail`, later failures (including cursor after codex on the dual-failure path at `scripts/lint-fix-loop.sh:413-433`) cannot update the stem. That conflicts with the plan’s “last failed agent” intent and with `scripts/test-lint-fix-loop.sh:1008-1010`, which expects `STDERR_TAIL_PATH=$run_dir/cursor.log` when both externals fail but codex has already written `codex.log.stderr-tail`. In the common case (codex fails with a real tail, then cursor fails), chat surfacing via `STDERR_TAIL_PATH` / `ship-pr.sh` `_surface_lint_fix_stderr_tail` / Step 5 will prefer the first failure (codex), not the last attempted agent (cursor).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Prefer latest failing agent stem or explicit cursor-over-codex precedence on dual failure
  - From dyn-stem-lifecycle-output.txt: Drop the early return at lines 29–31 and adopt last-wins when the new stem has a non-empty `${stem}.stderr-tail` (always assign `_LINT_FIX_STDERR_TAIL_STEM="$stem"` on failure paths that produced a tail); keep the empty-stem fallback at line 36 only when no tail file exists yet.

### FINDING_20: First-fixer-non-health no-commit path omits CI stderr-tail surfacing
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: First-fixer-non-health no-commit path does not call `_surface_ci_stderr_tail`. CI tier reports `LAUNCHER_EXIT=0` but leaves stderr-tail on disk; Exit 3 path shows no failed-agent tail in chat. Surface `${ci_fix_out_base}.${winning_tier}.stderr-tail` before `return 1` when the file is non-empty.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Surface ${ci_fix_out_base}.${winning_tier}.stderr-tail before return 1 when the file is non-empty

### FINDING_21: plan-review-loop.sh scope beyond #3227 Decision 7 minimum
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: #3227 Decision 7 allowed `plan-review-loop.sh` edits only when the FD-2 tail harness failed, and then a minimal tee fix; the branch also adds collector hard-fail routing to `panel-failed` and a new harness case not in the plan. Operators and tests may depend on new `panel-failed` semantics that were never specified or accepted for #3227; scope is harder to review and revert independently of stderr-tail surfacing. Keep only the minimum needed for the FD-2 tail test (likely `set +e` around the existing tee); move the empty-stdout `panel-failed` path and its harness case to a separate issue/plan or document and justify them explicitly under #3227.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_22: plan-review-loop harness contract docs incomplete
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: The harness contract in `skills/design/scripts/test-plan-review-loop.md` lists the stderr-tail-fd2 case but not the added collector-hard-fail case in `test-plan-review-loop.sh`. Contributors may not discover or maintain the out-of-plan collector-hard-fail regression. Document the case in `test-plan-review-loop.md` or remove it if the matching `plan-review-loop.sh` logic is dropped.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

---

**Aggregation notes (non-voting):** Input findings 29–30 from `dyn-stem-lifecycle-output.txt` are negative attestations (no clobber defect; orphan-tail gating deliberate and tested) and are omitted as they require no voter action. Merged groups: 5+10, 7+17+27, 8+11, 20+24, 22+28. Twenty-two normalized findings for the voter round.
