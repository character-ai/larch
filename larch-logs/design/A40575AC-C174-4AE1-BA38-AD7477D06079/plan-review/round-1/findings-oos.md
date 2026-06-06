### OOS_1:
- **Description**: Proposed `_OOS_HEADER_RE` is not semantically equivalent to the awk FINDING branch for tag-after-title headers. Scenario: Awk uses `index($0,"[OUT_OF_SCOPE]")` anywhere on the line after `^###[[:space:]]+FINDING_[0-9]+:`; Python `FINDING_\d+:\s*\[OUT_OF_SCOPE\]` requires the tag immediately after the colon (whitespace only). Headers like `### FINDING_1: Some Title [OUT_OF_SCOPE]` count in awk but not in Python, so bash and Python gates can disagree on defense-in-depth inputs even though the plan claims lockstep parity
- **Reviewer**: Cursor-dyn-awk-python-regex-parity
- **Severity**: latent
- **Focus area**: correctness
- **Location**: python/oos.py:32-33
- **Phase**: design

