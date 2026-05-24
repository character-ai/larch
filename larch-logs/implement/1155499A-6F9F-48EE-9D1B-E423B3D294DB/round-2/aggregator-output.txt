Here is the normalized aggregator output. In-scope clusters are merged by behavioral risk; `[OUT_OF_SCOPE]` sources are grouped into `### OOS_*` blocks only with other OOS-tagged inputs (never merged with in-scope `### FINDING_*`). Suggested-revision bullets are verbatim per slot; where a slot only said “Address the concern above,” that string is repeated.

---

### FINDING_1: `emit-design-plan-preview.sh` outline capture under `set -e` / `pipefail` can exit before empty-outline or `head -n 30` fallback
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Under `set -euo pipefail`, capturing `_outline` via `grep '^#{2,3} ' … | head` yields non-zero when there are no `^#{2,3} ` matches (`grep` exit 1) and/or SIGPIPE when `head` closes the pipe; the script can abort before the documented first-30-lines fallback and before sentinel/touch paths, so large headerless plans break Step 3 / Gate C preview and acceptance/docs that assume the fallback runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Append `|| true` to the pipeline or disable pipefail for that capture; keep empty-outline fallback.
  - From cursor-specialist-edge-cases-output.txt: Wrap grep in `(... || true)` or disable pipefail for that capture.

### FINDING_2: Step 3 chat order: timing-ledger vs acceptance “immediately after the Step 3 breadcrumb”
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: SKILL documents plan preview after the timing-ledger, while acceptance/checklist language treats the plan header as immediately after the Step 3 breadcrumb; literal QA or acceptance audits can fail despite SKILL’s ordering note unless acceptance or step order is aligned.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Reorder steps or rewrite acceptance to name the timing-ledger boundary as the anchor before the preview.

### FINDING_3: Plan / acceptance expect inlined fenced Bash; implementation centralizes behavior in `emit-design-plan-preview.sh`
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Issue/plan/AC text and “files to modify” narratives describe duplicated inline fenced blocks and a fixed file list; shipped behavior invokes a shared script, so mechanical/audit expectations (grep for fenced bodies, topology/script inventory, “no new scripts”) can false-negative or drift unless plan, acceptance, topology, or SKILL fences are reconciled with the script-backed path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Update issue acceptance or add one clarifying sentence that the mechanical contract is the script invocation.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Amend plan/acceptance to script-backed emit, or replace the thin fences with the plan’s inline Bash bodies.

### FINDING_4: Adjacent Step 3 fences both `source` `current-design-env.sh` (redundant SKILL text)
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Two adjacent Step 3 fences each source `current-design-env.sh`, adding noise; optional dedup with a one-line justification if the shell context is already shared.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_5: `CHANGELOG.md` taxonomy for the new `/design` bullet (`### Changed` vs `### Added`)
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: The new `/design` visibility line is filed under `### Changed`; reviewers note a possible preference for `### Added` or local convention—cosmetic only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_6: No harness coverage for `emit-design-plan-preview.sh` threshold / sentinel / summary vs full paths
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: New preview logic (threshold, sentinel, outline vs summary, edge cases) is not covered by a registered hermetic test next to peer design script tests; regressions may only show up in manual `/design` or field use.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_7: Unquoted or fragile `cat` / `$DESIGN_TMPDIR` examples in docs / SKILL
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: Gate C full-plan examples show `cat $DESIGN_TMPDIR/plan.txt`-style usage; a literal paste with spaces or glob characters in `DESIGN_TMPDIR` risks word-splitting or pathname expansion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Standardize on `cat -- "${DESIGN_TMPDIR}/plan.txt"` or Read-tool equivalent in both SKILL.md and approval-gates.md.

### FINDING_8: Gate C “Other” full-plan emission has no size bound (large `plan.txt` risk)
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Documented full-plan emission for Gate C Other has no byte cap; very large `plan.txt` can degrade chat/logging or increase accidental disclosure if secrets were pasted into the plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Document operator expectations and/or add optional byte-cap or pager-style guidance in a follow-up change.

### FINDING_9: Extremely long all-digit `LARCH_DESIGN_PLAN_SUMMARY_THRESHOLD` can exceed bash integer limits after digit-only normalization
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Rare env typo with an enormous digit-only string can exceed bash integer limits after normalization, producing hard failure instead of falling back to 120.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Clamp length or wrap arithmetic in a failure handler that resets to 120.

### FINDING_10: Plan / topology narrative vs new `skills/design/scripts/emit-design-plan-preview.sh`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Plan-style bullets claimed no new scripts / unchanged topology or omitted the script from “files to modify”; the branch adds `emit-design-plan-preview.sh`, so traceability and regeneration expectations can disagree until plan/topology/wording is updated.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: List the script in the plan surface or remove it per original plan.

### FINDING_11: `docs/configuration-and-permissions.md` vs issue #2683 wording on threshold semantics
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Docs describe leading-zero and base-10 coercion beyond the plan’s single `case` pattern; if the issue alone is treated as normative, docs and SKILL can drift from shipped semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Sync issue plan wording with the shipped env-var semantics or narrow docs to the original case rule.

