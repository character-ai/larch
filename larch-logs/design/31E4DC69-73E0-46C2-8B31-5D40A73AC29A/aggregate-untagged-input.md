### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/issue/learn_from_bugs.py
- **Concern**: The plan adds `introduced by PR #N` extraction but keeps `origin.ref` as a bare integer and renders every referenced chain as `#<origin> -> #<current>`.. Scenario: `introduced by PR #123` stores `ref=123` and the headline emits `#123 -> #6672` even though 123 is a PR number, not a causal issue. That misstates the regression chain the feature is meant to surface.
- **Proposed resolution**: Add a `ref_kind` (`issue` vs `pr`) or equivalent to `Origin`, render `#origin -> #current` chains only for issue refs, and either omit PR refs from chains or render an explicit `PR #N -> #current` form; extend headline and marker tests to cover PR-only markers.

### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: minor
- **Focus area**: correctness
- **Location**: skills/learn-from-bugs/SKILL.md:151-153
- **Concern**: The report-contract validation plan does not enforce the required single-sourcing class fix for duplicated-contract clusters. Scenario: A prompt-generated report can mention parallel parsers or copied field names, omit single-sourcing, and still pass the planned validator before printing or filing
- **Proposed resolution**: Extend the deterministic report contract and fixture coverage to reject duplicated-contract clusters that lack an explicit single-sourcing class fix

### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/issue/learn_from_bugs.py
- **Concern**: PR-derived refs render as issue chains. Scenario: The plan stores PR numbers in origin.ref and renders every referenced regression as #<origin> -> #<current>. An introduced by PR #5630 marker can emit #5630 -> #6672 even when 5630 is a PR, not an issue, misstating causality in the headline and failing acceptance-criterion chain semantics.
- **Proposed resolution**: Omit PR-sourced refs from chain lines (still count them in regression totals), or add an explicit ref kind and render PR chains as PR #N -> #<current>.

### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/learn-from-bugs/SKILL.md:38-67
- **Concern**: --zones-only path never forwards the resolved query. Scenario: Step 2 only passes --search when SEARCH_EXPLICIT=true. The plan routes zone output through RESOLVED_SEARCH/SEARCH_ARGS but never requires SEARCH_EXPLICIT=true for a --zones-only invocation. prepare then keeps DEFAULT_SEARCH [BUG] in:title and ignores the zone query.
- **Proposed resolution**: Add an explicit Step 1 --zones branch that sets SEARCH_EXPLICIT=true and RESOLVED_SEARCH from the zone CLI; pin that wiring in scripts/test-learn-from-bugs-structure.sh.

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/learn-from-bugs/SKILL.md:97-98
- **Concern**: Section 2 intro conflicts with first-block headline contract. Scenario: The current Section 2 template keeps Each recurring pattern, its member issues... on the same line as the heading. validate_report_contract requires the generated headline as the first content block in Section 2 before cluster rows. Implementations can place the headline after that intro and fail validation, or drop the intro without plan authority.
- **Proposed resolution**: Define one Section 2 layout: headline immediately after the section heading (relocate or remove the intro sentence), and make the validator and structural harness pin that exact order.

### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: skills/learn-from-bugs/SKILL.md:90-106
- **Concern**: Report-contract CLI argv contract is unspecified. Scenario: Step 4 must call validation before print/marker/filing, but the plan registers a validation entry point without subcommand name, required flags (--report, --headline, exit codes), or a Step 4 Bash fence. Wiring can drift or omit the prepared headline comparison.
- **Proposed resolution**: Specify the cli.py subcommand, argv/stdout contract, non-zero failure behavior, and the exact Step 4 fence that passes ORIGIN_HEADLINE_PATH plus ${RUN_DIR}/report.md. ### 1. [correctness] PR-derived refs render as issue chains (`python/larch/issue/learn_from_bugs.py`) The plan treats `introduced by PR #N` like issue markers and renders `#<ref> -> #<current>`. PR numbers are not issue numbers, so chains can cite the wrong artifact. Minimum fix: omit PR-sourced refs from chain lines (same as bare regressions) while still counting them in regression totals. ### 2. [correctness] `--zones`-only path never forwards the resolved query (`skills/learn-from-bugs/SKILL.md:38-67`) Existing Step 2 only adds `--search` when `SEARCH_EXPLICIT=true`. A zones-only run that sets `RESOLVED_SEARCH` but not `SEARCH_EXPLICIT` will still call prepare with the default `[BUG] in:title` query. The plan needs an explicit zones branch that sets both values. ### 3. [correctness] Section 2 intro conflicts with first-block headline contract (`skills/learn-from-bugs/SKILL.md:97-98`) The validator requires the prepared headline as Section 2’s first content block, but the current template puts descriptive intro prose on the section line before any cluster rows. Pick one layout and pin it in SKILL.md, the validator, and the structural harness. ### 4. [risk-integration] Report-contract CLI argv contract is unspecified (`skills/learn-from-bugs/SKILL.md`, `python/larch/cli.py`) Step 4 depends on a validation CLI that the plan never names or wires. Without subcommand name, required paths, and failure semantics, the deterministic contract check can be skipped or implemented inconsistently.

