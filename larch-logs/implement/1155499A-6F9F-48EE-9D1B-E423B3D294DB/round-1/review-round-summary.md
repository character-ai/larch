# Review Round 1

- Mode: `diff`
- 6 accepted, 3 rejected (1 exonerated)

## Accepted Findings

### FINDING_1: Duplicated Step 3 / Gate C plan-summary Bash
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The same large-plan summary logic lives in two fenced Bash blocks (Step 3 and Gate C). That invites drift (headers, sentinels, threshold/outline/bold-note behavior), inconsistent operator UX between pre-voting and final approval, and weaker assurance because the snippets sit outside `lint-bash32` (`*.sh` / `*.inc.bash` only) and outside deferred `test-design-structure` anchors (#2702), so typos or reorder mistakes can ship green in CI and only show up in manual `/design`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Extract shared logic to one script or single canonical snippet with lint or caller-only wrappers


### FINDING_2: `LARCH_DESIGN_PLAN_SUMMARY_THRESHOLD` parsing (leading zeros / octal)
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, dyn-bash-portability-output.txt
- **Severity**: latent
- **Concern**: The digit-only `case` guard still admits strings like `00` or `0120`. Values such as `00` can be interpreted as octal zero in `[ "$_plan_lines" -gt "$_summary_threshold" ]`, skewing summary vs full-plan mode; values like `0120` are not normalized to decimal `120` and can be parsed as octal (e.g. 80), so the effective threshold can diverge silently from the documented “positive integer / default 120” contract. Invalid-env / plan matrices may not cover these pathological forms.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt: Address the concern above.
  - From dyn-bash-portability-output.txt: Extend the `case` list (e.g. add a `0[0-9]*)` arm that resets to `120`, ordered so it catches multi-digit all-zero and other leading-zero forms) and/or compare using an explicit decimal coercion such as `$((10#_summary_threshold))` inside a guarded assignment so operands are always base-10 integers; keep the existing empty/`0`/non-numeric fallbacks and document that leading-zero env values are normalized to the default.


### FINDING_4: `approval-gates.md` vs SKILL on Other + full plan (summary-only wording)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Normative text ties `cat` + re-prompt on Other + full-plan request to summary-only framing (Presentation / Gate C Opt-in / line ~826), while SKILL Step 4b describes unconditional Other + full-plan `cat`. Orchestrators stricter than SKILL might skip re-`cat` when the plan was already fully printed (non-summary path), diverging from SKILL.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_7: Plan AC6 vs SKILL ordering (header vs timing-ledger)
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Plan acceptance criterion 6 calls for the header immediately after the Step 3 breadcrumb, but the implementation prints after the timing-ledger per AC1 / SKILL; manual QA keyed only to AC6 could falsely flag ordering before the timing-ledger.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_8: Gate C `### Presentation` missing `DESIGN_TMPDIR` guard mirror
- **Reviewer(s)**: dyn-doc-consistency-output.txt
- **Severity**: nit
- **Concern**: Gate C `### Presentation` documents the `plan.txt` missing/empty outcome but not the first-branch `DESIGN_TMPDIR` invalid/absent guard and matching `**⚠ 4b: DESIGN_TMPDIR missing or invalid; cannot present final design plan**` string that the mechanical block in `skills/design/SKILL.md` implements, so the normative write-up is not a full mirror of the fenced guard ladder.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-doc-consistency-output.txt: Extend `### Presentation` with one sentence covering invalid/absent `DESIGN_TMPDIR` and the exact `**⚠ 4b: ...**` string, aligned with the Step 4b fence, before the `plan.txt` sentence.


### FINDING_9: `approval-gates.md` “Large-plan summary mode” reads Gate-C-centric
- **Reviewer(s)**: dyn-doc-consistency-output.txt
- **Severity**: latent
- **Concern**: The **Large-plan summary mode** paragraph describes the shared Bash block in terms of the Step 4b `SKILL.md` fence, while Step 3 uses the same `_summary_threshold`, strict `line_count > threshold`, outline cap, empty-outline fallback, and bold-note behavior at `## Plan Candidate for Review`; Step 3 prose mainly points at Gate C. Readers can misread approval-gates as Gate-C-only even though `docs/configuration-and-permissions.md` scopes the env var to both Step 3 and Gate C.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-doc-consistency-output.txt: Add an explicit clause under **Large-plan summary mode** that the same threshold, strict `line_count > threshold` rule, outline cap, empty-outline fallback, and bold-note behavior apply at Step 3’s `## Plan Candidate for Review` emit, or factor one short shared subsection both steps reference.


