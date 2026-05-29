Normalized aggregator output from the supplied reviewer findings (merged by shared behavioral risk; severity = max across sources).

### FINDING_1: Gate A optional-trailer guard omits EMIT_PLAN before Step 2b.5
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: Gate A’s optional-trailer guard ends with dedup then Step 2b.5 without `ACTION=EMIT_PLAN`. After a discussion rewrite, an executor can run `check-plan-size` on `plan.txt` while `diff-lines.txt` stays stale, breaking implement handoff and logs. The Gate A guard should match the approval-gates shared pipeline: snapshot → rewrite → dedup → `EMIT_PLAN` validator → Step 2b.5.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_2: Gate A snapshot vs dedup blocks legitimate trailer value recompute
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: SKILL prose allows preserving snapshotted keys and values or recomputing estimates, and the waterfall path can preserve keys with new values, but `gate-b-dedup-plan.sh --dedup` rejects value changes after snapshot. Gate A snapshots optional trailer values before a discussion rewrite; a legitimate rewrite (e.g. `diff_added` 5000 → 800 after scope reduction) fails dedup with exit 1 and blocks Step 2b.5 despite docs permitting recompute. Recompute must happen in pre-snapshot Write, or the mechanical contract needs re-snapshot after Gate A rewrite, a dedicated recompute path that refreshes the values snapshot, and aligned updates to `SKILL.md` and `discussion-rounds.md`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_3: Redundant Bash 08/09 filter duplicates awk rules in check-plan-size
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Bash-side 08/09 rejection in `check-plan-size.sh` duplicates awk metadata-block rules. The duplicate path increases drift risk if awk rules change without updating Bash. Remove the redundant Bash filter or document it as defensive-only with awk as the single source of truth.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_4: Optional-trailer helper tests not registered in Makefile / CI
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Four optional-trailer test scripts are documented in `SKILL.md` but not wired into Makefile harness targets (including standalone `lib-plan-optional-trailers` unit scripts). Helpers can rot silently while CI stays green; awk/parser changes may break snapshot/validate behavior with only indirect detection via larger integration tests. Register a combined lib harness in the Makefile, merge cases into `test-gate-b-dedup-plan.sh` / `test-check-plan-size.sh`, or add a `test-trailer-helpers` target.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_5: Leading-zero and 08/09 trailer behavior under-documented for designers
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Leading-zero and 08/09 trailer handling extends beyond strict digit grammar in plan prose. Plans with `diff_added: 002001` or `diff_added: 08` may behave differently than designers expect from Step 2b. Document normalized decimal rules in Step 2b and `flags.md` designer guidance.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_6: Discussion-rounds vs Gate A ambiguous optional-trailer enforcement
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Discussion rounds use a prompt-side keys-only guard while Gate A adds mechanical keys+values `gate-b-dedup`. The same Gate A rewrite path has ambiguous enforcement; operators may skip mechanical dedup. Make `gate-b-dedup-plan.sh` the mechanical authority in `discussion-rounds.md` and cross-link `approval-gates`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] lib-plan-optional-trailers repeated plan reads per helper
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Each helper re-reads the plan file for `trailer_nr` before awk. Extra I/O on large plans during validation loops. Pre-existing; cache `trailer_nr` within a single validation call if optimizing later.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] plan-review-loop uses three awk passes for advisory fields
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Three awk passes parse `size_out` for advisory fields. Minor inefficiency only; combine into one awk block in a future cleanup.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_9: Committed test-doosc-debug.sh not in CI despite SKILL.md listing
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Debug-only `test-doosc-debug.sh` is committed and listed in `SKILL.md` as an optional-trailer harness but not registered in Makefile/CI. Maintainers may rely on a non-regression debug filter; CI gives false confidence while the DOOSC debugging artifact ships in the plugin. Remove or relocate the script, drop it from the `SKILL.md` helper list, and keep coverage in `test-plan-review-loop.sh` only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_10: test-design-structure.sh missing grep pins for gate-b-dedup hooks in SKILL.md
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `test-design-structure.sh` does not pin `gate-b-dedup-plan.sh` snapshot/dedup hooks in `SKILL.md` despite plan acceptance requiring Gate A/B structural pins there. `SKILL.md` Gate A/B optional-trailer guards could be deleted; `test-gate-b-dedup-plan.sh` and reference docs still pass while live `/design` runs lose trailer preservation. Add grep pins for `gate-b-dedup-plan.sh --snapshot-trailers` and `--dedup` in `SKILL.md` (and `discussion-rounds.md` if desired).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_11: [OUT_OF_SCOPE] discussion-rounds.md omits gate-b-dedup-plan.sh mechanical authority
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `discussion-rounds.md` describes prompt-side trailer guards without naming `gate-b-dedup-plan.sh`, unlike `SKILL.md` / `approval-gates.md`. Operators following discussion-rounds only might skip the mechanical snapshot helper. Align `discussion-rounds.md` with `gate-b-dedup-plan.sh` when touching that file (separate change).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_12: Optional trailers enable diff-gating downgrade without independent verification
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: New optional trailers let the plan author downgrade diff hard gating without external verification. An agent can write understated `diff_added` or `mechanical_churn:true` on a multi-thousand-line plan; Step 2b.5 and `plan-review-loop` proceed without Split/Cancel though legacy total churn would have hard-blocked. Treat as an explicit operator-accepted trust boundary, or add independent measurement / retain hard prompt when `diff_lines` exceeds the legacy threshold.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_13: Waterfall acceptance preserves trailer keys but not values
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Waterfall acceptance validates optional trailer keys only; the dedup path validates keys and values. A revision can keep `diff_added:` / `mechanical_churn:` lines but change values; the candidate is accepted and gate outcomes change without restoration that dedup would trigger. This is risky if downstream `gate-b-dedup` or `plan-review-loop` value validation is skipped. Call `validate_optional_trailers_preserved` after apply in unified-diff and file-replacement paths (consistent with `lib-plan-optional-trailers.sh` dedup helper), or require value-validating dedup on every waterfall exit before `EMIT_PLAN`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_14: [OUT_OF_SCOPE] check-plan-size --plan-file not constrained to design tmpdir
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `--plan-file` is not restricted to the design tmpdir. Orchestrator misconfiguration could point the size check at an arbitrary local file (read-only). Constrain `plan-file` to `DESIGN_TMPDIR/plan.txt` or a resolved path under a validated tmpdir if multi-tenant risk matters.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_15: [OUT_OF_SCOPE] LARCH_DEDUP_PLAN_LINES_PY enables hostile dedup script injection
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `LARCH_DEDUP_PLAN_LINES_PY` selects the dedup script path. Hostile env injection could run attacker-chosen Python as the invoking user during dedup. Document trusted-env requirement; ignore in single-user dev plugin context.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_16: awk treats diff_added/diff_deleted 08/09 lines as metadata terminator
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: In `lib-plan-optional-trailers.awk`, `diff_added` / `diff_deleted` lines matching 08/09 terminate the metadata scan instead of being skipped. A plan with `diff_added: 100`, `diff_deleted: 5000`, `diff_added: 08`, `diff_lines: 5100` ignores the real addition count and can hard-trigger on legacy `diff_lines > 1500`, undoing deletion-heavy relief. On 08/09 regex matches, use `continue` not `break`; add a sandwiched-metadata regression in `test-check-plan-size.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_17: Empty snapshot forbids first-time optional trailer introduction after revision
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: An empty snapshot forbids any new optional trailers after revision. A legacy plan revised to first emit `mechanical_churn` / `diff_added` for relief fails preservation until the operator pre-seeds trailers before rewrite. Document as policy or relax the empty-snapshot rule to allow intentional first-time trailer introduction.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_18: Empty keys_file skips pre-dedup restore on validation failure
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: An empty `keys_file` skips pre-dedup restore on validation failure. On a rare dedup path, `plan.txt` can remain deduped with spurious trailers when validation fails and `keys_file` was empty. Always snapshot the plan before dedup `mv`, or restore from dedup input on any validation failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
