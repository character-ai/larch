### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/lint/lint_markdown_heading_fence_state.py
- **Concern**: Fence compliance must accept inline same-loop fence gating, not only helper import. Scenario: The plan requires importing or defining a fence-line-index helper for compliance, but production parsers already gate heading matches with inline fence state in the same splitlines loop (for example python/larch/review/voting.py:1501-1524 and python/larch/rendering/rendering.py:214-219) without calling _balanced_fence_line_indices. A helper-centric rule would false-positive compliant code across the python/**/*.py surface.
- **Proposed resolution**: Define compliance as same-function data flow: any splitlines iteration that matches a heading regex must skip fenced indices via a helper call, an index-not-in-fenced-lines guard, or an equivalent inline in_fence toggle updated on fence markers before the heading match.



### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/lint/lint_self_disarmable_gate.py
- **Concern**: Self-disarm detection must exempt authority-verified oversize_override suppression. Scenario: The plan tests require _size_trigger_assessment to stay compliant, but the lint rules only discuss model-authored metadata and never carve out the production path where check_plan_size_main passes trusted_oversize_override into _size_trigger_assessment (python/larch/design/plan_quality.py:674-758, 479). Naive matching on the oversize_override identifier in override_suppressed would flag the live operator-authorized override as self-disarm.
- **Proposed resolution**: Limit disarm detection to author-controlled OptionalMetadata field reads (meta.diff_added, meta.mechanical_churn, etc.) in trigger-suppression control flow, and explicitly exempt override_suppressed when its oversize_override argument is supplied from _trusted_oversize_override rather than parsed plan metadata.



### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: python/unreachable-branch-baseline.json
- **Concern**: Unreachable-branch baseline identity fields are still underspecified. Scenario: The plan lists stable file, qualified-symbol, structural occurrence, and normalized-condition keys but does not define how to compute normalized-condition or returned-value equivalence, or how occurrence is counted. Without pinning to the existing (file, qualified_symbol, occurrence) ratchet model used by lint_tempfile_dir.py and lint_lifecycle_prefix_literal.py, unrelated edits can churn or duplicate baseline rows and break shrink-only enforcement.
- **Proposed resolution**: Pin baseline rows to the established occurrence-counter pattern plus an AST-unparsed normalized condition string and a separate normalized return-expression key; document the exact tuple in docs/linting.md the same way other structural lints document baseline identity.



### FINDING_4:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: ARCHITECTURAL_INVARIANTS.md:23-25
- **Concern**: Plan explicitly omits the mechanical backing required by the new I-Commit-1 invariant. Scenario: The committed run-log path can continue writing tmpdir pointers while the repository claims a commit-time scan rejects them, so the adopted invariant is unenforced and its stated audit guarantee remains false
- **Proposed resolution**: Implement the commit-time staged-log scan and extend the existing run-log flush/redaction path to embed voted finding bodies, or do not add I-Commit-1 until that backing ships



### FINDING_5:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/design/plan_quality.py:452-479
- **Concern**: Trusted operator oversize override needs an explicit self-disarmable-gate carve-out. Scenario: The plan requires detecting author-controlled metadata that suppresses hard triggers, and OptionalMetadata includes oversize_override. _size_trigger_assessment sets override_suppressed from the oversize_override parameter, which production supplies via _trusted_oversize_override, not raw meta.oversize_override. A name-based or metadata-field scan would flag the live gate as self-disarming even though only authority-verified operator override can suppress SIZE_TRIGGER_FIRED. Tests alone do not define the lint contract.
- **Proposed resolution**: State the lint rule explicitly: flag suppression only when plan-meta fields such as meta.oversize_override feed the trigger decision without a trusted-authority check. Treat override_suppressed driven by _trusted_oversize_override or equivalent sidecar-verified input as compliant operator override, not model self-disarm.



### FINDING_6:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/review/voting.py:1500-1524
- **Concern**: Markdown fence compliance must accept inline same-loop fence guards. Scenario: The plan treats compliance as requiring a fence-line-index helper plus fenced-line gating. _validate_code_review_headers already gates re.match(r"^#{1,6}\s", line) with an inline in_fence toggle over splitlines(), which matches G-Md-3 intent but does not import or define an index helper. Under the written rule the lint would report a production violation and push a shrinking baseline or suppressions onto already-correct code.
- **Proposed resolution**: Extend the compliance rule to accept same-function fence-state guards that skip heading matches inside fenced regions, including inline toggles and index-set helpers. Add a positive test fixture for the voting.py pattern so implementers do not require _balanced_fence_line_indices at every call site.



