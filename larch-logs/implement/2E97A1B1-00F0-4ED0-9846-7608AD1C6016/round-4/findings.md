Here is the normalized structured finding list (merged by shared behavioral risk; distinct fixes kept separate; `[OUT_OF_SCOPE]` preserved on merged out-of-scope items).

```text
### FINDING_1: Empty-merge attestation stricter than plan and short summaries
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: Zero structured `### FINDING_` blocks still require `LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED` in raw vendor output when the input had findings, so models, automation, or operators guided only by a one-line “return 0 on zero blocks” / unconditional clean-pass reading can hit `validation-failed` without the token; this is a breaking model- and operator-facing contract versus looser issue/plan wording and needs explicit acceptance, bundle/deploy pairing of prompt + script, and aligned issue/CHANGELOG/SECURITY messaging (including older cached prompts that lack the token).
- **Suggested revision**: Reconcile canonical plan/issue text with the attestation gate, or deliberately relax the validator only if product/security owners reject the stricter contract; in all cases align external summaries and operator docs with the enforced behavior.

### FINDING_2: Symmetric `normalize_slot` on input and output
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-symmetric-slot-normalization-output.txt
- **Concern**: Applying the same trailing-parenthetical stripping to input tokens and merge output collapses reviewer labels that differ only inside `(...)`, conflating membership checks, attribution, and `oos_only_slots` logic (including the case where an OOS-only suffixed label can collapse with a different in-scope base label); the same regex can also strip legitimate slot strings that end in parenthetical suffixes. This may contradict a written “normalize merge output only, keep input literal” plan unless that plan is updated to explicitly bless symmetric collapse as the shipped contract.
- **Suggested revision**: Confirm intended semantics with stakeholders; either document symmetric collapse as authoritative (and accept the broader matching) or narrow normalization (e.g., output-only / stricter canonical slot rules / feature flag) to preserve distinct reviewer identities where required.

### FINDING_3: Post-validation attestation strip masks `python3` failures (`|| true`)
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-protocol-cross-file-output.txt, dyn-symmetric-slot-normalization-output.txt
- **Concern**: The strip pipeline uses `python3 … || true` under `set -e`, swallowing non-zero exits and partial writes; combined with the zero-block newline salvage, an empty or truncated `merged_tmp` can become a single newline, pass size checks, and `mv` over `findings.md` with success reason—dropping narrative that already passed validation or persisting truncated merged output—undermining fail-closed staging and atomic replace expectations.
- **Suggested revision**: Remove unconditional success masking; propagate strip failure as `validation-failed` (or dedicated logging), preserve `findings.md` unchanged on failure, and only run the newline fallback after a confirmed successful strip (or add explicit content/size parity checks before `mv`); improve diagnostics so “staged merge output empty” distinguishes strip failures from other causes.

### FINDING_4: Duplicated empty-merge attestation string literals
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: The `EMPTY_MERGE_ATTESTATION` token is duplicated across separate heredocs, risking future edits that update one copy and desynchronize validation vs strip behavior.
- **Suggested revision**: Centralize the token string in a single shell-visible definition consumed by both paths.

### FINDING_5: Misleading maintainer comment referencing wrong validator artifact
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: A comment points readers at `aggregate-validate.py` even though validation is an inline heredoc in this script, sending maintainers on a wrong trace when debugging validate vs strip.
- **Suggested revision**: Reword the comment to name the inline validator heredoc (or the real module path if refactored).

### FINDING_6: BOM-sensitive attestation line matching
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Attestation detection compares stripped lines to the exact token without stripping a leading UTF-8 BOM, so a BOM-prefixed attestation line can fail detection despite being semantically present.
- **Suggested revision**: Apply BOM-tolerant normalization (e.g., `line.lstrip("\ufeff").strip()`) consistently in both validator and stripper predicates.

### FINDING_7: Orchestrator prose vs mechanical validator rules for the attestation token
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-protocol-cross-file-output.txt
- **Concern**: `agents/orchestrator-aggregator.md` reads stricter than the script: it implies the token must be the final line and must not appear anywhere when `### FINDING_` blocks exist, while the validator appears to accept any full line whose trim equals the token for empty merges and only treats whole-line matches as co-present “spurious” attestation when blocks exist—so narrative after the token or inline substring mentions may diverge from operator expectations.
- **Suggested revision**: Pick one contract and align orchestrator wording, `aggregate-findings.md`, and the Python validator (either tighten validation to match the prompt or narrow the prompt to the exact implemented rule).

### FINDING_8: `SECURITY.md` omits spurious-attestation co-occurrence failure mode
- **Reviewer(s)**: dyn-protocol-cross-file-output.txt
- **Concern**: The new zero-output paragraph explains attestation and strip-before-persist but does not state that structured `### FINDING_` blocks plus a full-line empty-merge attestation line fail closed and leave the ballot unchanged.
- **Suggested revision**: Extend the same `SECURITY.md` discussion with the paired “blocks + attestation line” rejection behavior to match code, tests, and orchestrator intent.

### FINDING_9: [OUT_OF_SCOPE] Operator doc gap for spurious attestation in `aggregate-findings.md`
- **Reviewer(s)**: dyn-protocol-cross-file-output.txt
- **Concern**: Like `SECURITY.md`, shipped operator contract text documents empty-merge attestation and stripping but not the symmetric rule that merged output containing structured findings blocks together with a full-line attestation line is rejected—doc alignment only, not runtime logic.
- **Suggested revision**: Mirror whichever finalized cross-file contract you choose (same as FINDING_7/FINDING_8) in `aggregate-findings.md` for operator clarity.

### FINDING_10: [OUT_OF_SCOPE] Orthogonal `larch-logs/implement/` run metadata on the branch
- **Reviewer(s)**: dyn-protocol-cross-file-output.txt, dyn-symmetric-slot-normalization-output.txt
- **Concern**: The branch adds committed implement run artifacts under `larch-logs/implement/…`, which is orthogonal to aggregator attestation correctness and mostly affects repo hygiene/review noise.
- **Suggested revision**: Treat as separate hygiene/release process decision (keep, relocate, or trim per run-log policy) independent of aggregator fixes.

### FINDING_11: [OUT_OF_SCOPE] Embedded Python definition order readability (`normalize_slot` vs `oos_attributed_slots`)
- **Reviewer(s)**: dyn-symmetric-slot-normalization-output.txt
- **Concern**: `normalize_slot` is defined after `oos_attributed_slots` but late binding avoids a runtime ordering bug; the layout can confuse readers during refactors.
- **Suggested revision**: Optional clarity-only reorder or comment—no functional defect identified.

### FINDING_12: [OUT_OF_SCOPE] Review noise from enumerating recent commits on the branch
- **Reviewer(s)**: dyn-symmetric-slot-normalization-output.txt
- **Concern**: Reviewer commentary listing `git merge-base`..`HEAD` commits is diagnostic noise rather than an additional distinct defect class beyond the merged in-scope topics.
- **Suggested revision**: None required for product behavior; ignore or fold into PR description if useful.
```
