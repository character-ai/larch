# Round 1 — Scope & Constraints (resolved from issue body + codebase inspection)

## Decision 1: In-scope file set
- **Question**: Which files may this change touch?
- **Resolution**: `skills/design/scripts/decompose-file-issues.sh` (the `re.search` site near line 97), `skills/design/scripts/test-decompose-file-issues.sh` (add at least 2 new test cases per acceptance), `skills/design/scripts/decompose-file-issues.md` (one-line clarification under "Edge-extraction rules"). NOTHING ELSE.
- **Source**: issue body (Acceptance section enumerates exactly these surfaces)

## Decision 2: Single-blocker backward compatibility
- **Question**: Must existing single-blocker shape (`blocked-by Piece N`) continue to work?
- **Resolution**: Yes — existing harness fixtures (`p1`, `p2` cycle test) must still pass unchanged.
- **Source**: issue body ("Verified locally" table includes `blocked-by Piece 1 → [1]`) + existing test cases at `test-decompose-file-issues.sh:55,77,83,110`

## Decision 3: Strict-reference rule on ALL blockers
- **Question**: When `blocked-by Piece 1, Piece 99` and Piece 99 does not exist, must we still exit 2 with `DECOMPOSE_PARTITION_STATUS=bad-dependency-ref`?
- **Resolution**: Yes — the strict-reference rule must hold across every blocker in the list, not just the first.
- **Source**: issue body Acceptance bullet 3 (explicit)

## Decision 4: Idempotency on duplicate blockers
- **Question**: How should `blocked-by Piece 1, Piece 1` be handled?
- **Resolution**: Single edge, no error (idempotent). Sketch uses a `seen` set.
- **Source**: issue body Acceptance bullet 2 + proposed-fix sketch

## Decision 5: Plural-no-repeat shape (`Pieces 1, 2, 3`)
- **Question**: Should this shape be supported?
- **Resolution**: NO — explicitly an "optional follow-on" the issue says is NOT required for this fix. Not observed in production.
- **Source**: issue body "Optional follow-on (not required for this issue)" subsection

## Decision 6: Separator support
- **Question**: Which separators must work between `Piece N` tokens?
- **Resolution**: Comma (`,`) and the word `and` (e.g., `blocked-by Piece 1 and Piece 2`). The proposed `re.findall(r"Piece\s+(\d+)", ...)` naturally handles both because the regex matches each `Piece N` token regardless of separator.
- **Source**: issue body "Verified locally" reproduction table

Round 1 resolved 6 decisions, all from the issue body and codebase — no `AskUserQuestion` was needed.
