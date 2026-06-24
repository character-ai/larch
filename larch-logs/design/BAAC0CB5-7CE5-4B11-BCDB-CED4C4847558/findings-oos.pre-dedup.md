### OOS_1: [OUT_OF_SCOPE] [SCOPE-REDUCTION] Public `design dialectic-validate-candidates` verb exceeds issue need
- **Description**: [OUT_OF_SCOPE] [SCOPE-REDUCTION] Public `design dialectic-validate-candidates` verb exceeds issue need. Scenario: Shape/cap validation is already planned in `parse_drafter_output()`, promotion, and `design_dialectic.py`. A standalone public CLI verb adds surface, tests, and docs with no Gate C caller on the clarifier path (prior rounds OOS).
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/cli.py:153
- **Phase**: design



### OOS_2: [OUT_OF_SCOPE] Operator docs still mandate retired `design-step4b-preview.sh` for Gate C emit
- **Description**: [OUT_OF_SCOPE] Operator docs still mandate retired `design-step4b-preview.sh` for Gate C emit. Scenario: The plan retargets normative Gate C emit to `design-step3b-tail.sh` in `approval-gates.md` and `SKILL.md` but does not list operator docs in firm `### UPDATED:` files. `docs/configuration-and-permissions.md` and `docs/issue-anchored-plan.md` still cite `design-step4b-preview.sh`, which no longer exists in the repo. Auditors following docs can mis-wire Gate C.
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: docs/configuration-and-permissions.md:336
- **Phase**: design



### OOS_3: [SCOPE-REDUCTION] Public `design dialectic-validate-candidates` exceeds issue need
- **Description**: [SCOPE-REDUCTION] Public `design dialectic-validate-candidates` exceeds issue need. Scenario: Shape/cap validation already lives in `agents.py` parse edge and `design_dialectic.py` promotion. A standalone public verb adds CLI surface, tests, and docs with no Gate C caller on the clarifier path (prior rounds OOS).
- **Reviewer**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: architecture
- **Location**: python/cli.py:148-154
- **Phase**: design



### OOS_4: docs still wire Gate C through retired `design-step4b-preview.sh`
- **Description**: docs still wire Gate C through retired `design-step4b-preview.sh`. Scenario: Operator docs name a fence the repo no longer ships; auditors can expect a second 4b preview after tail consolidation. The plan updates skill references but not these docs.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: docs/configuration-and-permissions.md:336
- **Phase**: design



### OOS_5: [SCOPE-REDUCTION] Separate public `dialectic-promote-candidates` verb adds surface beyond need
- **Description**: [SCOPE-REDUCTION] Separate public `dialectic-promote-candidates` verb adds surface beyond need. Scenario: Post-postplan promotion is a single internal hook in `step2b_drafter_main`; a public promote verb duplicates `dialectic-write-candidates` orchestration paths and expands CLI/tests without a distinct operator callsite.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/cli.py:148-154
- **Phase**: design



### OOS_6: [OUT_OF_SCOPE] [SCOPE-REDUCTION] Public `design dialectic-validate-candidates` verb exceeds the clarifier need.
- **Description**: [OUT_OF_SCOPE] [SCOPE-REDUCTION] Public `design dialectic-validate-candidates` verb exceeds the clarifier need.. Scenario: Shape/cap validation already lives in `agents.py` parse/promotion and `design_dialectic.py` promotion paths; no Gate C caller needs a standalone public verb, adding CLI surface and tests without a named consumer.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/cli.py:148-154
- **Phase**: design



### OOS_7: [OUT_OF_SCOPE] Operator docs still wire Gate C preview through retired `design-step4b-preview.sh`.
- **Description**: [OUT_OF_SCOPE] Operator docs still wire Gate C preview through retired `design-step4b-preview.sh`.. Scenario: Live docs tell auditors/implementers to expect a Step 4b preview fence that the plan retires in favor of `design-step3b-tail.sh`, increasing risk of wiring the wrong entrypoint even after code changes.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: code-quality
- **Location**: docs/configuration-and-permissions.md:336
- **Phase**: design



### OOS_8: [OUT_OF_SCOPE] Issue-anchored plan doc still cites `design-step4b-preview.sh` for Gate C.
- **Description**: [OUT_OF_SCOPE] Issue-anchored plan doc still cites `design-step4b-preview.sh` for Gate C.. Scenario: Same stale entrypoint drift as `docs/configuration-and-permissions.md`; implementers following issue wire docs may miss dialectic-before-preview ordering owned by the Step 4 tail.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: code-quality
- **Location**: docs/issue-anchored-plan.md:219
- **Phase**: design



### OOS_9: [SCOPE-REDUCTION] [OUT_OF_SCOPE] Public `design dialectic-validate-candidates` verb exceeds issue need
- **Description**: [SCOPE-REDUCTION] [OUT_OF_SCOPE] Public `design dialectic-validate-candidates` verb exceeds issue need. Scenario: The issue requires detection, Gate C surfacing, and promotion/clear helpers. Shape and cap validation already live in `agents.py` parse edge and `design_dialectic.py` promotion. A standalone public verb adds CLI surface and tests without a named Gate C caller.
- **Reviewer**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/cli.py:153
- **Phase**: design



