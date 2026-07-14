## Goal
Implement issue #7021: [IMPLEMENTING] contract-unification [FEATURE] 6988.3: Equivalence harness and synthetic golden fixtures.

## Implementation Plan
## Plan

## Approach

Build a test-only equivalence layer over the three legacy `scan_file()` APIs. Materialize each JSON case below `tmp_path` as a synthetic repository with detector sources under `repo_root/python/`, run the matching adapter, map legacy results to `larch.lint.engine.Finding`, then compare engine identity tuples and `render_finding()` lines.

Use `(path, line, rule_id, message)` as the identity, matching the engine’s dedupe and sort contract. Map each legacy detector path, which is relative to synthetic `python/`, to repository-relative POSIX `Finding.path` values prefixed with `python/`. Set `rule_id` from each detector’s `SUPPRESSION` constant. Preserve `qualified_symbol`; leave `metric` unset.

Export typed fixture models plus `load_equivalence_fixture()` and `assert_equivalent_findings()` for later detector port tests. Keep adapter dispatch in a registry keyed by supported rule ID.

## Files to modify/create

### NEW: python/tests/lint/test_lint_engine_equivalence.py

- Define frozen models for fixture, case, and expected-finding records. Validate decoded JSON at the boundary.
- Reject malformed fixtures, duplicate case labels, empty source maps, unsafe or absolute source paths, unsupported rules, and invalid finding shapes.
- Materialize `sources` below a fresh synthetic repository root at `tmp_path`, placing detector inputs beneath `repo_root/python/` without reading the live tree.
- Add adapters for:
  - markdown heading fence state: scan synthetic `repo_root/python` sources with `python_dir`, then map each legacy relative file to `python/{legacy.file}` as the repository-relative `Finding.path`;
  - unreachable branch: scan synthetic `repo_root/python/larch` sources with `larch_dir`, then map each legacy relative file to `python/{legacy.file}` as the repository-relative `Finding.path`;
  - self-disarmable gate: resolve metadata from the synthetic design package, then scan its synthetic `plan_quality.py` and map each legacy relative file to `python/{legacy.file}` as the repository-relative `Finding.path`.
- Map markdown findings with messages that retain `pattern_name` and `occurrence`.
- Map unreachable-branch findings with messages that retain `normalized_condition` and `occurrence`.
- Reuse each self-disarmable-gate finding’s existing message.
- Normalize actual legacy-derived paths to repository-relative POSIX form before comparison, then sort actual and expected identities. Separately compare sorted `render_finding()` output.
- Parametrize over every discovered fixture and case so each JSON file is exercised.
- Add completeness guards that require the fixture directory, registry, expected filenames, and the three imported `SUPPRESSION` constants to agree exactly.
- Export the loader and assertion helpers without changing production detector contracts.

### NEW: python/tests/lint/fixtures/lint_engine_equivalence/markdown_heading_fence_state.json

- Set `rule` to the markdown detector’s supported rule ID.
- Add a labeled case with self-contained Python source that applies a heading regex to `splitlines()` without fence-state gating.
- Record the exact normalized identity and rendered engine line with the repository-relative `python/...` path, including the legacy pattern and occurrence data.

### NEW: python/tests/lint/fixtures/lint_engine_equivalence/unreachable_branch.json

- Set `rule` to the unreachable-branch detector’s supported rule ID.
- Add a labeled case with a repeated condition after an earlier matching return.
- Record the exact normalized identity and rendered engine line with the repository-relative `python/...` path, including the normalized condition and occurrence.

### NEW: python/tests/lint/fixtures/lint_engine_equivalence/self_disarmable_gate.json

- Set `rule` to the self-disarmable-gate detector’s supported rule ID.
- Embed both the synthetic `OptionalMetadata` definition and a `plan_quality.py` gate that author-controlled metadata can disable.
- Record the exact normalized identity and rendered engine line with the repository-relative `python/...` path using the detector’s diagnostic message.

## Edge cases

- Normalize expected and actual engine paths to repository-relative POSIX form, including the `python/` prefix; distinguish these from legacy detector and baseline file keys, which are relative to `python/`.
- Keep line numbers tied to the embedded source text.
- Allow multi-file cases while scanning only detector-relevant Python files.
- Treat duplicate or unsupported fixture registrations as harness failures.
- Ensure empty finding results remain distinguishable from fixtures that were not exercised.

## Failure modes

- Fail fixture loading with a path-specific assertion when JSON or schema validation fails.
- Fail completeness checks when a fixture is missing, extra, unsupported, or not parametrized.
- Let legacy detector failures surface rather than converting them into clean results.
- Keep fixtures independent of committed baselines, Git discovery, and live repository content.

## Testing strategy

1. Run `python3 -m pytest python/tests/lint/test_lint_engine_equivalence.py -q`.
2. Run `python3 -m pytest python/tests/lint/test_lint_markdown_heading_fence_state.py python/tests/lint/test_lint_unreachable_branch.py python/tests/lint/test_lint_self_disarmable_gate.py -q`.
3. Run scoped Ruff check and format verification for `python/tests/lint/test_lint_engine_equivalence.py`.
4. Run the repository’s scoped strict pyright command for the new Python test.
5. Confirm `git diff --name-only` contains only the four firm headings.
6. Confirm no production detector, engine, baseline, CLI registration, Makefile target, or CI workflow changed.

## Confidence

High. The shared engine and all three legacy detector APIs are present, and the approved outline fixes the scope and fixture shape.

## Acceptance

1. Run `python3 -m pytest python/tests/lint/test_lint_engine_equivalence.py -q`.
2. Run `python3 -m pytest python/tests/lint/test_lint_markdown_heading_fence_state.py python/tests/lint/test_lint_unreachable_branch.py python/tests/lint/test_lint_self_disarmable_gate.py -q`.
3. Run scoped Ruff check and format verification for `python/tests/lint/test_lint_engine_equivalence.py`.
4. Run the repository’s scoped strict pyright command for the new Python test.
5. Confirm `git diff --name-only` contains only the four firm headings.
6. Confirm no production detector, engine, baseline, CLI registration, Makefile target, or CI workflow changed.

diff_added: 420
diff_deleted: 0
mechanical_churn: false
diff_lines: 420

## Test plan
(no test plan section in plan-file)
