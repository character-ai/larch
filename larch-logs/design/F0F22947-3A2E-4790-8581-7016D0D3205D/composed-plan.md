## Plan

## Approach

Add one canonical design-wire fixture module. Migrate valid, ordinary fixtures to it. Keep malformed, legacy, and parser-boundary literals inline so tests remain explicit.

Piece 1 and Piece 2 are already present through `tests.support.review_wire` and `tests.support.session`.

## Files to modify/create

### NEW: python/tests/support/design_wire.py

- Add `plan_body` for canonical plan text with ordered `### NEW:` and `### UPDATED:` file sections.
- Add `diff_lines_trailer` for the terminal `diff_lines: <N>` grammar.
- Add `result_env_lines` and `write_result_env` for ordered, newline-terminated `KEY=value` fixtures.
- Reject invalid keys and embedded newline, carriage-return, or NUL values.
- Add `run_params_json` for deterministic schema-v3 seeds and caller overrides.
- Preserve caller order where order is part of the fixture contract.

### UPDATED: python/tests/support/test_foundation.py

- Add focused tests for exact plan headings, trailer placement, result-env ordering, unsafe-value rejection, run-parameter defaults, overrides, and terminal newlines.
- Cover paths and Unicode values without weakening the line-oriented wire contract.

### UPDATED: python/tests/design/test_design_lifecycle.py

- Replace repeated valid plan bodies, run-parameter JSON, and result-env writes with the shared builders.
- Use Piece 2 `make_design_tmpdir` where the production-style design layout does not alter the test.
- Keep malformed result envs, missing trailers, stale plans, and partial run-parameter documents inline.

### UPDATED: python/tests/design/test_design_publish.py

- Build ordinary plan and composed-plan fixtures with `plan_body` and `diff_lines_trailer`.
- Replace repeated `.step3-review-result.env` setup with `write_result_env`.
- Preserve invalid trailer ordering, missing assessment, partial checkpoint, and write-failure fixtures inline.

### UPDATED: python/tests/design/test_plan_quality.py

- Migrate normal plan-heading and trailer fixtures to the shared builders.
- Retain raw strings for malformed metadata, duplicate trailers, fenced-heading cases, trailing prose, injection tokens, and other grammar rejection tests.
- Ensure heading-format changes require editing the shared builder rather than each ordinary fixture.

### UPDATED: python/tests/design/test_design_postplan.py

- Use `make_design_tmpdir`, `plan_body`, and `run_params_json` for normal postplan setup.
- Keep sparse or intentionally invalid inputs explicit when they test failure behavior.

### UPDATED: python/tests/design/test_design_log_publish_flow.py

- Use shared plan and run-parameter seeds where committed-log fixtures represent valid design artifacts.
- Preserve arbitrary payload markers used only to test inclusion, exclusion, or byte fidelity.

### UPDATED: python/tests/rendering/test_rendering.py

- Replace repeated plan-body and `run-params.json` writers on design rendering paths.
- Use `make_design_tmpdir` where its extra `source-env.sh` does not affect renderer assertions.
- Keep payload-fidelity markers and empty or malformed inputs inline.

## Edge cases

- Do not normalize negative fixtures into valid wire data.
- Preserve exact trailing-newline behavior.
- Allow dynamic paths and empty values in result envs, but reject multiline injection.
- Let callers override run parameters without mutating shared defaults.
- Avoid adding unrelated heading kinds until a migrated fixture requires them.

## Failure modes

- Broad replacement could hide grammar defects by making malformed tests valid.
- `make_design_tmpdir` may add files that affect directory enumeration tests.
- Different JSON whitespace or key order may break byte-sensitive assertions.
- Result-env validation may reject fixtures that intentionally exercise unsafe input. Those fixtures must remain inline.

## Testing strategy

- Run focused support tests:
  `python3 -m pytest python/tests/support/test_foundation.py`
- Run the migrated design and rendering files:
  `python3 -m pytest python/tests/design/test_design_lifecycle.py python/tests/design/test_design_publish.py python/tests/design/test_plan_quality.py python/tests/design/test_design_postplan.py python/tests/design/test_design_log_publish_flow.py python/tests/rendering/test_rendering.py`
- Run the design pytest shard or its corresponding focused Make targets.
- Run ruff, pylint, and pyright against the changed Python files.
- Verify by search that ordinary plan headings and result-env writers use `tests.support.design_wire`, while remaining literals are negative or fidelity fixtures.

## Acceptance

- Run focused support tests:
  `python3 -m pytest python/tests/support/test_foundation.py`
- Run the migrated design and rendering files:
  `python3 -m pytest python/tests/design/test_design_lifecycle.py python/tests/design/test_design_publish.py python/tests/design/test_plan_quality.py python/tests/design/test_design_postplan.py python/tests/design/test_design_log_publish_flow.py python/tests/rendering/test_rendering.py`
- Run the design pytest shard or its corresponding focused Make targets.
- Run ruff, pylint, and pyright against the changed Python files.
- Verify by search that ordinary plan headings and result-env writers use `tests.support.design_wire`, while remaining literals are negative or fidelity fixtures.

review_status: complete
rounds_completed: 1
difficulty: MODERATE
mechanical_churn: true
diff_lines: 620
