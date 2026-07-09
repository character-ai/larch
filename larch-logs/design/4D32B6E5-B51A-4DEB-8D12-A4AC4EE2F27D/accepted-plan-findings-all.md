### FINDING_2: Stateful fence pairing in pass 1
- **Reviewer(s)**: Codex-Pragmatic, Codex-Requirements, Cursor-dyn-Parser State Reviewer
- **Severity**: major
- **Concern**: The generic parser's pass-1 fence scan still pairs opener/closer lines independently, so closing fence lines can be reinterpreted as new openers and later real `###` boundaries can be swallowed into fenced content, corrupting item splits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Track active fence state in pass 1 so only lines outside an open fence can start a new range, or skip any candidate opener that falls inside an already recorded balanced range
  - From Codex-Requirements: Make pass 1 stateful: only recognize a new fence opener when not already inside an active fence, and ignore fence markers that appear in fenced content
  - From Cursor-dyn-Parser State Reviewer: Mirror dedup-plan-lines.py Pass 1: single forward pass, stack of (line_index, marker_char, marker_len); on a marker line when the stack is empty push, else pop only when char matches and len>=top and suffix is empty, then add interior indices to fenced_lines; unclosed stack entries add nothing. Extend the regex for ~~~ fences. Keep Pass 2 gating on OOS_HEADING_RE, PLAIN_HEADING_RE, and consume_oos_field only when index not in fenced_lines, with enumerate(text.splitlines()) and the existing in_body append path for fenced lines.


