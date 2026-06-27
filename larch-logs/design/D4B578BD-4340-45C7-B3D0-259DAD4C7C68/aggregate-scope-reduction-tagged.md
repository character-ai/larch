### FINDING_8:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/references/self-review.md:31-38
- **Concern**: [SCOPE-REDUCTION] Plan simultaneously requires folding telemetry-mark into the first self-review verb and preserving a standalone telemetry-mark fence plus relocation needle. Scenario: Issue scope calls for folding the telemetry-mark for ~1 fewer self-review turn (design Phase-7 parity). Plan lines 31-32 mandate fold, but lines 34-38 and 257 still require fence 1 and the full `timing telemetry-mark` launcher string in `self-review.md`, with line 32 allowing a physical fence when harness pins need it. Implementers can satisfy harness checks while keeping an extra Bash turn, missing the issue savings goal.
- **Proposed resolution**: Pick one contract: fold telemetry into enter-self-review prose (drop fence 1 from the preserved-four list and relocation needles) or drop the fold requirement; do not require both. If folded, retarget any harness pin to the folded instruction instead of a standalone fence.

### FINDING_14:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/implement/references/self-review.md:32-38
- **Concern**: [SCOPE-REDUCTION] Telemetry fold conflicts with mandatory four-fence preservation. Scenario: The issue requires folding the standalone telemetry-mark into the first self-review verb for ~1 fewer turn. The plan simultaneously mandates preserving all four relocated Bash fences (lines 34-38) and requires the telemetry launcher string in the relocation-authority loop (line 257). Implementers will keep a standalone fence and miss the stated savings without adding harness value.
- **Proposed resolution**: Pick one contract: either fold telemetry into the first verb and drop the standalone fence plus its relocation needle, or drop the fold requirement and document that the issue's turn savings are intentionally deferred.

### FINDING_17:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/references/self-review.md:32-38
- **Concern**: [SCOPE-REDUCTION] Telemetry-fold goal conflicts with mandatory four-fence preservation. Scenario: The issue requires folding the standalone telemetry-mark into the first self-review verb for ~1 fewer turn (design Phase-7 parity). The plan line 32 instructs folding, but lines 34-38 and relocation needles (257, 222) still require a standalone `timing telemetry-mark` Bash fence in `self-review.md`, and line 32 explicitly allows keeping it for harness pins. An implementer can satisfy harnesses while leaving an extra Bash turn, missing the stated savings without breaking tests.
- **Proposed resolution**: Resolve the conflict: either fold telemetry into prose only (no standalone fence), drop telemetry-mark from the four-fence preservation list and relocation needles, and keep `EXPECTED_NEW` at -4 from the other three fences; or document an explicit issue-level waiver if the extra turn is accepted.
