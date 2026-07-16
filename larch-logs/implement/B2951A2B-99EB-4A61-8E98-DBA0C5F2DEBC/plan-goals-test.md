## Goal
Implement issue #7480: [IMPLEMENTING] contract-unification [DEDUP] Return typed open-issue rows from the GitHub layer.

## Implementation Plan
#### Problem

`issue/combine_issues.py` and `issue/deps_audit.py` exactly repeat JSON loading, positive-number parsing, JSON emission, `gh issue list` field selection, open-state filtering, and loose dictionary normalization. #7007 centralized the command wrapper but left each consumer to reconstruct the returned row contract.

#### Goal

Add a narrow frozen `OpenIssueRow` parser and an `open_issue_rows_read` owner in the GitHub or issue integration layer. Migrate the two exact consumers first. Preserve tolerant label/body normalization and existing error messages. Do not turn the generic GitHub wrapper into a broad domain model or migrate unrelated callers speculatively.

#### Required implementation

- Define a frozen row with positive `number`, string `title`, normalized lowercase `state`, tuple of label names, and string `body`. Keep optional fields lossless enough for both current consumers.
- Add one reader that calls the existing `gh.issue_list_read` wrapper with fields `number,title,state,labels,body` and the current large limit, validates row shapes, filters to open state, and returns an immutable sequence.
- Decide malformed-row behavior from current callers. Preserve skip versus fail policy explicitly and test it. Do not let `bool` pass as a positive integer.
- Migrate `combine_issues.py` and `deps_audit.py` to the typed rows. Remove their duplicated `_load_json_file`, `_positive_int_value`, and `_emit_json` only where the shared owner fully replaces them; retain unrelated file-input helpers if their contract differs.
- Preserve JSON output keys, ordering, exit codes, stderr diagnostics, and injected runner behavior.

#### Verification

Add owner tests for missing and malformed fields, numeric strings, booleans, zero/negative numbers, non-list labels, closed rows, duplicate rows, GitHub failure, and invalid JSON. Run focused combine/dependency audit suites and the raw-gh-wrapper lints.

#### Size and acceptance

Expected change: 400-700 lines with a net reduction. Tests must cover malformed rows, non-positive numbers, closed rows, missing optional fields, and runner failures. The duplicate helper trio must disappear from both consumers.

## Test plan
(no test plan section in plan-file)