### FINDING_12: Bash 3.2: `$((10#_t))` does not expand `_t`; breaks `normalize_summary_threshold` under `set -e`
- **Reviewer(s)**: dyn-bash-script-output.txt, dyn-bash-script-output.txt
- **Severity**: important
- **Concern**: `printf '%s' "$((10#_t))"` is invalid on bash 3.2: `10#_t` is parsed as a base-10 literal with digit characters `_t`, causing arithmetic evaluation error (“value too great for base”) and, with `set -e`, aborting the script whenever `normalize_summary_threshold` runs in `emit_plan_body`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-script-output.txt: Use base-10 coercion on the variable value, e.g. `printf '%s' "$((10#${_t}))"` (verified on bash 3.2), or assign to a safe numeric path without the broken token.
  - From dyn-bash-script-output.txt: Coerce the *value* of `_t`, e.g. `printf '%s' "$((10#${_t}))"` (or an equivalent safe integer path), after the `case` has restricted `_t` to digits-only.

### FINDING_13: `--design-tmpdir` parsing: `${2:?…}` aborts on empty second token before warning/`exit 0` paths
- **Reviewer(s)**: dyn-bash-script-output.txt, dyn-bash-script-output.txt
- **Severity**: important
- **Concern**: `design_tmpdir="${2:?--design-tmpdir requires a value}"` treats an empty value after the flag as fatal during expansion, so calls like `--design-tmpdir "$DESIGN_TMPDIR"` when `DESIGN_TMPDIR` is unset exit before branches that print `**⚠ 3:**` / `**⚠ 4b:**` and `exit 0`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-script-output.txt: Accept empty after `--design-tmpdir` (e.g. `design_tmpdir=${2-}` then `shift 2`) and rely on the existing `[[ -z "$design_tmpdir" || ! -d ... ]]` checks to emit the same warnings and exit 0 as the inlined SKILL behavior.
  - From dyn-bash-script-output.txt: Avoid `:?` on `$2` for this flag (e.g. assign `design_tmpdir=${2-}` and `shift 2`, then let the existing `[[ -z "$design_tmpdir" || ! -d "$design_tmpdir" ]]` branches print the warning and exit 0).

### FINDING_14: Branch adds a full `larch-logs/implement/…` tree unrelated to `/design` preview behavior (PR scope / history bloat)
- **Reviewer(s)**: dyn-skill-invocation-output.txt
- **Severity**: important
- **Concern**: The branch adds a full `/implement` run tree (`manifest.json`, tally, large `plan-goals-test.md`, etc.), bloating history and mixing session telemetry with the feature; risk of confusing curated vs incidental run logs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-skill-invocation-output.txt: Remove these paths from the PR (or relocate only what `docs/run-logs.md` explicitly requires) so the change set is limited to `skills/design/*`, `docs/configuration-and-permissions.md`, and `CHANGELOG.md`.

### FINDING_15: `approval-gates.md` “Presentation” MUST vs missing/empty `plan.txt` warning-only path
- **Reviewer(s)**: dyn-skill-invocation-output.txt
- **Severity**: important
- **Concern**: `### Presentation` states the executor MUST emit `plan.txt` under `## Final Design Plan`, while the same material documents a path that prints only `**⚠ 4b: plan.txt missing or empty...**` and continues—a literal MUST read contradicts the exception path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-skill-invocation-output.txt: Reword so the obligation is on running the preview block and emitting the header **when** `plan.txt` is present and non-empty, with the warning-only path explicitly labeled as the defined exception.

### FINDING_16: `plan-goals-test.md` fenced snippets vs `normalize_summary_threshold` / docs (leading-zero / base-10)
- **Reviewer(s)**: dyn-threshold-divergence-output.txt
- **Severity**: important
- **Concern**: Flushed artifact still shows older inline fenced Bash (simple `case` before `-gt`) that does not reject leading-zero all-digit values the way `emit-design-plan-preview.sh` does, so `0120`-style values can behave differently (e.g. octal interpretation in comparisons); prose in that file can mis-document canonical behavior vs `docs/configuration-and-permissions.md` and the script.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-threshold-divergence-output.txt: Update those fenced blocks (or replace them with “invoke `emit-design-plan-preview.sh` …”) so they match `normalize_summary_threshold` in `emit-design-plan-preview.sh`, or add a clear note that the snippet is historical and non-normative while the script is authoritative.

---

### OOS_1: [OUT_OF_SCOPE] Implement run-log noise in branch diff (review scope / no product action)
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-script-output.txt
- **Severity**: latent
- **Concern**: `larch-logs/implement/1155499A-6F9F-48EE-9D1B-E423B3D294DB/*` (and related flush) appears in the diff; reviewers flag it as excluded run-log scope, routine policy, or operational noise—not correctness of the preview feature itself.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-bash-script-output.txt: Out-of-scope: larch-logs flush / large plan-goals-test.md in diff — operational noise, not correctness of the feature logic.

### OOS_2: [OUT_OF_SCOPE] Scout confirmations / non-issues (executable bit, env contract, gate/header, threshold docs, runtime path)
- **Reviewer(s)**: dyn-bash-script-output.txt, dyn-skill-invocation-output.txt, dyn-skill-invocation-output.txt, dyn-skill-invocation-output.txt, dyn-skill-invocationAggregating the supplied reviewer findings: merging duplicates, preserving verbatim suggested revisions where they differ, and separating `[OUT_OF_SCOPE]` items into `### OOS_N:` blocks with required severity lines.


