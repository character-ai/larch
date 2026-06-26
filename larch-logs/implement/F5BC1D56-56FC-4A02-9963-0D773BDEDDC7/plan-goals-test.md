## Goal
Implement issue #5495: [IMPLEMENTING] [OOS] [OUT_OF_SCOPE] security: security-tagged dropped OOS committed to public run logs.

## Implementation Plan
## Plan

## Approach

- Extract the existing `voting.is_security_block` string classifier into `voting.is_security_block_text(text: str) -> bool`.
- Keep `voting.is_security_block(block_file)` as the file-reading wrapper.
- In `_apply_pre_vote_oos_gate`, split `dropped_blocks` into:
  - `public_blocks`: not security-tagged.
  - `security_blocks`: security-tagged by `voting.is_security_block_text`.
- Write only `public_blocks` to `oos-dropped-before-vote.md`.
- Write `security_blocks` to local-only `oos-dropped-security-local.md`.
- Keep `gate.dropped_count` as the total dropped count.
- Keep `PRE_VOTE_OOS_DROPPED_FILE` pointing at `oos-dropped-before-vote.md`.
- Do not change `_ROUND_ARTIFACT_ALLOW` or `_copy_gate_audit_to_parent`.

## Files to modify/create

### UPDATED: python/voting.py

- Add `is_security_block_text(text: str) -> bool`.
- Move the current regex and line-scanning logic into that helper.
- Change `is_security_block` to read the file and return `is_security_block_text(text)`.
- Preserve current detection behavior.

### UPDATED: python/review_pipeline.py

- Add a local `security_dropped_file = review_tmpdir / "oos-dropped-security-local.md"` in `_apply_pre_vote_oos_gate`.
- Partition `dropped_blocks` with `voting.is_security_block_text(block)`.
- Write `_renumber_oos_audit_blocks(public_blocks)` to `oos-dropped-before-vote.md`.
- Write `_renumber_oos_audit_blocks(security_blocks)` to `oos-dropped-security-local.md`.
- Write empty strings for absent groups to prevent stale artifact contents.
- Keep status as `ok` when any OOS block was dropped, even if all dropped blocks are security-local.

### UPDATED: python/test_voting.py

- Add direct tests for `is_security_block_text`.
- Cover at least:
  - canonical security focus field text.
  - the existing space-separated `Focus area` form.
  - non-security text returning false.

### UPDATED: python/test_review_pipeline.py

- Add a pre-vote OOS gate test with both public OOS and security OOS blocks.
- Assert:
  - `gate.dropped_count` counts both.
  - public `oos-dropped-before-vote.md` contains only public OOS.
  - local `oos-dropped-security-local.md` contains only security OOS.
  - `findings.md` keeps and renumbers only in-scope findings.
  - `pre-vote-oos-gate.env` still points at `oos-dropped-before-vote.md`.
- Add or extend an all-security dropped-OOS case if needed to verify the public audit is empty while the local sidecar has the security block.

### UPDATED: SECURITY.md

- Document that pre-vote dropped security-tagged OOS blocks are retained only in `oos-dropped-security-local.md`.
- State that they must not be copied to public `oos-dropped-before-vote.md` or committed run logs.

## Edge cases

- **All dropped blocks are security-tagged**: keep `dropped_count` non-zero, write an empty public audit, and write all content to the local sidecar.
- **Mixed public and security OOS**: renumber each audit stream independently as `OOS_1`, `OOS_2`, etc.
- **No dropped blocks**: write empty public and local audit files.
- **Classifier false positives in fenced examples**: preserve the existing classifier semantics by extracting logic only.

## Failure modes

- If writing either audit file fails, `_apply_pre_vote_oos_gate` should keep the existing fail-closed `PreVoteGateError` path.
- If the ballot rewrite fails after audit writes, keep the existing restoration path for `findings.md`.
- If a future change allowlists `oos-dropped-security-local.md`, that is a separate run-log policy regression. Do not add it to `_ROUND_ARTIFACT_ALLOW`.

## Testing strategy

- Run targeted tests:
  - `python3 -m pytest python/test_voting.py python/test_review_pipeline.py`
- Run required repo checks:
  - `make py-lint`
  - `make py-test`
  - `make lint`

## Acceptance

- Run targeted tests:
  - `python3 -m pytest python/test_voting.py python/test_review_pipeline.py`
- Run required repo checks:
  - `make py-lint`
  - `make py-test`
  - `make lint`

diff_added: 95
diff_deleted: 15
mechanical_churn: false
diff_lines: 110

## Test plan
(no test plan section in plan-file)
