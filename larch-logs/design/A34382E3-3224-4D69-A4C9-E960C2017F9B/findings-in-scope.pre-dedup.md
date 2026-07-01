### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/SKILL.md:620
- **Concern**: Step 8+ preserve inventory omits the structure-pinned `Python ship driver wrapper` substring. Scenario: Item 3 authorizes tightening the Step 8+ opening paragraph. `scripts/test-implement-structure.sh` requires that exact substring in SKILL.md (lines 839-845). A density edit can pass routing semantics yet fail `make test-implement-structure`.
- **Proposed resolution**: Add `Python ship driver wrapper` to the Step 8+ byte-stable preserve list, Edge cases, and acceptance checks.



### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/SKILL.md:607
- **Concern**: Acceptance anti-halt checklist is incomplete versus `test-implement-anti-halt.sh`. Scenario: Testing strategy and acceptance only freeze `Continue to Step 15.` and `Continue to Step 16.`. The harness also requires `Continue to Step 8 IMMEDIATELY` (line 68). Item 4 still allows adjacent tightening near the architectural-guidelines to Step 8 boundary where that literal lives.
- **Proposed resolution**: Extend acceptance and Edge cases to require all anti-halt literals the harness checks, including `Continue to Step 8 IMMEDIATELY`, or delete Item 4.



### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/implement/SKILL.md:127
- **Concern**: Macro or Step 1.r condensation lacks guard against forbidden absorbed-1.r ROUTE prose. Scenario: Item 1 and Item 2 invite rewriting the long `CHECKPOINT_NEXT` macro and Step 1.r routing text. `scripts/test-implement-structure.sh` forbids reintroducing `branch on envelope \`ROUTE=\` and \`REBASE_RC=\` from the Step 0 bootstrap stdout envelope` (line 495). A shorter rewrite can accidentally restore that retired wording and fail structure tests without changing runtime behavior.
- **Proposed resolution**: Add an explicit do-not-reintroduce pin for the line-495 `forbid()` substring to the Rebase Checkpoint Macro and Step 1.r preserve bullets.



### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:686-689
- **Concern**: Step 8+ preserve inventory omits the execution-issues refresh trigger and fence. Scenario: The plan authorizes tightening the Step 8+ post-driver skeleton and branch blockquotes but never lists the unpinned trigger `When ship-pr-exit-matrix.md requires tracking metadata projection refresh, run this fence; skip it when ISSUE_NUMBER is empty or 0.` or the `python/cli.py execution-issues refresh` Bash fence. A density pass can delete that block while routing semantics and harness pins still pass, violating zero-behavior-change acceptance and skipping metadata projection refresh on branches that need it.
- **Proposed resolution**: Add the trigger sentence and fence to Item 3 byte-stable preserve list, Edge cases, Failure modes, and Acceptance checks (or an explicit do-not-delete note in the post-driver skeleton section).



### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:655
- **Concern**: Step 8+ post-driver continuation omits recovery pre-driver re-run preserve pin. Scenario: Item 3 tells implementers to tighten post-driver continuations and the long-running driver blockquote but does not freeze `If the **Pre-driver predicate** still matches, re-run python/cli.py ship pre-driver before step-8-ship.sh`. That sentence is not harness-pinned; condensing the blockquote can drop it while `every Step 8+ re-entry goes through step-8-ship.sh` remains, so turn recovery on seeded-but-no-PR state can skip the pre-driver verb and invert Step 8+ bootstrap order.
- **Proposed resolution**: Add that recovery substring to Item 3 preserve inventory, Edge cases, and Failure modes alongside the four existing pre-driver predicate pins.



### FINDING_6:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/SKILL.md:249
- **Concern**: Step 0 bootstrap condensation cites only keeping the malformed `BOOTSTRAP_NEXT` sentence "intact enough for structure tests" without the exact `require()` substring. Scenario: `scripts/test-implement-structure.sh` line 485 requires the verbatim sentence `if `BOOTSTRAP_NEXT` is absent or any other value, treat the bootstrap envelope as malformed and abort with exit `2``. A density pass can paraphrase that line while editing the Step 0 routing paragraph or `BOOTSTRAP_NEXT` table preamble, preserving intent but failing `make test-implement-structure`
- **Proposed resolution**: Add the exact malformed-envelope substring to the Step 2 preserve inventory and Edge cases (same treatment as pre-driver predicate pins and `bootstrap_recovery_read_degraded`), and replace "intact enough" with "byte-stable"



### FINDING_7:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:686-690
- **Concern**: Step 8+ post-driver skeleton tightening omits preserve pin for the execution-issues refresh trigger sentence. Scenario: The plan byte-stabilizes Bash fences and lists many structure needles, but authorizes condensing the post-driver branch skeleton without freezing `When ship-pr-exit-matrix.md requires tracking metadata projection refresh, run this fence; skip it when ISSUE_NUMBER is empty or 0.` That predicate is not pinned by `scripts/test-implement-structure.sh` (only a retired `**Execution-issues checkpoint**` forbid exists). An implementer can delete the trigger while keeping the fence and still pass listed harnesses, skipping refresh on non-OOS paths or running it without the ISSUE_NUMBER guard; that violates zero-behavior-change acceptance.
- **Proposed resolution**: Add the trigger sentence (and `python/cli.py execution-issues refresh --implement-tmpdir "$IMPLEMENT_TMPDIR" --best-effort` pairing) to the Step 8+ byte-stable preserve inventory and Edge cases, alongside the existing fence-shape rule.



### FINDING_8:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:99-101
- **Concern**: Anti-halt preservation list omits Step 17 and Step 18 continuation reminders. Scenario: scripts/test-implement-anti-halt.sh also requires `Continue to Step 17.` and `Continue to Step 18.`. The plan currently only protects `Continue to Step 15.` and `Continue to Step 16.`, so a density pass in the Step 16/17/18 tail can delete the remaining continuation reminders and fail the harness.
- **Proposed resolution**: Add `Continue to Step 17.` and `Continue to Step 18.` to the preserved anti-halt literals and edge-case pin list, and mention them in the validation checklist.



