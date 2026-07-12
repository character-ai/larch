### FINDING_1: correctness: python/larch/issue/learn_from_bugs.py:89-92
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [major] _SECTION2_HEADING_RE matches any heading containing root-cause clusters so _section2_body can start at an earlier subsection. Section 1 heading ### Prior root-cause clusters review appears before Section 2; validate-report rejects a report whose generated headline is correctly placed under 2. **Root-cause clusters.** Anchor Section 2 with a strict numbered heading pattern or locate Section 2 relative to the Scope section instead of substring-matching any heading.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_2: correctness: python/larch/issue/learn_from_bugs.py:591-603
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [major] Prose-only validation uses only a fixed 400/800 character window around each marker. A compliant long guideline entry places #6746/#6747 or the mechanical-alternative line more than 800 characters after the marker; validate-report fails despite meeting the Step 4 contract. Expand validation to the enclosing proposal or Section 6 block, not a fixed character window.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_4: [OUT_OF_SCOPE] correctness: python/larch/issue/learn_from_bugs.py:79
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [minor] Bare regression regex matches non-regression wording. Root cause says this was a non-regression change; origin becomes regression and skews the headline ratio. Tighten bare-regression detection (e.g. negative lookbehind or phrase list) if precision matters.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=1 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_5: [OUT_OF_SCOPE] correctness: python/tests/issue/test_learn_from_bugs.py
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [minor] Plan-listed tests for missing denominator/ratio rejection are absent. Verifier behavior is only covered indirectly via verbatim headline tests. Add negative fixtures if separate denominator/ratio checks are desired beyond verbatim match.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false

### FINDING_6: [OUT_OF_SCOPE] risk-integration: skills/learn-from-bugs/SKILL.md:64-66
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [minor] Explicit --search path does not document binding RESOLVED_SEARCH before SEARCH_ARGS. Orchestrator may pass empty --search when only --search was intended. Bind RESOLVED_SEARCH to the explicit query in Step 1 (pre-existing).
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_7: correctness: python/larch/issue/learn_from_bugs.py:476-508,862-887
- **Reviewer**: codex-specialist-correctness-output.txt
- **Concern**: [major] Zone values can inject newlines into the RESOLVED_SEARCH wire output. --zones $'design\nimplement' produces a multiline result; Step 1 parses only the first whole line and silently searches only for design. Reject carriage returns and newlines in zone names or escape them through the audited wire-value helper before emitting RESOLVED_SEARCH.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_8: correctness: python/larch/issue/learn_from_bugs.py:585-604
- **Reviewer**: codex-specialist-correctness-output.txt
- **Concern**: [major] The prose-only validator associates evidence using a broad character window rather than the containing proposal or cluster. A marker lacking citations and a mechanical alternative passes when a nearby later cluster supplies #6746, #6747, and a lint or hook name within the window. Parse proposal or cluster boundaries and validate each marker against its own containing block.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_9: [OUT_OF_SCOPE] code-quality: python/larch/issue/learn_from_bugs.py:616-636
- **Reviewer**: codex-specialist-correctness-output.txt
- **Concern**: [minor] Malformed issue numbers become zero in digest records. A malformed row can produce a misleading chain such as #100 -> #0; this behavior predates the branch feature. Fail closed or record an unusable digest if malformed issue rows must not enter origin reporting.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false

### FINDING_11: security: python/larch/issue/learn_from_bugs.py:489-494
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [minor] Zone names are embedded into gh search syntax without grammar validation or escaping. A zone containing ) or OR can break the OR group and broaden search beyond intended zones. Allowlist zone tokens or escape each name before building the OR-group query.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=1 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_12: correctness: python/larch/issue/learn_from_bugs.py:85-88,599-602
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [minor] Prose-only mechanical-alt validation accepts any incidental lint/hook/invariant word in the window. validate-report can pass with vague prose that cites #6746/#6747 but names no real mechanical alternative. Require an explicit alternative line pattern instead of a bare keyword match.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_13: correctness: python/larch/issue/learn_from_bugs.py:365-385,407-414
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [minor] Origin extraction scans fenced code inside root-cause sections. Markers inside code fences can false-classify regressions and skew chains/ratio. Exclude fenced-code ranges from origin source text like fenced headings are excluded.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_14: [OUT_OF_SCOPE] correctness: python/larch/issue/learn_from_bugs.py:467-468
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [minor] Bare regression regex matches ordinary regression-test phrasing. Best-effort origin stats over-count regression; documented heuristic tradeoff. Narrow the bare-regression pattern or require residual/regressed context if precision matters later.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_15: [OUT_OF_SCOPE] risk-integration: skills/learn-from-bugs/SKILL.md:71-78
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [minor] Step 2 does not require prepare exit 0 before KV parsing. Pre-existing orchestration gap; prepare failure may still be mishandled prompt-side. Check prepare rc and abort before reading DIGEST_PATH or ORIGIN_HEADLINE_PATH.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false

