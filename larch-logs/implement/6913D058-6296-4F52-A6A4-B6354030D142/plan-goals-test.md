## Goal
Implement issue #7473: [IMPLEMENTING] contract-unification [DEDUP] Extract cycle-free rendering generator helpers.

## Implementation Plan
#### Problem

`python/larch/rendering/_rendering_generators.py` carries `# pylint: skip-file` and states that helpers were duplicated from `rendering.py` to avoid circular imports. `_extract_generated_body`, `_replace_output_instruction`, and their leaf support are exact or near-exact copies. The skip hides the copy from the standard duplicate-code checker.

#### Goal

Extract the shared leaf behavior into a cycle-free rendering helper module. Import it from `rendering.py` and `_rendering_generators.py`. Preserve rendered output and error messages. Remove the `_rendering_generators.py` skip-file directive and its shrink-only baseline row. Do not create a new facade or move renderer-specific orchestration into the leaf.

#### Required implementation

- Move the duplicated `_frontmatter_body`, `_extract_generated_body`, `_replace_output_instruction`, `_sha256_path`, and atomic text helper only when both callers use byte-equivalent behavior. Leave caller-specific generation orchestration in place.
- Place the leaf below both callers in the import graph. It may import `pathlib`, hashing, and shared leaf utilities, but it must not import `rendering.py`, `_rendering_generators.py`, CLI modules, or package facades.
- Preserve heading extraction, frontmatter removal, newline normalization, in-scope and out-of-scope instruction formatting, checksum bytes, file mode, and exception text.
- Repoint both callers to qualified imports. Remove copied constants only after proving both callers use the same values.
- Remove exactly the `_rendering_generators.py` record from `python/pylint-skip-file-baseline.json`. Do not regenerate unrelated baseline rows.

#### Verification

Run focused rendering and generator golden tests, the skip-file lint, duplicate-code against the rendering package, ruff, pyright, and import smoke tests in fresh Python processes. Compare generated artifacts before and after byte-for-byte.

#### Size and acceptance

Expected change: 400-700 lines with a net reduction. Golden generator tests and focused rendering tests must pass. Import-cycle tests must show that both callers load without eager cycles. The skip-file baseline must shrink by exactly the intended row.

## Test plan
(no test plan section in plan-file)