### FINDING_7:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/learn-from-bugs/SKILL.md:93-110
- **Concern**: Step 4 does not specify an executable invocation and result check for the planned report-contract validator. Scenario: The prompt can require validation in prose, but an implementation may print the report, write the durable marker, or start filing without ever invoking the validator. The required headline and prose-only contract then remain unenforced on the feature path
- **Proposed resolution**: Add the exact `python3 ... learn-from-bugs validate-report` command, its required inputs, whole-line result grammar, nonzero failure handling, and place it after report generation but before printing, marker persistence, or filing

### FINDING_8:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/issue/learn_from_bugs.py:validate_report_contract
- **Concern**: Validation only of present prose-only markers cannot enforce the requirement that guideline-only residuals receive the marker. Scenario: A model can omit `prose-only prevention: unlikely to stick` from a guideline-only cluster and still pass a validator that checks citations and mechanical alternatives only when the marker exists, so the required warning is silently missing
- **Proposed resolution**: Pass the validator enough expected residual metadata to identify guideline-only clusters, or add a deterministic per-cluster residual-kind marker and reject any guideline-only cluster lacking the exact warning, citations, and mechanical-alternative line

### FINDING_9:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/issue/learn_from_bugs.py
- **Concern**: PR reference markers still render as issue-number regression chains. Scenario: The plan requires `introduced by PR #N` extraction and `#<origin> -> #<current>` chain rendering, but `origin.ref` is only an integer with no PR-vs-issue discriminator, so `introduced by PR #123` will emit `#123 -> #<bug>` as if 123 were a causal issue
- **Proposed resolution**: Pin chain behavior in the plan and tests: add `ref_kind` (`issue|pr`) and render PR chains as `PR #N -> #<current>`, or keep PR classification but omit PR-sourced refs from `#X -> #Y` chains while still counting them in the regression ratio

### FINDING_10:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/issue/learn_from_bugs.py:proposed validate_report_contract
- **Concern**: [ALREADY_ADDRESSED] The prior fix remains incomplete because validation checks only prose-only markers that already exist and cannot detect a missing marker. Scenario: A report can place a guideline as a cluster's only residual proposal, omit the required warning entirely, and still pass validation. This violates acceptance criterion 2 and leaves the required report fixture unable to verify the omission path
- **Proposed resolution**: Add a narrow check that identifies guideline-only residual clusters from a small explicit report grammar and requires the marker and mechanical-alternative line. Add the mandated fixture where a guideline-only cluster without the marker fails validation

### FINDING_11:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/issue/learn_from_bugs.py:302-321
- **Concern**: The planned origin helper relies on _split_sections(), which overwrites repeated headings instead of preserving all root-cause bodies in document order. Scenario: An issue with two Root Cause sections loses the first section. A marker in that first section is missed, so the digest becomes unknown or uses a later marker despite the plan's all-root-cause and first-in-document-order contracts
- **Proposed resolution**: Add a minimal origin-specific ordered section iterator, or adjust section parsing to preserve repeated headings, then test a marker in the first of two root-cause sections

### FINDING_12:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/issue/learn_from_bugs.py
- **Concern**: PR-introduced markers still render as issue chains. Scenario: The plan extracts `introduced by PR #N` into the same `origin.ref` integer shape as issue markers and `render_origin_headline()` always emits `#<ref> -> #<current>`. A digest whose only referenced marker is PR-based will still print a causal chain that reads like an issue link (for example `#42 -> #9001`) even though 42 is a PR number. That misstates causality and breaks the headline contract operators use to follow residuals.
- **Proposed resolution**: Keep PR markers as `kind=regression`, but either add a `ref_kind` (`issue|pr`) and render PR chains as `PR #<ref> -> #<current>` (or omit PR refs from the chain list while still counting them in regression totals), and add a unit/headline fixture for `introduced by PR #N` so the chain grammar is pinned. **1. correctness — `python/larch/issue/learn_from_bugs.py`** The plan still conflates PR numbers and issue numbers in regression chains. It documents `introduced by PR #N` extraction, stores the captured number in `origin.ref`, and requires chains formatted as `#<origin> -> #<current>`. PR and issue references share one integer field with no rendering rule, so PR-sourced digests produce false issue-causality chains. Extend the `Origin` shape or chain renderer to distinguish PR refs (or exclude them from chains), and add the matching headline fixture called out in the testing section.

### FINDING_13:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/issue/learn_from_bugs.py:302-321
- **Concern**: Prior origin-allowlist fix remains incomplete because `_split_sections()` returns a dictionary and overwrites repeated headings. Scenario: The plan requires scanning all root-cause sections in document order, but two sections with the same normalized heading retain only the last body. A marker in an earlier repeated root-cause section is lost, producing the wrong origin classification and headline counts.
- **Proposed resolution**: Add an ordered, unsqueezed section iterator or extend the splitter to preserve duplicate sections, then classify every allowed root-cause body in document order.

### FINDING_14:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: python/larch/issue/learn_from_bugs.py
- **Concern**: The proposed prose-only validator succeeds vacuously when the required marker is omitted. Scenario: The validator checks citations and the mechanical-alternative line only for markers already present. A report can omit `prose-only prevention: unlikely to stick` from a guideline-only cluster, pass validation, and violate required design item 3 and acceptance criterion 2.
- **Proposed resolution**: Make validation detect guideline-only residual clusters and require the marker and alternative line, or add another deterministic artifact that identifies which clusters require the marker and validate the report against it.
