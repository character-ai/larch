Here is the normalized structured finding list. Duplicates about the same behavioral risk are merged; distinct fix paths stay separate. Out-of-scope items are listed after in-scope findings with preserved `[OUT_OF_SCOPE]` tags.

```text
### FINDING_1: Bash 3.2 incompatibility in OOS shared include
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: `declare -A` in `oos-disposition-shared.inc.bash` is Bash 4+; default macOS Bash 3.2 errors when the include is sourced, breaking the disposition gate and audit paths that depend on rejection counting. Static `lint-bash32` may not cover `*.inc.bash` if only `*.sh` is scanned, so the regression can slip past CI.
- **Suggested revision**: Replace associative-array deduping with Bash 3.2-safe counting (for example `sort -u` / `wc -l`), and/or extend `lint-bash32` globs to include dotted `.inc.bash` helpers; verify under Bash 3.2.

### FINDING_2: Inline-triage evidence matches substring, not documented rule tokens
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Concern**: Gate/audit logic counts lines containing the substring `Inline-triage rule` while policy/SKILL text describes `Inline-triage rule N:`-style linkage. Operators may follow the stricter mental model while the implementation uses a weaker heuristic; conversely, two unrelated mentions of the phrase can satisfy counts without real per-rule triage folds.
- **Suggested revision**: Either align NEVER/docs with the substring heuristic or tighten matching (for example `grep`/`awk` requiring the numeric rule token) and update tests accordingly.

### FINDING_3: Tests mutate git config inside TMPDIR repos
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: Test harnesses call `git config user.email` / `user.name`, writing config inside ephemeral repos; unnecessary use of the git config API for test setup.
- **Suggested revision**: Prefer `git -c user.email=… -c user.name=…` (or equivalent) for commits instead of `git config` writes.

### FINDING_4: Inline-triage hits double-counted across audit artifacts
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: `_audit_oos_inline_triage_hits` aggregates inline-triage counts from more than one artifact; duplicate lines across `codex-commit-message.txt` and `session-transcript.jsonl` can inflate `inline_count`, yielding audit pass skew versus what the gate would enforce on a single canonical source.
- **Suggested revision**: Deduplicate across sources or define a single canonical artifact and precedence rules in docs and implementation.

### FINDING_5: Gate counts lines, not occurrences of inline-triage markers
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: `grep -cF`-style line counting can undercount when multiple inline-triage rules appear on one commit body line relative to `non_sec` expectations, producing gate failure despite substantive inline triage text.
- **Suggested revision**: Count occurrences (not just lines), document the rule, and extend harness coverage.

### FINDING_6: Accepted-markdown path errors can zero out obligations and pass
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Wrong CSV paths or missing `oos-accepted` files can yield `non_sec=0` and an unconditional pass, silently clearing obligations while the OOS pipeline assumed those inputs existed.
- **Suggested revision**: Fail closed when disposition is active but expected accepted files are missing or unreadable, or validate paths before treating the obligation set as empty.

### FINDING_7: `jq` errors in rejected-marker counting can abort whole audit under `set -e`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: A corrupt `oos-issues.ndjson` line can cause `jq` failure that aborts `audit-scan-run.sh` mid-registry, preventing later scan emissions.
- **Suggested revision**: Isolate parsing for this scan (treat bad lines as skip/partial with explicit reporting) without failing the entire run.

### FINDING_8: Mixed PR scope hurts plan-to-diff traceability
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: The branch combines OOS disposition work with unrelated ship-pr token work, version/changelog bumps, and other non-OOS edits, so a reviewer using only the OOS plan cannot map requirements cleanly to the diff.
- **Suggested revision**: Split unrelated changes into another PR or expand the plan scope list to explicitly cover every shipped delta.

### FINDING_9: Plan edge-case story vs AWK “security” focus-area matching
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: Plan edge-case prose may imply broader “security” prose matching, while implementation intentionally honors dedicated `**focus-area**` list lines (with tests like `false-sec.md` encoding the stricter rule), creating plan-vs-code ambiguity.
- **Suggested revision**: Update plan edge-case text to match `oos-disposition-gate.md` and the AWK, or change the AWK if the looser match was actually required.

### FINDING_10: Plan gate contract omits `--oos-issues-ndjson`
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: Short gate contract bullets drift from NEVER #18 / actual wiring: the plan checklist omits `--oos-issues-ndjson` even though implementation already supports it.
- **Suggested revision**: Refresh the plan contract bullet for checklist parity with the real CLI surface.

### FINDING_11: [OUT_OF_SCOPE] `CALLER_KIND` rename in `scripts/test-ship-pr.sh`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: Treated as separate issue (e.g. 2539), not OOS gate scope; behavior consistent with SKILL Exit 5 / NEVER 15; no OOS-review change required.
- **Suggested revision**: None for this OOS review; track in the dedicated issue/PR if still desired.

### FINDING_12: [OUT_OF_SCOPE] Committed implement run logs under `larch-logs/implement/...`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: Intentional run-log flush per run-logs policy; chore noise unrelated to gate correctness.
- **Suggested revision**: None for this OOS review.

### FINDING_13: [OUT_OF_SCOPE] `.claude-plugin/plugin.json` version bump ships with feature PR
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: Release metadata only; not a gate-correctness defect for this review.
- **Suggested revision**: None for this OOS review.

### FINDING_14: [OUT_OF_SCOPE] `eval`-based dynamic reads in `audit-scan-run.sh`
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: Pre-existing CLI arg validation pattern; not introduced or widened by OOS scan wiring.
- **Suggested revision**: None required for this branch.

### FINDING_15: [OUT_OF_SCOPE] `SECURITY.md` not updated for security-routing heuristic
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Operators relying on `SECURITY.md` may miss how focus-area security routing interacts with OOS gating; no diff touch in scope.
- **Suggested revision**: Optional follow-up doc note if policy applies; not blocking this OOS review.
```
