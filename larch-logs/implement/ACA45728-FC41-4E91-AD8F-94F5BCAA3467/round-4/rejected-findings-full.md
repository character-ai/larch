### [rejected] FINDING_14

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_14: Overlapping cap/redaction tests across implementer harnesses
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Duplicate cap/redaction tests overlap `test-lib-failed-agent-stderr-tail.sh`. Future cap constant changes require updating multiple harnesses; risk of inconsistent assertions. Consolidate to one bounded/redaction check per implementer or rely on the lib harness only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_15

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_15: Expanded stderr-tail emit without emit-time re-redaction
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: New consumer stderr-tail emit sites read pre-redacted `.stderr-tail` files without re-running `redact-secrets` at emit time, expanding #3202 partial-redaction exposure to implement/CI/lint-fix/Step 5 chat paths. Codex/Cursor auth or API errors containing opaque bearer tokens or `CURSOR_API_KEY` values without matching `redact-secrets` patterns can reach operator chat on more failure lanes than before #3227. Treat as accepted operator diagnostic tradeoff if intentional; optionally re-redact at emit or restrict stems to session tmp roots.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_16: `_surface_lint_fix_stderr_tail` lacks session-root stem validation
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: `_surface_lint_fix_stderr_tail` trusts parsed `STDERR_TAIL_PATH`/`CODER_LOG_FILE` stems from capture stdout without session-root validation. A malformed capture file could direct emit at an arbitrary readable `${stem}.stderr-tail` outside the active implement tmpdir. Require stem prefix under `$IMPLEMENT_TMPDIR` (or accepted session roots) before calling `emit_failed_agent_stderr_tail_larch_err`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_18

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_18: `run_codex` may clobber existing stderr-tail after `run-external-agent`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `run_codex` unconditionally rewrites stderr-tail after `run-external-agent` may have already written it. Redaction fails on the second `write_failed_agent_stderr_tail` call; lib `rm -f` removes an existing good tail; caller-scope surfacing is silent. Only write when `! -s ${run_dir}/codex.log.stderr-tail` or drop redundant post-external-agent write when sink matches.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Only write when ! -s ${run_dir}/codex.log.stderr-tail or drop redundant post-external-agent write when sink matches


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: Duplicated lint stderr-tail stem logic (Step 5 vs ship-pr RCC)
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `_surface_lint_fix_stderr_tail` duplicates `step5_surface_lint_stderr_tail` stem logic. Future KV or fallback changes must be edited in two places and can drift (Step 5 vs ship-pr RCC). Extract shared emit-from-KV helper in `lib-failed-agent-stderr-tail.sh` and call from both sites.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: Recovery waterfall failure gating split across branches
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Recovery waterfall uses two separate revert/continue blocks for `tier_rc` vs `launcher_exit`/tail. Harder to see that surfacing runs once before all failure exits; slightly higher risk of editing one branch only. Merge failure conditions into one revert/continue after `_surface_ci_stderr_tail`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: Repeated awk parsing in `run_lint_fix_loop_capture`
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `run_lint_fix_loop_capture` repeats awk parsing of tail KVs. Minor maintenance noise when extending lint-fix stdout contract. Parse `STDERR_TAIL_PATH` and `CODER_LOG_FILE` once into locals after subshell capture.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: `step5_surface_lint_stderr_tail` on lint-fix-attempt-cap success path
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: `step5_surface_lint_stderr_tail` is called on lint-fix-attempt-cap after `applied` status (e.g. `review-implement-step5-loop.sh` ~268–277). Misleading call site; usually a no-op because `STDERR_TAIL_PATH` is unset, but it suggests failure surfacing on a success-shaped terminal path. Harmless when last `LINT_FIX_STATUS` is `applied`; no wrong tail emitted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Restrict `step5_surface_lint_stderr_tail` to failure terminal arms only.
  - From cursor-specialist-correctness-output.txt: Optional comment only; no code change required.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

