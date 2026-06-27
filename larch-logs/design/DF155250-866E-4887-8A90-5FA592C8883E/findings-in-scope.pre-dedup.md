### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/references/ship-pr-oos-checkpoint-router.md:45,70
- **Concern**: Approach items 45 and 70 contradict: item 45 requires router prose containing `/issue --input-file`, while item 70 forbids that exact substring in `ship-pr-oos-checkpoint-router.md` and item 123 adds a structural forbid for it.. Scenario: A literal implementation cannot satisfy both the required cap-pointer sentence and `make test-implement-structure` router forbids; implementers must guess which instruction wins or the harness fails after an otherwise-correct trim.
- **Proposed resolution**: Rephrase item 45 (and mirrored router bullets at items 45 and 107) to describe cap authority without the forbidden literal, e.g. "this branch does not run cap or public batch OOS issue filing"; keep item 70 forbids unchanged.



### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: blocking
- **Focus area**: risk-integration
- **Location**: skills/implement/references/ship-pr-oos-checkpoint-router.md
- **Concern**: [SCOPE-REDUCTION] Router cap-pointer sentence conflicts with structural forbid on `/issue --input-file`. Scenario: Approach items 45 and 70 and structural pin item 70 require adding a router sentence that includes `/issue --input-file` while also forbidding that exact substring in `ship-pr-oos-checkpoint-router.md`. `scripts/test-implement-structure.sh` `forbid()` is substring-based, so the mandated negation cannot coexist with the forbid pin; implementers must weaken the forbid or drop the required sentence, reintroducing either harness failure or ambiguous public-filing guidance on the security-only branch.
- **Proposed resolution**: Rephrase the required cap-authority sentence without the literal `/issue --input-file` token (for example, "does not run cap enforcement or public issue batch filing"). Keep the structural forbid on positive batch-filing instructions only, or scope the harness forbid to exclude clearly negated forms.



### FINDING_3:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:45,70,107,123
- **Concern**: The plan simultaneously requires and forbids the literal `/issue --input-file` substring in `ship-pr-oos-checkpoint-router.md`.. Scenario: Approach items 45 and 107 require a cap-pointer sentence that includes `/issue --input-file` batch emission. Structural pin items 70 and 123 forbid that exact substring in the router. An implementer cannot satisfy both without weakening the forbid pin, which risks reintroducing dead public batch-filing guidance on the security-only branch and failing `make test-implement-structure`.
- **Proposed resolution**: Reword the required cap-pointer to avoid forbidden literals, e.g. state that cap enforcement applies only on the pre-driver `python/cli.py oos file` path and that this branch does not run batch filing. Keep the forbid pin on `/issue --input-file` unchanged.



### FINDING_4:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: skills/implement/references/ship-pr-oos-checkpoint-router.md:1-13
- **Concern**: Router cap sentence conflicts with the plan’s own no-router-cap rule. Scenario: The plan says this router should mention pre-driver cap enforcement, but item 4 says not to relocate cap prose into the router and item 9 forbids `/issue --input-file` in the same file. Implemented literally, the file cannot satisfy both the required wording and the new structure pins, so `make test-implement-structure` will fail.
- **Proposed resolution**: Remove the cap sentence from the router and keep cap authority in the pre-driver `python/cli.py oos file` path or another non-router reference.



### FINDING_5:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/references/ship-pr-oos-checkpoint-router.md:45,70
- **Concern**: Approach items 45 and 70 contradict: the router must add a cap-authority sentence containing `/issue --input-file` while structural pins forbid that exact substring in the same file.. Scenario: Implementing both instructions makes `make test-implement-structure` fail on the router forbid pin, or forces dropping the required cap pointer.
- **Proposed resolution**: Reword item 45 (and matching router/SKILL prose) to state cap authority lives on the pre-driver `python/cli.py oos file` path and this branch performs no public batch filing, without the literal `/issue --input-file` token; keep item 70 forbids unchanged.



### FINDING_6:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: plan.txt:32-45,97-108,123,156
- **Concern**: Drops the required OOS-cap relocation into the live router and forbids it there.. Scenario: The feature description explicitly says to relocate `## OOS cap contract` into `ship-pr-oos-checkpoint-router.md`, but the plan says not to relocate cap prose into the router, deletes the matrix section, and updates `scripts/test-implement-structure.sh` to forbid any router cap text. That leaves the cap contract anchored only in dead Python-path references and makes the live `oos-pipeline` branch incomplete.
- **Proposed resolution**: Update items 4, 5, 9, and the structure pins so the router carries the OOS-cap reminder or section, and stop forbidding router cap text there.