### FINDING_16: [OUT_OF_SCOPE] architecture: python/larch/issue/learn_from_bugs.py:607-613
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [minor] Report validator does not enforce cluster-level single-sourcing or guideline-only rules. Cluster contract drift is possible even when headline/prose-only checks pass. Extend validator only if mechanical enforcement of those cluster rules is desired.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_18: correctness: python/larch/issue/learn_from_bugs.py:585-603
- **Reviewer**: codex-specialist-edge-cases-output.txt
- **Concern**: [major] Prose-only validation uses a broad surrounding window instead of the containing proposal block. Nearby clusters can supply the required citations and mechanical-alternative wording, so an invalid marked cluster passes the report gate. Parse cluster boundaries and validate each marker against only its own cluster or proposal block.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_19: risk-integration: python/larch/issue/learn_from_bugs.py:85-88
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [major] Prose-only validation accepts incidental lint/hook/invariant words instead of a named mechanical alternative. Acceptance criterion 2 can pass with #6746/#6747 citations plus vague prose, so guideline-only clusters evade the intended warning. Tighten _MECHANICAL_ALT_RE to require an explicit alternative line or no-mechanical-alternative phrase; add a negative pytest fixture.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_20: risk-integration: python/larch/issue/learn_from_bugs.py:880-902
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [minor] validate_report_main has no CLI smoke tests while Step 4 depends on it. Registry or argv wiring regressions would surface only at skill runtime, not in CI. Add pytest coverage for success KV, contract failure exit 2, and missing file paths.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_21: risk-integration: python/tests/issue/test_learn_from_bugs.py:1008-1068
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [minor] Plan-listed report-contract negatives for missing denominator or ratio are untested. A truncated or partial headline might pass if it remains a substring match. Add fixtures rejecting headlines without selected denominator or regression-ratio lines.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=1 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_22: risk-integration: python/larch/issue/learn_from_bugs.py:583-601
- **Reviewer**: codex-specialist-testing-output.txt
- **Concern**: [minor] The prose-only contract check uses a broad character window rather than a bounded proposal or cluster block. A malformed marked cluster can borrow required citations or a mechanical alternative from a neighboring cluster and pass validation. Parse cluster or proposal boundaries and require the marker, #6746, #6747, and the mechanical-alternative or explicit no-alternative statement within the same block; add an adjacent-cluster regression fixture.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_23: risk-integration: python/larch/issue/learn_from_bugs.py:729-747
- **Reviewer**: codex-specialist-testing-output.txt
- **Concern**: [minor] DIGEST_CHARS omits newline separators present in the generated digest.jsonl payload. For multiple selected issues, reported digest size differs from the payload supplied to the model. Compute the statistic from the exact serialized JSONL payload including separators and add a multi-record length assertion.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_24: **correctness** `python/larch/issue/learn_from_bugs.py:79-80,467-468` — `_BARE_REGRESSION_RE` (`\bregression\b`) false-positives on common negated and contextual phrasing in allowed origin sources. Substrings like `non-regression`, `not a regression`, and `regression test` all match, so root-cause text that explicitly denies a regression (or discusses regression tests) is classified as `kind="regression"` with `ref=None`. That inflates the regression count and regression-ratio headline. **Suggested fix:** Tighten bare-regression detection with negative lookbehind/ahead or explicit denylist patterns (for example `non-regression`, `not a regression`, `no regression`) before accepting `\bregression\b`, or require a positive residual cue (`regression of`, `regressed`, `reintroduced`) instead of any standalone token; add unit tests for those negated forms.
- **Reviewer**: dyn-dyn-origin-allowlist-output.txt
- **Concern**: - **correctness** `python/larch/issue/learn_from_bugs.py:79-80,467-468` — `_BARE_REGRESSION_RE` (`\bregression\b`) false-positives on common negated and contextual phrasing in allowed origin sources. Substrings like `non-regression`, `not a regression`, and `regression test` all match, so root-cause text that explicitly denies a regression (or discusses regression tests) is classified as `kind="regression"` with `ref=None`. That inflates the regression count and regression-ratio headline. **Suggested fix:** Tighten bare-regression detection with negative lookbehind/ahead or explicit denylist patterns (for example `non-regression`, `not a regression`, `no regression`) before accepting `\bregression\b`, or require a positive residual cue (`regression of`, `regressed`, `reintroduced`) instead of any standalone token; add unit tests for those negated forms.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false

### FINDING_25: [OUT_OF_SCOPE] **[OUT_OF_SCOPE]** `python/larch/issue/learn_from_bugs.py:413-414` — For `_title_only` digests (`prefix` shorter than `TITLE_ONLY_PREFIX_MAX`), `_origin_source_texts` scans only the normalized title and drops even a short diagnostic lead-in such as `persists after #N` before the plan boundary. That is plan-consistent, but it can leave referenced markers unclassified when the only signal is a brief pre-plan line rather than the title.
- **Reviewer**: dyn-dyn-origin-allowlist-output.txt
- **Concern**: - **[OUT_OF_SCOPE]** `python/larch/issue/learn_from_bugs.py:413-414` — For `_title_only` digests (`prefix` shorter than `TITLE_ONLY_PREFIX_MAX`), `_origin_source_texts` scans only the normalized title and drops even a short diagnostic lead-in such as `persists after #N` before the plan boundary. That is plan-consistent, but it can leave referenced markers unclassified when the only signal is a brief pre-plan line rather than the title.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false

### FINDING_26: [OUT_OF_SCOPE] **[OUT_OF_SCOPE]** `python/tests/issue/test_learn_from_bugs.py:932-939` — Negative allowlist coverage exists for `## Suggested fix(es)`, but not for the singular `## Suggested fix` heading also listed in `WANT_SECTIONS`; behavior should match, yet the gap leaves the allowlist contract unproven for that heading variant.
- **Reviewer**: dyn-dyn-origin-allowlist-output.txt
- **Concern**: - **[OUT_OF_SCOPE]** `python/tests/issue/test_learn_from_bugs.py:932-939` — Negative allowlist coverage exists for `## Suggested fix(es)`, but not for the singular `## Suggested fix` heading also listed in `WANT_SECTIONS`; behavior should match, yet the gap leaves the allowlist contract unproven for that heading variant.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false
